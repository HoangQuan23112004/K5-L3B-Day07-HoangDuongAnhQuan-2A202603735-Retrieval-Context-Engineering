import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.rag.settings import load_project_env


class SettingsTests(unittest.TestCase):
    def test_loads_literal_values_without_overriding_shell(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'RAG_CHAT_MODEL': 'shell-model'}, clear=True):
            path = Path(directory) / '.env'
            path.write_text('# comment\nRAG_CHAT_MODEL=file-model\nGROQ_API_KEY="test-only#key" # note\n'
                            "RAG_BASE_URL='https://api.groq.com/openai/v1'\nRAG_PROVIDER=openai # note\n"
                            'export RAG_MODEL_CACHE=C:\\local\\cache\nUNRELATED_SETTING=ignored\n', encoding='utf-8-sig')
            load_project_env(path)
            self.assertEqual(os.environ['RAG_CHAT_MODEL'], 'shell-model')
            self.assertEqual(os.environ['GROQ_API_KEY'], 'test-only#key')
            self.assertEqual(os.environ['RAG_PROVIDER'], 'openai')
            self.assertEqual(os.environ['RAG_MODEL_CACHE'], r'C:\local\cache')
            self.assertNotIn('UNRELATED_SETTING', os.environ)

    def test_missing_file_is_optional(self):
        with tempfile.TemporaryDirectory() as directory:
            load_project_env(Path(directory) / 'missing.env')

    def test_invalid_file_does_not_expose_value_or_partially_load(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            path = Path(directory) / '.env'
            path.write_text('RAG_PROVIDER=openai\nGROQ_API_KEY="secret-test-value\n', encoding='utf-8')
            with self.assertRaises(ValueError) as caught:
                load_project_env(path)
            self.assertNotIn('secret-test-value', str(caught.exception))
            self.assertNotIn('RAG_PROVIDER', os.environ)


if __name__ == '__main__':
    unittest.main()
