"""Offline regression tests; synthetic vectors/controllers measure code only."""
import json
import tempfile
import unittest
import importlib.util
import io
from pathlib import Path
from unittest.mock import patch

from src.rag.agent import run_agent
from src.rag.cli import main
from src.rag.common import enough, validate_cases
from src.rag.evaluation import summarize
from src.rag.providers import Provider
from src.rag.retrieval import BM25, Retriever, VectorStore, pack_context, provider_identity

CHUNKS = [
    {'id': 'c1', 'text': 'TLS handshake uses cryptographic keys.', 'source_id': 'doc', 'source': 'doc.txt', 'page': 1, 'metadata': {'year': 2018}},
    {'id': 'c2', 'text': 'Ticket lifetime is limited.', 'source_id': 'doc', 'source': 'doc.txt', 'page': 2, 'metadata': {'year': 2020}},
]
CONFIG = {'method': 'bm25', 'top_k': 3, 'budget_chars': 1000, 'max_searches': 2}


def call(name, **args):
    return {'tool_calls': [{'function': {'name': name, 'arguments': json.dumps(args)}}]}


class FakeProvider:
    kind, base_url, embedding_model = 'test-only', 'offline', 'test-only'
    def __init__(self, actions=()):
        self.actions, self.calls, self.messages = iter(actions), [], []
    def embed(self, texts):
        return [[1., 0.] for _ in texts]
    def embed_query(self, query):
        return self.embed([query])[0]
    def chat(self, messages, tools):
        self.messages.append(messages)
        return next(self.actions)


