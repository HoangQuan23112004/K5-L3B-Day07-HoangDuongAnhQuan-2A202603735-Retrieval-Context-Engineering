"""Run from repository root: python -m src.rag --help."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from .agent import run_agent
from .common import digest, load, save, validate_cases, validate_chunks
from .evaluation import retrieval_trace, review_template, summarize
from .providers import Provider, RateLimitError
from .retrieval import Retriever, get_store, provider_identity
from starter.agent_metrics import aggregate
from .settings import load_project_env


def provider(args):
    return Provider(args.provider, args.base_url, args.chat_model, args.embedding_model, embedding_backend=args.embedding_backend)


def identity(args, chunks, cases, config, mode):
    p = provider(args)
    manifest = Path(str(args.index) + '.manifest.json')
    return {'corpus_hash': digest(chunks), 'cases_hash': digest(cases), 'config_hash': digest(config),
            'provider': provider_identity(p), 'chat_model': p.chat_model, 'chat_provider': p.kind,
            'chat_url': p.base_url, 'vector_store': args.vector_store, 'mode': mode,
            'index_manifest_hash': digest(load(manifest)) if manifest.exists() else None}


def main(argv=None):
    load_project_env()
    parser = argparse.ArgumentParser(description='Day 7 Agentic RAG: real models, traceable evidence')
    parser.add_argument('--provider', choices=['ollama', 'openai'], default=os.getenv('RAG_PROVIDER', 'ollama'))
    parser.add_argument('--base-url', default=os.getenv('RAG_BASE_URL'))
    parser.add_argument('--chat-model', default=os.getenv('RAG_CHAT_MODEL', 'qwen2.5:7b'))
    parser.add_argument('--embedding-model', default=os.getenv('RAG_EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2'))
    parser.add_argument('--embedding-backend', choices=['remote', 'fastembed'], default=os.getenv('RAG_EMBEDDING_BACKEND', 'fastembed'))
    parser.add_argument('--vector-store', choices=['sqlite', 'qdrant'], default=os.getenv('RAG_VECTOR_STORE', 'qdrant'))
    parser.add_argument('--chunks', default='data/alice/chunks.json')
    parser.add_argument('--cases', default='data/alice/cases.json')
    parser.add_argument('--index', default='artifacts/qdrant-day6-b')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('validate')
    index = sub.add_parser('index')
    index.add_argument('--batch-size', type=int, default=16)
    index.add_argument('--provenance', required=True, help='Day 6 index/version or honest new-index provenance')
    imp = sub.add_parser('import-index')
    imp.add_argument('--vectors', required=True, help='JSON: embedding_identity, provenance, vectors keyed by chunk ID')
    ask = sub.add_parser('ask')
    ask.add_argument('question')
    ask.add_argument('--config', default='configs/hybrid.json')
    ask.add_argument('--filter', type=json.loads, default=None, help='User-supplied metadata equality filter as JSON')
    ask.add_argument('--output', default='artifacts/answer.json')
    bench = sub.add_parser('benchmark')
    bench.add_argument('--config', required=True)
    bench.add_argument('--split', required=True, choices=['dev', 'test'])
    bench.add_argument('--mode', required=True, choices=['retrieval', 'agent'])
    bench.add_argument('--output', required=True)
    bench.add_argument('--lock', default='artifacts/frozen.json')
    bench.add_argument('--resume-from', type=Path, help='Reuse successful traces from an identical run; retry only error cases into a new output directory')
    audit = sub.add_parser('audit')
    audit.add_argument('--run', required=True, help='Agent benchmark output directory')
    audit.add_argument('--reviews', required=True, help='Completed reviewer labels with reasons and reviewer provenance')
    freeze = sub.add_parser('freeze')
    freeze.add_argument('--selected', required=True)
    freeze.add_argument('--baseline', default='configs/bm25.json')
    freeze.add_argument('--dev-results', nargs='+', required=True, help='Dev output directories for >=3 methods and >=2 variants')
    freeze.add_argument('--reason', required=True, help='Selection rationale using declared criteria and human dev review')
    freeze.add_argument('--retrieval-only', action='store_true', help='Freeze retrieval evaluation only; agent tests still require an audited agent freeze')
    freeze.add_argument('--output', default='artifacts/frozen.json')
    args = parser.parse_args(argv)
    chunks = load(args.chunks)
    validate_chunks(chunks)
    if args.command == 'validate':
        print(json.dumps(validate_cases(chunks, load(args.cases), minimum=True), indent=2))
        return 0
    p = provider(args)
    if args.command == 'audit':
        directory = Path(args.run)
        manifest = load(directory / 'manifest.json')
        if manifest['mode'] != 'agent':
            raise ValueError('Audit requires an agent run')
        cases = load(args.cases)
        if digest(cases) != manifest['identity']['cases_hash'] or digest(chunks) != manifest['identity']['corpus_hash']:
            raise ValueError('Audit dataset differs from the run')
        cases = [q for q in cases if q['split'] == manifest['split']]
        traces = load(directory / 'traces.json')
        reviews = load(args.reviews)
        successful = {t['query_id'] for t in traces if t['status'] != 'error'}
        if {r['query_id'] for r in reviews} != successful:
            raise ValueError('Reviews must cover every successful query exactly once')
        for review in reviews:
            if not isinstance(review.get('reason'), str) or not review['reason'].strip():
                raise ValueError('Each review requires a human reason')
            if type(review.get('context_grade')) is not int or review['context_grade'] not in (0, 1, 2):
                raise ValueError('context_grade must be 0, 1 or 2')
            reasons = review.get('citation_reasons')
            if not isinstance(reasons, list) or len(reasons) != len(review.get('citation_support', [])) or any(not isinstance(r, str) or not r.strip() for r in reasons):
                raise ValueError('Each citation requires a support reason')
        result = aggregate(cases, traces, reviews)
        result.update(context_grades={str(i): sum(r['context_grade'] == i for r in reviews) for i in (0, 1, 2)},
                      reviews_hash=digest(reviews), traces_hash=digest(traces),
                      review_provenance={'ai_assisted': sum(r.get('review_type') == 'ai_assisted' for r in reviews),
                                         'human_verified': sum(r.get('human_verified') is True for r in reviews)})
        save(directory / 'reviews.json', reviews)
        save(directory / 'audit.json', result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command in ('index', 'import-index'):
        started = time.perf_counter()
        if args.command == 'index':
            if args.batch_size < 1:
                raise ValueError('batch-size must be positive')
            vectors = []
            for start in range(0, len(chunks), args.batch_size):
                vectors.extend(p.embed([c['text'] for c in chunks[start:start + args.batch_size]]))
                print(f'Embedded {len(vectors)}/{len(chunks)}', flush=True)
            provenance = args.provenance
        else:
            exported = load(args.vectors)
            if exported.get('embedding_identity') != provider_identity(p):
                raise ValueError('Export embedding_identity does not match query provider/model/URL')
            if set(exported['vectors']) != {c['id'] for c in chunks}:
                raise ValueError('Export vector IDs must exactly match corpus IDs')
            vectors = [exported['vectors'][c['id']] for c in chunks]
            provenance = exported['provenance']
        if not isinstance(provenance, str) or not provenance.strip():
            raise ValueError('Index provenance required')
        result = get_store(args.index, args.vector_store).create(chunks, vectors, provider_identity(p), provenance)
        result.update(elapsed_ms=(time.perf_counter() - started) * 1000, provider_calls=p.calls)
        save(str(args.index) + '.manifest.json', result)
        print(json.dumps(result, indent=2))
        return 0
    if args.command == 'freeze':
        cases = load(args.cases)
        selected, baseline = load(args.selected), load(args.baseline)
        expected = identity(args, chunks, cases, selected, 'agent')
        manifests = []
        for directory in args.dev_results:
            manifest = load(Path(directory) / 'manifest.json')
            if manifest['split'] != 'dev' or manifest['identity']['corpus_hash'] != expected['corpus_hash'] or manifest['identity']['cases_hash'] != expected['cases_hash']:
                raise ValueError('Dev results must use the same corpus and benchmark')
            for key in ('provider', 'chat_model', 'chat_provider', 'chat_url', 'vector_store', 'index_manifest_hash'):
                if manifest['identity'][key] != expected[key]:
                    raise ValueError('Dev results use different model settings')
            summary = load(Path(directory) / 'summary.json')
            if summary['errors'] or not summary['successful']:
                raise ValueError('Resolve dev run errors before freezing')
            if manifest['mode'] == 'agent':
                audit_result = load(Path(directory) / 'audit.json')
                if audit_result['reviews_hash'] != digest(load(Path(directory) / 'reviews.json')) or audit_result['traces_hash'] != digest(load(Path(directory) / 'traces.json')):
                    raise ValueError('Audit no longer matches traces/reviews')
            manifests.append(manifest)
        if len({m['config']['method'] for m in manifests if m['mode'] == 'retrieval'}) < 3:
            raise ValueError('Freeze requires retrieval dev results for three methods')
        if len({m['identity']['config_hash'] for m in manifests if m['mode'] == 'retrieval'}) < 3:
            raise ValueError('Freeze requires baseline plus two improvement configurations')
        for cfg in (selected, baseline):
            mode = 'retrieval' if args.retrieval_only else 'agent'
            if not any(m['mode'] == mode and m['identity']['config_hash'] == digest(cfg) for m in manifests):
                raise ValueError(f'Freeze requires baseline and selected {mode} dev runs')
        if Path(args.output).exists():
            raise ValueError('Lock already exists; preserve it and use a new evaluation protocol for further tuning')
        save(args.output, {'identity': expected, 'allowed_config_hashes': [digest(selected), digest(baseline)],
                           'selected': selected, 'baseline': baseline, 'reason': args.reason, 'dev_manifests': manifests,
                           'scope': 'retrieval' if args.retrieval_only else 'agent'})
        print(f'Frozen: {args.output}')
        return 0
    config = load(args.config)
    if args.command == 'ask':
        state = {'question': args.question, 'config': config}
        try:
            run_agent(args.question, p, Retriever(chunks, p, config, args.index, args.vector_store), config, args.filter, state)
        except Exception as exc:
            state.update(status='error', error={'type': type(exc).__name__, 'message': str(exc)})
            save(args.output, state)
            raise
        save(args.output, state)
        print(state['answer'])
        return 0
    cases = load(args.cases)
    selected_cases = [q for q in cases if q['split'] == args.split]
    validate_cases(chunks, selected_cases)
    run_identity = identity(args, chunks, cases, config, args.mode)
    previous = {}
    if args.resume_from:
        old_manifest = load(args.resume_from / 'manifest.json')
        if old_manifest['identity'] != run_identity or old_manifest['split'] != args.split or old_manifest['mode'] != args.mode:
            raise ValueError('Resume requires identical corpus, cases, index, model, config, split and mode')
        old_traces = load(args.resume_from / 'traces.json')
        previous = {t['query_id']: t for t in old_traces}
        if len(previous) != len(old_traces) or set(previous) != {q['id'] for q in selected_cases}:
            raise ValueError('Resume source must have one trace per selected query')
        allowed = ('answered', 'abstain', 'error') if args.mode == 'agent' else ('retrieved', 'error')
        if any(t.get('status') not in allowed for t in old_traces):
            raise ValueError('Resume source has an invalid trace status')
    if args.split == 'test':
        frozen = load(args.lock)
        if args.mode == 'agent' and frozen.get('scope') != 'agent':
            raise ValueError('Agent test requires an audited agent freeze, not a retrieval-only lock')
        for key in ('corpus_hash', 'cases_hash', 'provider', 'chat_model', 'chat_provider', 'chat_url', 'vector_store', 'index_manifest_hash'):
            if run_identity[key] != frozen['identity'][key]:
                raise ValueError(f'Test differs from frozen {key}')
        if digest(config) not in frozen['allowed_config_hashes']:
            raise ValueError('Only frozen baseline and selected configurations may run on test')
    output = Path(args.output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output directory is not empty; choose a new run directory')
    output.mkdir(parents=True, exist_ok=True)
    save(output / 'manifest.json', {'identity': run_identity, 'config': config, 'split': args.split, 'mode': args.mode,
                                   'python': sys.version, 'index_manifest': str(args.index) + '.manifest.json',
                                   'resume_from': str(args.resume_from) if args.resume_from else None})
    traces = []
    retriever = None
    try:
        retriever = Retriever(chunks, p, config, args.index, args.vector_store)
    except Exception as exc:
        # Keep setup failures as per-case errors, never as empty successful retrieval.
        setup_error = {'type': type(exc).__name__, 'message': str(exc)}
    with (output / 'traces.jsonl').open('w', encoding='utf-8') as stream:
        rate_limited = None
        for case in selected_cases:
            old = previous.get(case['id'])
            if old and old['status'] != 'error':
                state = {**old, 'reused_from': str(args.resume_from)}
                traces.append(state)
                stream.write(json.dumps(state, ensure_ascii=False) + '\n')
                stream.flush()
                print(f"{case['id']}: {state['status']} (reused)", flush=True)
                continue
            state = {'query_id': case['id'], 'question': case['question'], 'events': [], 'citations': []}
            start = time.perf_counter()
            call_start = len(p.calls)
            try:
                if rate_limited is not None:
                    state.update(status='error', error=rate_limited, events=[{'event': 'skipped_rate_limit'}])
                elif retriever is None:
                    state.update(status='error', error=setup_error)
                elif args.mode == 'retrieval':
                    state.update(retrieval_trace(case, retriever, config))
                else:
                    run_agent(case['question'], p, retriever, config, case.get('filter'), state)
            except RateLimitError as exc:
                rate_limited = {'type': type(exc).__name__, 'message': str(exc)}
                state.update(status='error', error=rate_limited)
            except Exception as exc:
                state.update(status='error', error={'type': type(exc).__name__, 'message': str(exc)})
            if old:
                state['previous_attempt'] = old
            state['elapsed_ms'] = (time.perf_counter() - start) * 1000
            state['provider_calls'] = p.calls[call_start:]
            traces.append(state)
            stream.write(json.dumps(state, ensure_ascii=False) + '\n')
            stream.flush()
            print(f"{case['id']}: {state['status']}", flush=True)
    report = summarize(selected_cases, traces, args.mode)
    save(output / 'traces.json', traces)
    save(output / 'summary.json', report)
    if args.mode == 'agent':
        save(output / 'reviews.template.json', review_template(selected_cases, traces))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report['errors'] else 0
