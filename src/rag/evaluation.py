import statistics
import time

from .common import enough
from .retrieval import pack_context


def ratio(n, total):
    return {'n': n, 'N': total, 'rate': n / total if total else None}


def retrieval_trace(case, retriever, config):
    start = time.perf_counter()
    results = retriever.search(case['question'], top_k=max(3, config['top_k']), filters=case.get('filter'))
    context, selected = pack_context(results[:config['top_k']], config['budget_chars'])
    return {'query_id': case['id'], 'question': case['question'], 'status': 'retrieved', 'results': results,
            'context': context, 'context_chunks': selected, 'context_ids': [c['id'] for c in selected],
            'elapsed_ms': (time.perf_counter() - start) * 1000}


def summarize(cases, traces, mode):
    by_id = {q['id']: q for q in cases}
    successful = [t for t in traces if t['status'] != 'error']
    answerable = [t for t in successful if by_id[t['query_id']]['answerable']]
    report = {'cases': len(cases), 'successful': len(successful), 'errors': len(traces) - len(successful),
              'median_ms': statistics.median(t['elapsed_ms'] for t in successful) if successful else None,
              'cost_usd': None, 'cost_note': 'Usage recorded; set actual provider pricing externally. No inferred dollar cost.',
              'context_evidence_rate': ratio(sum(enough(t['context_chunks'], by_id[t['query_id']]) for t in answerable), len(answerable)),
              'average_context_chars': statistics.mean(len(t['context']) for t in successful) if successful else None}
    if mode == 'retrieval':
        for k in (1, 3):
            report[f'hit_at_{k}'] = ratio(sum(enough(t['results'][:k], by_id[t['query_id']]) for t in answerable), len(answerable))
    else:
        counts = [sum(e['event'] == 'search' for e in t['events']) for t in successful]
        report['tool_use'] = ratio(sum(n > 0 for n in counts), len(successful))
        report['search_call_counts'] = counts
        report['requires_human_review'] = ['answer_grade', 'citation_support', 'abstention_correct', 'context_grade', 'reasons']
    calls = [c for t in traces for c in t.get('provider_calls', [])]
    if mode == 'retrieval' and all(c['endpoint'].startswith('local/') for c in calls):
        report['cost_usd'] = 0
        report['cost_note'] = 'Local retrieval; no paid API calls. Hardware/electricity not priced.'
    report['provider_call_count'] = len(calls)
    return report


def review_template(cases, traces):
    by_id = {q['id']: q for q in cases}
    return [{'query_id': t['query_id'], 'answer_grade': None if by_id[t['query_id']]['answerable'] else 'not_applicable',
             'citation_support': [None] * len(t['citations']), 'context_grade': None,
             'abstention_correct': 'not_applicable' if by_id[t['query_id']]['answerable'] else None,
             'reason': '', 'citation_reasons': [''] * len(t['citations'])}
            for t in traces if t['status'] != 'error']