class RagTests(unittest.TestCase):
    def test_bm25_unicode_filters_and_zero_matches(self):
        index = BM25(CHUNKS)
        self.assertEqual(index.search('TLS handshake')[0]['id'], 'c1')
        self.assertEqual(index.search('TLS', filters={'year': 2020}), [])
        self.assertEqual(index.search('unrelated'), [])
        c = {**CHUNKS[0], 'text': 'Hoàn tiền'}
        self.assertEqual(BM25([c]).search('Hoàn')[0]['id'], 'c1')

    def test_context_budget_deduplicates_and_keeps_full_sources(self):
        context, rows = pack_context(CHUNKS + CHUNKS, 1000)
        self.assertEqual(len(rows), 2)
        self.assertIn('page=1', context)
        self.assertEqual(pack_context(CHUNKS, 1), ('', []))

    def test_sqlite_dense_model_corpus_dimension_guards(self):
        p = FakeProvider()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'v.sqlite'
            store = VectorStore(path)
            store.create(CHUNKS, [[1., 0.], [0., 1.]], provider_identity(p), 'unit-test-only')
            r = Retriever(CHUNKS, p, {**CONFIG, 'method': 'dense'}, path)
            self.assertEqual(r.search('q')[0]['id'], 'c1')
            self.assertEqual(r.search('q', filters={'page': 2})[0]['id'], 'c2')
            with self.assertRaises(ValueError):
                store.read(CHUNKS, {'wrong': 'model'})
            with self.assertRaises(ValueError):
                store.read(CHUNKS[:1], provider_identity(p))
            p.embed = lambda texts: [[1., 0., 0.]]
            with self.assertRaises(ValueError):
                r.search('q')

    def test_rrf_uses_ranks_and_deduplicates(self):
        p = FakeProvider()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'v.sqlite'
            VectorStore(path).create(CHUNKS, [[1., 0.], [0., 1.]], provider_identity(p), 'test-only')
            r = Retriever(CHUNKS, p, {**CONFIG, 'method': 'hybrid'}, path)
            rows = r.search('TLS')
            self.assertEqual(rows[0]['component_ranks'], {'dense': 1, 'bm25': 1})
            self.assertAlmostEqual(rows[0]['score'], 2/61)
            self.assertEqual(len({c['id'] for c in rows}), len(rows))

    def test_vector_store_rejects_nonfinite_zero_and_bad_dimensions(self):
        with tempfile.TemporaryDirectory() as temp:
            store = VectorStore(Path(temp) / 'v.sqlite')
            for vectors in ([[float('nan'), 0], [0, 1]], [[0, 0], [0, 1]], [[1], [0, 1]]):
                with self.assertRaises(ValueError):
                    store.create(CHUNKS, vectors, {}, 'test-only')

    def retriever(self):
        return Retriever(CHUNKS, FakeProvider(), CONFIG, 'unused.sqlite')

    def test_agent_cites_and_never_receives_gold(self):
        p = FakeProvider([call('search', query='TLS'), call('finish', answer='Uses keys [c1]', citations=['c1'])])
        result = run_agent('How?', p, self.retriever(), CONFIG)
        self.assertEqual(result['status'], 'answered')
        self.assertNotIn('expected_answer', json.dumps(p.messages))
        self.assertEqual(result['context_ids'], ['c1'])

    def test_agent_unknown_citation_or_extra_marker_abstains(self):
        for answer, citations in [('Fact [bad]', ['bad']), ('Fact [c1] [bad]', ['c1'])]:
            p = FakeProvider([call('search', query='TLS'), call('finish', answer=answer, citations=citations)])
            self.assertEqual(run_agent('q', p, self.retriever(), CONFIG)['status'], 'abstain')

    def test_agent_renders_valid_structured_citations(self):
        p = FakeProvider([call('search', query='TLS'), call('finish', answer='Uses keys.', citations=['c1'])])
        result = run_agent('q', p, self.retriever(), CONFIG)
        self.assertEqual(result['status'], 'answered')
        self.assertEqual(result['answer'], 'Uses keys. [c1]')
        self.assertIn('citation_formatting', [e['event'] for e in result['events']])

    def test_ollama_native_tool_result_preserves_object_arguments(self):
        p = FakeProvider([call('search', query='TLS'), call('finish', answer='Uses keys.', citations=['c1'])])
        p.kind = 'ollama'
        result = run_agent('q', p, self.retriever(), CONFIG)
        self.assertEqual(result['status'], 'answered')
        self.assertEqual(p.messages[1][-1]['tool_name'], 'search')
        self.assertEqual(p.messages[1][-2]['tool_calls'][0]['function']['arguments'], {'query': 'TLS'})

    def test_structured_citation_formatting_rejects_untrusted_ids(self):
        for answer, citations in [('Fact', ['bad']), ('Fact', []), ('Fact', ['c1', 'c1']),
                                  ('Fact [c1]', ['c1', 'c2'])]:
            p = FakeProvider([call('search', query='TLS Ticket'), call('finish', answer=answer, citations=citations)])
            result = run_agent('q', p, self.retriever(), CONFIG)
            self.assertEqual(result['status'], 'abstain')
            self.assertEqual(result['answer'], 'Không thể xác thực trích dẫn cho câu trả lời.')
            self.assertNotIn('citation_formatting', [e['event'] for e in result['events']])

    def test_agent_abstains_only_after_search(self):
        p = FakeProvider([call('search', query='not-found'), call('abstain', reason='No evidence')])
        self.assertEqual(run_agent('q', p, self.retriever(), CONFIG)['status'], 'abstain')
        with self.assertRaises(ValueError):
            run_agent('q', FakeProvider([call('abstain', reason='No evidence')]), self.retriever(), CONFIG)

    def test_latest_search_can_replace_stale_context(self):
        p = FakeProvider([call('search', query='TLS'), call('search', query='Ticket'),
                          call('finish', answer='Limited [c2]', citations=['c2'])])
        result = run_agent('q', p, self.retriever(), {**CONFIG, 'budget_chars': 90})
        self.assertEqual(result['context_ids'], ['c2'])
        self.assertEqual(result['status'], 'answered')
        for messages in p.messages:
            tools = [m for m in messages if m['role'] == 'tool']
            self.assertLessEqual(len(tools), 1)
            for tool in tools:
                self.assertLessEqual(len(json.loads(tool['content'])['context']), 90)
                self.assertEqual(tool['tool_call_id'], messages[-2]['tool_calls'][0]['id'])

    def test_search_limit_and_error_preserve_partial_trace(self):
        p = FakeProvider([call('search', query='TLS')] * 3)
        result = run_agent('q', p, self.retriever(), CONFIG)
        self.assertEqual(result['events'][-1]['event'], 'search_limit')
        state = {}
        r = self.retriever()
        r.search = lambda *args, **kw: (_ for _ in ()).throw(ConnectionError('offline'))
        with self.assertRaises(ConnectionError):
            run_agent('q', FakeProvider([call('search', query='TLS')]), r, CONFIG, trace=state)
        self.assertEqual(state['events'][-1]['event'], 'search')
        self.assertIn('elapsed_ms', state)

    def test_required_evidence_groups_and_unanswerable_denominator(self):
        q = {'id': 'q', 'split': 'dev', 'question': 'q', 'answerable': True, 'expected_answer': 'a',
             'evidence_groups': [[{'source_id': 'doc', 'page': 1, 'evidence': 'TLS'}],
                                 [{'source_id': 'doc', 'page': 2, 'evidence': 'Ticket'}]]}
        self.assertFalse(enough(CHUNKS[:1], q))
        self.assertTrue(enough(CHUNKS, q))
        missing = {'id': 'n', 'split': 'dev', 'question': 'n', 'answerable': False, 'absence_reason': 'Absent after corpus review'}
        validate_cases(CHUNKS, [q, missing])
        traces = [{'query_id': cid, 'status': 'retrieved', 'results': CHUNKS, 'context_chunks': CHUNKS,
                   'context': 'abc', 'elapsed_ms': 1} for cid in ['q', 'n']]
        summary = summarize([q, missing], traces, 'retrieval')
        self.assertEqual(summary['hit_at_1']['N'], 1)
        self.assertEqual(summary['hit_at_1']['n'], 0)
        self.assertEqual(summary['hit_at_3']['n'], 1)

    def test_test_run_requires_frozen_configuration(self):
        q = {'id': 'q', 'split': 'test', 'question': 'TLS?', 'answerable': False, 'absence_reason': 'test-only'}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name, value in [('chunks', CHUNKS), ('cases', [q]), ('config', CONFIG)]:
                (root / (name + '.json')).write_text(json.dumps(value), encoding='utf-8')
            with self.assertRaises(FileNotFoundError):
                main(['--chunks', str(root/'chunks.json'), '--cases', str(root/'cases.json'), 'benchmark',
                      '--split', 'test', '--mode', 'retrieval', '--config', str(root/'config.json'),
                      '--lock', str(root/'missing.json'), '--output', str(root/'run')])
            self.assertFalse((root/'run').exists())

    def test_openai_embedding_rows_are_ordered(self):
        p = Provider('openai', embedding_model='test-only')
        with patch.object(p, 'post', return_value={'data': [{'index': 1, 'embedding': [0, 1]}, {'index': 0, 'embedding': [1, 0]}]}):
            self.assertEqual(p.embed(['a', 'b']), [[1., 0.], [0., 1.]])

    def test_groq_key_is_separate_from_openai(self):
        p = Provider('openai', base_url='https://api.groq.com/openai/v1')
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'openai-test-only'}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'GROQ_API_KEY'):
                p.post('/chat/completions', {'model': 'test-only'})
        with patch.dict('os.environ', {'GROQ_API_KEY': 'groq-test-only'}, clear=True):
            with patch('urllib.request.urlopen', return_value=io.StringIO('{"usage": {}}')) as send:
                p.post('/chat/completions', {'model': 'test-only'})
                self.assertEqual(send.call_args.args[0].get_header('Authorization'), 'Bearer groq-test-only')
                self.assertEqual(send.call_args.args[0].get_header('User-agent'), 'Day7-AgenticRAG/1.0')

    def test_groq_requests_one_required_tool_call(self):
        p = Provider('openai', base_url='https://api.groq.com/openai/v1', chat_model='test-only')
        with patch.object(p, 'post', return_value={'choices': [{'message': {'tool_calls': []}}]}) as send:
            p.chat([], [])
            body = send.call_args.args[1]
            self.assertEqual(body['tool_choice'], 'required')
            self.assertFalse(body['parallel_tool_calls'])

    def test_corpus_contract_and_minimum(self):
        root = Path(__file__).resolve().parents[1] / 'data/alice'
        from src.rag.common import load
        counts = validate_cases(load(root/'chunks.json'), load(root/'cases.json'), minimum=True)
        self.assertEqual(sum(counts.values()), 24)

    def test_day6_conversion_preserves_ids_text_and_metadata(self):
        from src.rag.common import load
        root = Path(__file__).resolve().parents[1]
        source = [json.loads(line) for line in (root/'vendor/day6/results/chunks_B.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
        converted = load(root/'data/alice/chunks.json')
        self.assertEqual(len(source), 238)
        for before, after in zip(source, converted):
            for key in ('text', 'metadata', 'page', 'source'):
                self.assertEqual(before[key], after[key])
            self.assertEqual(before['chunk_id'], after['id'])
        validate_cases(converted, load(root/'data/alice/cases.json'), minimum=True)

    @unittest.skipUnless(importlib.util.find_spec('qdrant_client'), 'Install requirements.txt for Qdrant integration test')
    def test_qdrant_real_store_roundtrip_and_filters(self):
        from src.rag.qdrant_store import QdrantStore
        with tempfile.TemporaryDirectory() as temp:
            store = QdrantStore(Path(temp)/'qdrant')
            store.create(CHUNKS, [[1., 0.], [0., 1.]], {'model': 'test-only'}, 'unit-test-only')
            self.assertEqual(store.search([1., 0.], 2, {})[0]['id'], 'c1')
            self.assertEqual(store.search([1., 0.], 2, {'year': 2020})[0]['id'], 'c2')
            self.assertEqual(store.read(CHUNKS, {'model': 'test-only'})[0]['dimension'], 2)
            with self.assertRaises(ValueError):
                store.create(CHUNKS, [[1., 0.], [0., 1.]], {}, 'test-only')


if __name__ == '__main__':
    unittest.main()
