"""Print evidence for manual/AI-assisted review; does not assign grades."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.rag.common import load

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    parser.add_argument('--ids', nargs='*')
    parser.add_argument('--all-context', action='store_true')
    args = parser.parse_args()
    cases = {q['id']: q for q in load('data/alice/cases.json')}
    path = args.run/'traces.json'
    traces = load(path) if path.exists() else [json.loads(l) for l in (args.run/'traces.jsonl').read_text(encoding='utf-8').splitlines()]
    for trace in traces:
        if args.ids and trace['query_id'] not in args.ids:
            continue
        case = cases[trace['query_id']]
        print(json.dumps({'id': case['id'], 'question': case['question'], 'expected': case.get('expected_answer'),
                          'status': trace['status'], 'answer': trace.get('answer'), 'citations': trace.get('citations'),
                          'error': trace.get('error'), 'final_event': (trace.get('events') or [{}])[-1]}, ensure_ascii=False))
        for chunk in trace.get('context_chunks', []):
            if args.all_context or chunk['id'] in trace.get('citations', []):
                print(json.dumps({'chunk': chunk['id'], 'page': chunk['page'], 'text': chunk['text']}, ensure_ascii=False))
