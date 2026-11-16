"""BM25, SQLite dense cosine, and reciprocal rank fusion."""
import json
import math
import re
import sqlite3
import unicodedata
from collections import Counter
from contextlib import closing
from pathlib import Path

from .common import digest, unit, validate_chunks


def tokens(text):
    return re.findall(r'\w+', unicodedata.normalize('NFC', text).casefold())


def matches(chunk, filters):
    return all((chunk.get(k) if k in ('source_id', 'source', 'page') else chunk['metadata'].get(k)) == v
               for k, v in (filters or {}).items())


class BM25:
    def __init__(self, chunks, k1=1.5, b=0.75):
        self.chunks = chunks
        self.k1, self.b = k1, b
        self.counts = [Counter(tokens(c['text'])) for c in chunks]
        self.lengths = [sum(c.values()) for c in self.counts]
        self.avg = sum(self.lengths) / max(1, len(chunks)) or 1
        df = Counter(t for row in self.counts for t in row)
        self.idf = {t: math.log(1 + (len(chunks) - n + .5) / (n + .5)) for t, n in df.items()}

    def search(self, query, top_k=3, filters=None):
        result = []
        for chunk, counts, length in zip(self.chunks, self.counts, self.lengths):
            if not matches(chunk, filters):
                continue
            score = sum(self.idf.get(t, 0) * counts[t] * (self.k1 + 1) /
                        (counts[t] + self.k1 * (1 - self.b + self.b * length / self.avg)) for t in set(tokens(query)))
            if score > 0:
                result.append({**chunk, 'score': score, 'strategy': 'bm25'})
        return sorted(result, key=lambda c: (-c['score'], c['id']))[:top_k]


class VectorStore:
    def __init__(self, path):
        self.path = Path(path)

    def create(self, chunks, vectors, identity, provenance):
        validate_chunks(chunks)
        if len(chunks) != len(vectors):
            raise ValueError('Embedding count does not match corpus')
        vectors = [unit(v) for v in vectors]
        if len({len(v) for v in vectors}) != 1:
            raise ValueError('Embedding dimensions differ')
        meta = {'identity': identity, 'dimension': len(vectors[0]), 'corpus_hash': digest(chunks),
                'provenance': provenance, 'count': len(chunks), 'vectors_hash': digest(vectors)}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)')
            conn.execute('CREATE TABLE IF NOT EXISTS chunks (id TEXT PRIMARY KEY, chunk TEXT, vector TEXT)')
            conn.execute('DELETE FROM meta')
            conn.execute('DELETE FROM chunks')
            conn.execute('INSERT INTO meta VALUES (?, ?)', ('index', json.dumps(meta)))
            conn.executemany('INSERT INTO chunks VALUES (?, ?, ?)',
                             [(c['id'], json.dumps(c), json.dumps(v)) for c, v in zip(chunks, vectors)])
        return meta

    def read(self, chunks, identity):
        if not self.path.is_file():
            raise ValueError('Vector index missing; run index or import-index first')
        with closing(sqlite3.connect(f'{self.path.resolve().as_uri()}?mode=ro', uri=True)) as conn:
            meta = json.loads(conn.execute('SELECT value FROM meta WHERE key = ?', ('index',)).fetchone()[0])
            if meta['identity'] != identity or meta['corpus_hash'] != digest(chunks):
                raise ValueError('Index model/provider/URL or corpus mismatch; rebuild or import the matching index')
            rows = [(json.loads(c), unit(json.loads(v))) for c, v in conn.execute('SELECT chunk, vector FROM chunks ORDER BY id')]
        if len(rows) != len(chunks) or any(len(v) != meta['dimension'] for _, v in rows):
            raise ValueError('Corrupt vector index')
        return meta, rows


def provider_identity(provider):
    if getattr(provider, 'embedding_backend', None) == 'fastembed':
        return {'provider': 'fastembed', 'model': provider.embedding_model, 'query_method': 'query_embed'}
    return {'provider': provider.kind, 'base_url': provider.base_url, 'model': provider.embedding_model}


class Retriever:
    def __init__(self, chunks, provider, config, index_path, store_kind='sqlite'):
        validate_chunks(chunks)
        self.config, self.provider = config, provider
        self.method = config['method']
        if self.method not in ('bm25', 'dense', 'hybrid'):
            raise ValueError('Unknown retrieval method')
        self.lexical = BM25(chunks)
        self.meta, self.rows = (None, [])
        self.store_kind = store_kind
        if self.method != 'bm25':
            self.store = get_store(index_path, store_kind)
            self.meta, self.rows = self.store.read(chunks, provider_identity(provider))

    def dense(self, query, top_k, filters):
        vector = self.provider.embed_query(query)
        if len(vector) != self.meta['dimension']:
            raise ValueError('Query embedding dimension differs from Day 6 index')
        if self.store_kind == 'qdrant':
            return self.store.search(vector, top_k, filters)
        result = [{**c, 'score': sum(a*b for a, b in zip(vector, v)), 'strategy': 'dense'}
                  for c, v in self.rows if matches(c, filters)]
        return sorted(result, key=lambda c: (-c['score'], c['id']))[:top_k]

    def search(self, query, *, top_k=3, filters=None):
        if not isinstance(query, str) or not query.strip() or type(top_k) is not int or top_k < 1:
            raise ValueError('Nonempty query and positive top_k required')
        if self.method == 'bm25':
            results = self.lexical.search(query, top_k, filters)
        elif self.method == 'dense':
            results = self.dense(query, top_k, filters)
        else:
            count = max(top_k, self.config.get('candidates', 12))
            ranked = [self.dense(query, count, filters), self.lexical.search(query, count, filters)]
            fused = {}
            for name, rows in zip(('dense', 'bm25'), ranked):
                for rank, c in enumerate(rows, 1):
                    row = fused.setdefault(c['id'], {**c, 'score': 0, 'strategy': 'hybrid', 'component_ranks': {}})
                    row['score'] += 1 / (self.config.get('rrf_k', 60) + rank)
                    row['component_ranks'][name] = rank
            results = sorted(fused.values(), key=lambda c: (-c['score'], c['id']))[:top_k]
        return [{**c, 'rank': i} for i, c in enumerate(results, 1)]


def get_store(path, kind):
    if kind == 'qdrant':
        from .qdrant_store import QdrantStore
        return QdrantStore(path)
    if kind != 'sqlite':
        raise ValueError('Unknown vector store')
    return VectorStore(path)


def pack_context(results, budget):
    """Deduplicate whole chunks; retain provenance, never truncate conditions."""
    blocks, selected, seen = [], [], set()
    for c in results:
        if c['id'] in seen:
            continue
        seen.add(c['id'])
        block = f"[{c['id']}] source={c['source']} page={c['page']}\n{c['text']}"
        if len('\n\n'.join(blocks + [block])) <= budget:
            blocks.append(block)
            selected.append(c)
    return '\n\n'.join(blocks), selected
