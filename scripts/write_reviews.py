"""Apply explicit reviewer labels; no grading inferred from retrieval or IDs."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.rag.common import digest, load, save


def apply(run, notes):
    traces = load(run/'traces.json')
    by_id = {t['query_id']: t for t in traces}
    if set(notes) != {t['query_id'] for t in traces if t['status'] != 'error'}:
        raise ValueError('Supply an explicit review for every successful query')
    existing = {r['query_id']: r for r in load(run/'reviews.json')} if (run/'reviews.json').exists() else {}
    reviews = []
    for query_id, label in notes.items():
        trace = by_id[query_id]
        support = label['citation_support']
        reasons = label['citation_reasons']
        if len(support) != len(trace['citations']) or len(reasons) != len(trace['citations']):
            raise ValueError(f'{query_id}: a support label and reason required for each citation')
        review = {'query_id': query_id, **label, 'review_type': 'ai_assisted', 'human_verified': False,
                  'trace_hash': digest(trace)}
        old = existing.get(query_id, {})
        if old.get('human_verified') is True and old.get('trace_hash') == review['trace_hash'] and all(old.get(k) == v for k, v in label.items()):
            review['human_verified'] = True
            if 'human_verification' in old:
                review['human_verification'] = old['human_verification']
        reviews.append(review)
    save(run/'reviews.ai.json', reviews)
    return reviews


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    parser.add_argument('notes', type=Path)
    args = parser.parse_args()
    apply(args.run, load(args.notes))
