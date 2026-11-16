"""Verify final artifacts and provenance without calling a model or assigning grades."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.rag.common import digest, load, validate_cases
from build_final_report import RUNS


def main():
    root = ROOT/'results/final-agent'
    chunks, cases = load(ROOT/'data/alice/chunks.json'), load(ROOT/'data/alice/cases.json')
    validate_cases(chunks, cases, minimum=True)
    frozen = load(root/'frozen-agent.json')
    total = 0
    for _, split, folder in RUNS:
        run = root/folder
        manifest, traces, reviews, audit, summary = (load(run/name) for name in
            ('manifest.json', 'traces.json', 'reviews.json', 'audit.json', 'summary.json'))
        assert manifest['split'] == split and manifest['mode'] == 'agent', folder
        for key, value in frozen['identity'].items():
            if key != 'config_hash':
                assert manifest['identity'][key] == value, (folder, key)
        assert manifest['identity']['config_hash'] in frozen['allowed_config_hashes'], folder
        assert audit['reviews_hash'] == digest(reviews) and audit['traces_hash'] == digest(traces), folder
        assert summary['errors'] == audit['provider_errors'] == 0, folder
        assert {t['query_id'] for t in traces} == {q['id'] for q in cases if q['split'] == split}, folder
        by_id = {t['query_id']: t for t in traces}
        for review in reviews:
            assert review['trace_hash'] == digest(by_id[review['query_id']]), (folder, review['query_id'])
            assert review['review_type'] == 'ai_assisted'
            if review['human_verified'] is True:
                confirmation = load(root/'human-verification.json')
                scope = confirmation['runs'][folder]
                assert confirmation['human_verified'] is True
                assert scope['reviews_hash'] == digest(reviews) and scope['traces_hash'] == digest(traces)
            else:
                assert review['human_verified'] is False
        for trace in traces:
            assert len(trace['context']) <= manifest['config']['budget_chars']
            assert all(cid in trace['context_ids'] for cid in trace['citations'])
            if trace['status'] == 'answered':
                assert trace['citations'] and all(f'[{cid}]' in trace['answer'] for cid in trace['citations'])
        if split == 'test':
            assert (root/'frozen-agent.json').stat().st_mtime <= (run/'manifest.json').stat().st_mtime
        total += len(reviews)
        print(f'{folder}: {len(traces)} traces, audit hashes and lock verified')
    # Scan shareable outputs by filename only, never display possible credentials.
    candidates = [ROOT/'.env.example', ROOT/'TONG_HOP_QUA_TRINH_VA_KET_QUA.md']
    for directory in ('src', 'scripts', 'configs', 'docs', 'results', 'report'):
        candidates.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and p.suffix in ('.py', '.md', '.json', '.jsonl', '.txt'))
    for path in candidates:
        assert not re.search(r'gsk_[A-Za-z0-9]{16,}', path.read_text(encoding='utf-8', errors='replace')), f'Possible credential in {path.relative_to(ROOT)}'
    print(f'PASS: {total} reviewed traces; 4 complete runs; no Groq key pattern in shareable outputs.')


if __name__ == '__main__':
    main()
