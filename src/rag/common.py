import hashlib
import json
import math
from pathlib import Path


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def unit(vector):
    if not isinstance(vector, list) or not vector or any(type(x) not in (int, float) or not math.isfinite(x) for x in vector):
        raise ValueError('Embedding must contain finite numbers')
    norm = math.sqrt(sum(x * x for x in vector))
    if not norm or not math.isfinite(norm):
        raise ValueError('Embedding must have a finite, positive norm')
    return [x / norm for x in vector]


def validate_chunks(chunks):
    if not isinstance(chunks, list) or not chunks:
        raise ValueError('chunks must be a nonempty array')
    ids = set()
    for c in chunks:
        if any(not isinstance(c.get(k), str) or not c[k].strip() for k in ('id', 'text', 'source_id', 'source')):
            raise ValueError('Chunk requires nonempty id, text, source_id, source')
        if c['id'] in ids or type(c.get('page')) is not int or c['page'] < 1 or not isinstance(c.get('metadata'), dict):
            raise ValueError('Duplicate chunk ID, invalid page or metadata')
        ids.add(c['id'])


def evidence_hit(chunk, evidence):
    return (chunk['source_id'] == evidence['source_id'] and chunk['page'] == evidence['page']
            and evidence['evidence'] in chunk['text'])


def enough(chunks, case):
    """gold entries are alternatives; evidence_groups are required groups of alternatives."""
    groups = case.get('evidence_groups', [case.get('gold', [])])
    return bool(groups) and all(any(evidence_hit(c, g) for c in chunks for g in group) for group in groups)


def validate_cases(chunks, cases, minimum=False):
    validate_chunks(chunks)
    if not isinstance(cases, list) or not cases:
        raise ValueError('cases must be a nonempty array')
    ids = set()
    counts = {(s, a): 0 for s in ('dev', 'test') for a in (True, False)}
    for q in cases:
        if not isinstance(q.get('id'), str) or not q['id'].strip() or q['id'] in ids:
            raise ValueError('Case ID missing or duplicated')
        ids.add(q['id'])
        if q.get('split') not in ('dev', 'test') or type(q.get('answerable')) is not bool:
            raise ValueError('Case requires split and answerable boolean')
        if not isinstance(q.get('question'), str) or not q['question'].strip():
            raise ValueError('Question missing')
        if q.get('filter') is not None and not isinstance(q['filter'], dict):
            raise ValueError('filter must be an explicit user-supplied object')
        if q['answerable']:
            if not q.get('expected_answer') or not enough(chunks, q):
                raise ValueError(f"{q['id']}: missing answer or unresolved evidence")
        elif not q.get('absence_reason'):
            raise ValueError(f"{q['id']}: absence_reason required")
        counts[q['split'], q['answerable']] += 1
    if minimum and any(counts[key] < n for key, n in {( 'dev', True): 15, ('dev', False): 2, ('test', True): 5, ('test', False): 2}.items()):
        raise ValueError('Benchmark requires 15+2 dev and 5+2 test cases')
    return {f'{s}_{a}': n for (s, a), n in counts.items()}
