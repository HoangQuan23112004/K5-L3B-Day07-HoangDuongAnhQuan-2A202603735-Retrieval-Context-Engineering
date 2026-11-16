"""Reproduce retrieval experiments without sending any data to a chat model."""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.rag.common import load, save

CONFIGS = ['bm25', 'dense', 'hybrid', 'hybrid-wide', 'bm25-wide', 'bm25-small']


def run(*args):
    subprocess.run([sys.executable, '-X', 'utf8', '-m', 'src.rag', *args], cwd=ROOT, check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['dev', 'finalize'])
    parser.add_argument('--output', type=Path, default=ROOT/'results/alice')
    args = parser.parse_args()
    output = args.output.resolve()
    if args.phase == 'dev':
        # Every config uses the same corpus/index/labels. Compare ranking at top-3
        # even when a wider pipeline packs top-6 into the final context.
        for name in CONFIGS:
            run('benchmark', '--config', f'configs/{name}.json', '--split', 'dev', '--mode', 'retrieval',
                '--output', str(output/f'{name}-dev'))
    else:
        def score(name):
            summary = load(output/f'{name}-dev/summary.json')
            config = load(ROOT/f'configs/{name}.json')
            if summary['errors'] or summary['successful'] != 17:
                raise ValueError(f'Incomplete dev run: {name}')
            # Declared in docs/PROTOCOL.md before test: evidence > ranking > budget.
            # Latency is reported, not used as a noisy tie-breaker on this tiny corpus.
            return (summary['context_evidence_rate']['rate'], summary['hit_at_3']['rate'],
                    summary['hit_at_1']['rate'], -config['budget_chars'], -config['top_k'])
        chosen = max(CONFIGS, key=score)
        lock = output/'frozen-retrieval.json'
        run('freeze', '--retrieval-only', '--selected', f'configs/{chosen}.json', '--reason',
            'Maximize dev context evidence, then Hit@3, Hit@1; ties prefer smaller context budget and top-k. Agent connection deferred by user.',
            '--dev-results', *[str(output/f'{name}-dev') for name in CONFIGS], '--output', str(lock))
        save(output/'selection.json', {'selected': chosen, 'baseline': 'bm25', 'dev_score': score(chosen),
                                      'lock': str(lock.relative_to(ROOT)) if lock.is_relative_to(ROOT) else str(lock),
                                      'scope': 'retrieval only; no claim of grounded agent quality'})
        for name in dict.fromkeys(['bm25', chosen]):
            run('benchmark', '--config', f'configs/{name}.json', '--split', 'test', '--mode', 'retrieval',
                '--lock', str(lock), '--output', str(output/f'{name}-test'))
