"""Standard-library HTTP clients. No mock fallback, no credential logging."""
import json
import math
import os
import re
import socket
import ssl
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

from .common import unit


class RateLimitError(RuntimeError):
    """Request remained rate limited after bounded retries."""


def retry_delay(value, attempt):
    try:
        seconds = float(value)
        if math.isfinite(seconds) and seconds >= 0:
            return max(1.0, seconds)
    except (TypeError, ValueError):
        pass
    return 5.0 * 2 ** attempt


def connection_detail(error):
    """Classify network failures without printing URLs, proxy passwords or keys."""
    reason = error.reason if isinstance(error, urllib.error.URLError) else error
    if isinstance(reason, ssl.SSLCertVerificationError):
        return 'TLS certificate verification failed; check system clock and trusted certificates'
    if isinstance(reason, ssl.SSLError):
        return 'TLS handshake failed'
    if isinstance(reason, socket.gaierror):
        return 'DNS lookup failed; check the API hostname and DNS/network connection'
    if isinstance(reason, TimeoutError):
        return 'connection timed out; check network access to the API'
    if isinstance(reason, ConnectionRefusedError):
        return 'connection refused; check endpoint and proxy settings'
    if isinstance(reason, ConnectionResetError):
        return 'connection reset; check network, VPN or proxy'
    if isinstance(reason, OSError):
        code = getattr(reason, 'winerror', None) or reason.errno
        return f'OS network error {code}; check network and firewall access'
    if '407' in str(reason) or 'proxy authentication' in str(reason).lower():
        return 'proxy authentication required'
    return 'network connection failed; run scripts/check_provider.py for diagnostics'


