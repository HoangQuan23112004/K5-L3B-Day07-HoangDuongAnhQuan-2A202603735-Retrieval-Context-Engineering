"""Preserve Day 6 B chunks and IDs; create a new Day 7 held-out test."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.rag.common import digest, load, save, validate_cases
from starter.convert_day6 import convert_chunk, convert_question

REPO = 'https://github.com/HoangQuan23112004/K5-L3B-Day06-HoangDuongAnhQuan-2A202603735-DataIngestionEngineering'
COMMIT = '82080a89e87cf6eeab2c9709d8c50276ce8dd2c7'


def prepare(root, output):
    raw = [json.loads(line) for line in (root/'results/chunks_B.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    chunks = [convert_chunk(c) for c in raw]
    # Old Day 6 test is already exposed in its results and PROTOCOL.md. Retire it.
    cases = [{**convert_question(q), 'answerable': True, 'label_origin': 'Day 6 dev, unchanged'}
             for q in load(root/'benchmark/questions.json') if q['split'] == 'dev']
    fresh = [
        ('c778e44b8969b05255e0dae39e7b080a6857bf7e25971d89a6ba4ad94676102f',
         'Which four branches of Arithmetic does the Mock Turtle name in his education story?',
         'Ambition, Distraction, Uglification, and Derision.'),
        ('52df49b8955d3fee54598b9d546f629346011429ccf1a67fce71c96e8ca49de0',
         'Why do the jurors write their own names before the trial ends?',
         'They fear forgetting their names before the end of the trial.'),
        ('4e3a4a7ea769c0be16e552a13122c253ceeb839d7bd9d3579cbe40b2d6da1b79',
         'After writing all three dates for the beginning of the Hatter’s tea, what calculation did the jury do?',
         'They added the dates and reduced the result to shillings and pence.'),
        ('5ae97a93b30de4296cebf117501894116b17502433c59c2809b258c9cdca0391',
         'What mistake did Alice make while putting the Lizard back in the jury-box, and how did she fix it?',
         'She placed him head downwards, then took him out and put him the right way up.'),
        ('4dc73d58a323236207af1a75aea539a79e6809f8b985de91578b3dab16397d9e',
         'How did Bill resume making marks on his slate after the Queen threw an inkstand at him?',
         'He used the ink trickling down his face.'),
    ]
    by_id = {c['id']: c for c in chunks}
    for i, (cid, question, expected) in enumerate(fresh, 1):
        c = by_id[cid]
        cases.append({'id': f'D7-T{i:02}', 'split': 'test', 'question': question, 'answerable': True,
                      'expected_answer': expected, 'gold': [{'source_id': c['source_id'], 'page': c['page'], 'evidence': c['text']}],
                      'label_origin': 'New Day 7 question, full supporting source chunk; not an old Q16-Q20 question'})
    for cid, split, question, reason in [
        ('D7-D-N1', 'dev', 'What is the serial number engraved on the White Rabbit’s watch?',
         'The corpus describes a watch and its handling but never supplies an engraved serial number; full text checked.'),
        ('D7-D-N2', 'dev', 'What is the exact birthday of Alice’s sister?',
         'The corpus mentions the sister without giving her birth date; checked the complete source and occurrences of sister/birthday.'),
        ('D7-T-N1', 'test', 'What is the exact age in years of Bill the Lizard?',
         'Bill appears in the house and court episodes, but no exact age is specified in the complete source.'),
        ('D7-T-N2', 'test', 'What is the street number and postal address of Alice’s home?',
         'The complete story provides no numbered street/postal address for Alice’s home.'),
    ]:
        cases.append({'id': cid, 'split': split, 'question': question, 'answerable': False,
                      'expected_behavior': 'search_and_abstain', 'absence_reason': reason})
    validate_cases(chunks, cases, minimum=True)
    save(output/'chunks.json', chunks)
    save(output/'cases.json', cases)
    save(output/'manifest.json', {'upstream_repo': REPO, 'upstream_commit': COMMIT, 'strategy': 'B',
         'chunks': len(chunks), 'logical_pages': 69, 'physical_pages': None,
         'page_rule': load(root/'data/manifest.json')['page_rule'], 'corpus_hash': digest(chunks),
         'embedding_model': 'sentence-transformers/all-MiniLM-L6-v2', 'dimension': 384,
         'vector_store': 'Qdrant local cosine, alice_B; rebuild with original embedding model because snapshot was not published',
         'benchmark': '15 unchanged Day 6 dev + 5 newly authored Day 7 test + 2 dev and 2 test unanswerable',
         'test_protocol': 'Old Q16-Q20 retired. New test authored before Day 7 dev tuning; do not inspect retrieval outputs until freeze.',
         'rights': load(root/'data/manifest.json')['license_or_permission']})
    print(f'Prepared {len(chunks)} unchanged B chunks; 69 logical units; 17 dev + 7 fresh test cases')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--upstream', type=Path, default=Path('vendor/day6'))
    parser.add_argument('--output', type=Path, default=Path('data/alice'))
    args = parser.parse_args()
    prepare(args.upstream, args.output)
