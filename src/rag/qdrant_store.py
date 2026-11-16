"""Day 6-compatible Qdrant local cosine collections; no server required."""
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from .common import digest, load, save, unit, validate_chunks


class QdrantStore:
    collection = 'alice_B'

    def __init__(self, path):
        self.path = Path(path)

    def create(self, chunks, vectors, identity, provenance):
        from qdrant_client import QdrantClient, models
        validate_chunks(chunks)
        vectors = [unit(v) for v in vectors]
        if len(vectors) != len(chunks) or len({len(v) for v in vectors}) != 1:
            raise ValueError('Incompatible vector count/dimensions')
        # Never overwrite an existing persistent collection. Choose a new path
        # explicitly when rebuilding, preserving old experiment indexes.
        if self.path.exists() and any(self.path.iterdir()):
            raise ValueError('Qdrant index directory is not empty; choose a new --index path')
        self.path.mkdir(parents=True, exist_ok=True)
        meta = {'identity': identity, 'dimension': len(vectors[0]), 'count': len(chunks),
                'corpus_hash': digest(chunks), 'provenance': provenance, 'collection': self.collection,
                'vectors_hash': digest(vectors)}
        client = QdrantClient(path=str(self.path))
        try:
            client.create_collection(self.collection, vectors_config=models.VectorParams(size=meta['dimension'], distance=models.Distance.COSINE))
            for start in range(0, len(chunks), 128):
                client.upsert(self.collection, points=[models.PointStruct(id=str(uuid5(NAMESPACE_URL, c['id'])),
                              vector=v, payload=c) for c, v in zip(chunks[start:start+128], vectors[start:start+128])], wait=True)
        finally:
            client.close()
        save(self.path / 'rag-manifest.json', meta)
        return meta

    def read(self, chunks, identity):
        meta = load(self.path / 'rag-manifest.json')
        if meta['identity'] != identity or meta['corpus_hash'] != digest(chunks) or meta['count'] != len(chunks):
            raise ValueError('Qdrant corpus/model differs from the query settings')
        return meta, []

    def search(self, vector, top_k, filters):
        from qdrant_client import QdrantClient, models
        conditions = []
        for key, value in (filters or {}).items():
            if type(value) not in (str, int, bool):
                raise ValueError('Qdrant filters support scalar string/int/bool values')
            payload_key = key if key in ('source_id', 'source', 'page') else 'metadata.' + key
            conditions.append(models.FieldCondition(key=payload_key, match=models.MatchValue(value=value)))
        client = QdrantClient(path=str(self.path))
        try:
            config = client.get_collection(self.collection).config.params.vectors
            if config.size != len(vector) or config.distance != models.Distance.COSINE:
                raise ValueError('Qdrant query/index dimension or distance mismatch')
            rows = client.query_points(self.collection, query=vector, limit=top_k, with_payload=True,
                                       query_filter=models.Filter(must=conditions) if conditions else None).points
            return sorted([{**p.payload, 'score': p.score, 'strategy': 'dense'} for p in rows], key=lambda c: (-c['score'], c['id']))
        finally:
            client.close()