class Provider:
    def __init__(self, kind='ollama', base_url=None, chat_model=None, embedding_model=None, timeout=180, embedding_backend='remote'):
        if kind not in ('ollama', 'openai'):
            raise ValueError('provider must be ollama or openai')
        self.kind = kind
        self.base_url = (base_url or ('http://localhost:11434' if kind == 'ollama' else 'https://api.openai.com/v1')).rstrip('/')
        self.chat_model = chat_model
        self.embedding_model = embedding_model
        self.timeout = timeout
        self.calls = []
        self.embedding_backend = embedding_backend
        self._local = None
        self.is_groq = urlparse(self.base_url).hostname == 'api.groq.com'
        self.max_retries = int(os.getenv('RAG_MAX_RETRIES', '3'))
        self.retry_wait_limit = float(os.getenv('RAG_MAX_RETRY_WAIT_SECONDS', '60'))
        self.request_interval = float(os.getenv('RAG_REQUEST_INTERVAL_SECONDS', '3' if self.is_groq else '0'))
        if self.max_retries < 0 or any(not math.isfinite(v) or v < 0 for v in (self.retry_wait_limit, self.request_interval)):
            raise ValueError('Retry count and wait settings must be finite and nonnegative')
        self._last_request = None

    def local_model(self):
        if self._local is None:
            from fastembed import TextEmbedding
            self._local = TextEmbedding(model_name=self.embedding_model, threads=4,
                                        cache_dir=os.getenv('RAG_MODEL_CACHE', 'artifacts/model-cache'))
        return self._local

    def post(self, path, body):
        headers = {'Content-Type': 'application/json', 'User-Agent': 'Day7-AgenticRAG/1.0'}
        if self.kind == 'openai':
            key_name = 'GROQ_API_KEY' if self.is_groq else 'OPENAI_API_KEY'
            key = os.getenv('RAG_API_KEY') or os.getenv(key_name)
            if not key:
                raise RuntimeError(f'Set RAG_API_KEY or {key_name} in the environment')
            headers['Authorization'] = 'Bearer ' + key
        request = urllib.request.Request(self.base_url + path, data=json.dumps(body).encode(), headers=headers)
        start = time.perf_counter()
        for attempt in range(self.max_retries + 1):
            if self._last_request is not None:
                wait = self.request_interval - (time.monotonic() - self._last_request)
                if wait > 0:
                    time.sleep(wait)
            self._last_request = time.monotonic()
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    result = json.load(response)
                break
            except urllib.error.HTTPError as exc:
                if exc.code != 429:
                    self.raise_http_error(exc, path)
                delay = retry_delay(exc.headers.get('Retry-After') if exc.headers else None, attempt)
                exc.close()
                retry = attempt < self.max_retries and delay <= self.retry_wait_limit
                self.calls.append({'endpoint': path, 'model': body['model'], 'status': 'rate_limited',
                                   'http_status': 429, 'retry_after_seconds': delay,
                                   'will_retry': retry, 'usage': {}})
                if not retry:
                    raise RateLimitError(f'Provider HTTP 429 at {path} (rate_limit_exceeded); retry after {delay:g}s; request retries exhausted or wait exceeds configured limit') from None
                print(f'Groq/API rate limit: waiting {delay:g}s before retry {attempt + 1}/{self.max_retries}', flush=True)
                time.sleep(delay)
            except (urllib.error.URLError, TimeoutError) as exc:
                reason = exc.reason if isinstance(exc, urllib.error.URLError) else exc
                transient = isinstance(reason, (socket.gaierror, TimeoutError, ConnectionResetError))
                delay = min(5.0 * 2 ** attempt, self.retry_wait_limit)
                retry = transient and attempt < self.max_retries and delay > 0
                self.calls.append({'endpoint': path, 'model': body['model'], 'status': 'network_error',
                                   'detail': connection_detail(exc), 'will_retry': retry, 'usage': {}})
                if retry:
                    print(f'API network interruption: waiting {delay:g}s before retry {attempt + 1}/{self.max_retries}', flush=True)
                    time.sleep(delay)
                    continue
                raise ConnectionError(f'Provider unavailable at {path}: {connection_detail(exc)}') from None
        usage = result.get('usage', {}) if self.kind == 'openai' else {
            'prompt_tokens': result.get('prompt_eval_count', 0),
            'completion_tokens': result.get('eval_count', 0)}
        self.calls.append({'endpoint': path, 'model': body['model'], 'usage': usage,
                           'elapsed_ms': (time.perf_counter() - start) * 1000})
        return result

    @staticmethod
    def raise_http_error(exc, path):
        # Only expose bounded error codes, never raw bodies or echoed inputs.
        raw = exc.read(4096)
        exc.close()
        detail = ''
        try:
            error = json.loads(raw).get('error', {})
            code = error.get('code') or error.get('type')
            if isinstance(code, str) and re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', code):
                detail = f' ({code})'
        except (ValueError, AttributeError):
            if b'error code: 1010' in raw:
                detail = ' (Cloudflare 1010)'
        raise RuntimeError(f'Provider HTTP {exc.code} at {path}{detail}') from None

    def embed(self, texts):
        if not self.embedding_model:
            raise ValueError('embedding_model required')
        if self.embedding_backend == 'fastembed':
            start = time.perf_counter()
            vectors = [unit(v.tolist()) for v in self.local_model().embed(texts, batch_size=32)]
            self.calls.append({'endpoint': 'local/embed', 'model': self.embedding_model,
                               'elapsed_ms': (time.perf_counter() - start) * 1000, 'usage': {'texts': len(texts)}})
            return vectors
        body = {'model': self.embedding_model, 'input': texts}
        if self.kind == 'ollama':
            body['truncate'] = False
            rows = self.post('/api/embed', body)['embeddings']
        else:
            rows = [r['embedding'] for r in sorted(self.post('/embeddings', body)['data'], key=lambda r: r['index'])]
        if len(rows) != len(texts):
            raise ValueError('Provider returned an incorrect embedding count')
        vectors = [unit(v) for v in rows]
        if len({len(v) for v in vectors}) != 1:
            raise ValueError('Embedding dimensions differ')
        return vectors

    def embed_query(self, query):
        if self.embedding_backend == 'fastembed':
            start = time.perf_counter()
            vector = unit(next(iter(self.local_model().query_embed(query))).tolist())
            self.calls.append({'endpoint': 'local/query_embed', 'model': self.embedding_model,
                               'elapsed_ms': (time.perf_counter() - start) * 1000, 'usage': {'texts': 1}})
            return vector
        return self.embed([query])[0]

    def chat(self, messages, tools):
        if not self.chat_model:
            raise ValueError('chat_model required')
        body = {'model': self.chat_model, 'messages': messages, 'tools': tools}
        if self.kind == 'ollama':
            body.update(stream=False, options={'temperature': 0})
            return self.post('/api/chat', body)['message']
        if self.is_groq:
            body.update(tool_choice='required', parallel_tool_calls=False, temperature=0)
        return self.post('/chat/completions', body)['choices'][0]['message']
