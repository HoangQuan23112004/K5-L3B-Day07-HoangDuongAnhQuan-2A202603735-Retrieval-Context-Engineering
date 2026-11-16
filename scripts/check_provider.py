"""Minimal connection diagnostic; never prints credentials or request headers."""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.rag.settings import load_project_env
from src.rag.providers import connection_detail


def main():
    load_project_env()
    key = os.getenv('RAG_API_KEY') or os.getenv('GROQ_API_KEY')
    if not key:
        raise SystemExit('Configure GROQ_API_KEY first')
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key,
               'User-Agent': 'Day7-AgenticRAG/1.0'}
    body = {'model': os.getenv('RAG_CHAT_MODEL'), 'messages': [{'role': 'user', 'content': 'Reply OK.'}],
            'max_completion_tokens': 16}
    if '--tools' in sys.argv:
        from src.rag.agent import TOOLS, SYSTEM
        body.update(messages=[{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': 'What was in the ORANGE MARMALADE jar?'}],
                    tools=TOOLS, tool_choice='required', parallel_tool_calls=False, max_completion_tokens=1024)
    request = urllib.request.Request(os.getenv('RAG_BASE_URL').rstrip('/') + '/chat/completions',
                                     data=json.dumps(body).encode(), headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            print('HTTP:', response.status)
    except urllib.error.HTTPError as exc:
        raw = exc.read(4096).decode('utf-8', errors='replace').replace(key, '[REDACTED]')
        print('HTTP:', exc.code)
        print('Content-Type:', exc.headers.get('Content-Type'))
        print('Server:', exc.headers.get('Server'))
        try:
            error = json.loads(raw).get('error', {})
            print('Error:', json.dumps({k: error.get(k) for k in ('type', 'code', 'message')}, ensure_ascii=False))
        except (ValueError, AttributeError):
            # Limit non-JSON diagnostics to a known gateway error code.
            import re
            match = re.search(r'error code:\s*\d+', raw, re.I)
            print('Gateway:', match.group(0) if match else 'Non-JSON error response')
        return 1
    except (urllib.error.URLError, TimeoutError) as exc:
        print('Connection error:', connection_detail(exc))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
