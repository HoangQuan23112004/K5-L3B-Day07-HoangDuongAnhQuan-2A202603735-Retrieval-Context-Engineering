import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from src.rag.cli import main
from src.rag.common import load, save
from src.rag.providers import Provider, RateLimitError, retry_delay


class RateLimitTests(unittest.TestCase):
    def limited(self, delay='2'):
        return urllib.error.HTTPError('http://test-only', 429, 'limited', {'Retry-After': delay}, io.BytesIO(b'{}'))

    def test_waits_retry_after_then_succeeds_and_records_attempt(self):
        p = Provider('ollama')
        p.request_interval = 0
        with patch('urllib.request.urlopen', side_effect=[self.limited(), io.StringIO('{}')]) as send, patch('time.sleep') as sleep:
            self.assertEqual(p.post('/api/chat', {'model': 'test-only'}), {})
            sleep.assert_called_once_with(2.0)
            self.assertEqual(send.call_count, 2)
        self.assertEqual(p.calls[0]['status'], 'rate_limited')
        self.assertTrue(p.calls[0]['will_retry'])

    def test_long_quota_wait_is_not_retried_early(self):
        p = Provider('ollama')
        with patch('urllib.request.urlopen', side_effect=self.limited('3600')) as send, patch('time.sleep') as sleep:
            with self.assertRaisesRegex(RateLimitError, '3600s'):
                p.post('/api/chat', {'model': 'test-only'})
            sleep.assert_not_called()
            self.assertEqual(send.call_count, 1)

    def test_retries_are_bounded(self):
        p = Provider('ollama')
        p.request_interval, p.max_retries = 0, 1
        with patch('urllib.request.urlopen', side_effect=[self.limited(), self.limited()]) as send, patch('time.sleep'):
            with self.assertRaises(RateLimitError):
                p.post('/api/chat', {'model': 'test-only'})
            self.assertEqual(send.call_count, 2)
        self.assertFalse(p.calls[-1]['will_retry'])

    def test_retry_delay_rejects_nonfinite_or_malformed_header(self):
        for value in ('nan', 'inf', '-1', 'bad', None):
            self.assertEqual(retry_delay(value, 1), 10)

    def test_resume_reuses_successes_and_retries_only_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            chunks = [{'id': 'c1', 'text': 'Test source.', 'source_id': 'doc', 'source': 'test.txt', 'page': 1, 'metadata': {}}]
            cases = [{'id': name, 'question': name, 'split': 'dev', 'answerable': False, 'absence_reason': 'test only'} for name in ('q1', 'q2')]
            config = {'method': 'bm25', 'top_k': 3, 'budget_chars': 1000, 'max_searches': 2}
            for name, value in [('chunks', chunks), ('cases', cases), ('config', config)]:
                save(root/f'{name}.json', value)
            common = ['--chunks', str(root/'chunks.json'), '--cases', str(root/'cases.json'), '--index', str(root/'unused'),
                      'benchmark', '--config', str(root/'config.json'), '--mode', 'agent', '--split', 'dev']

            def fake_agent(question, provider, retriever, cfg, filters, state):
                state.update(status='abstain', answer='Insufficient evidence', context='', context_chunks=[], context_ids=[], events=[], citations=[])

            with patch('src.rag.cli.run_agent', side_effect=fake_agent):
                self.assertEqual(main(common + ['--output', str(root/'old')]), 0)
            traces = load(root/'old/traces.json')
            traces[1] = {'query_id': 'q2', 'status': 'error', 'error': {'message': '429'}}
            save(root/'old/traces.json', traces)
            with patch('src.rag.cli.run_agent', side_effect=fake_agent) as execute:
                self.assertEqual(main(common + ['--resume-from', str(root/'old'), '--output', str(root/'new')]), 0)
                self.assertEqual(execute.call_count, 1)
                self.assertEqual(execute.call_args.args[0], 'q2')
            resumed = load(root/'new/traces.json')
            self.assertIn('reused_from', resumed[0])
            self.assertEqual(resumed[1]['previous_attempt']['status'], 'error')
            self.assertEqual(load(root/'old/traces.json')[1]['status'], 'error')
            # A changed configuration cannot reuse old results.
            save(root/'config.json', {**config, 'top_k': 6})
            with self.assertRaisesRegex(ValueError, 'Resume requires identical'):
                main(common + ['--resume-from', str(root/'old'), '--output', str(root/'bad')])


if __name__ == '__main__':
    unittest.main()
