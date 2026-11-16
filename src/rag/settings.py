"""Load literal project configuration without executing or expanding values."""
import os
import re
from pathlib import Path

PROJECT_ENV = Path(__file__).resolve().parents[2] / '.env'


def load_project_env(path=PROJECT_ENV):
    """Shell variables take precedence. No interpolation or shell expansion."""
    path = Path(path)
    if not path.exists():
        return
    values = {}
    for number, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[7:].lstrip()
        key, separator, value = line.partition('=')
        key, value = key.strip(), value.strip()
        if not separator or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key):
            raise ValueError(f'Invalid .env setting at line {number}')
        if value.startswith(('"', "'")):
            quote = value[0]
            closing = value.find(quote, 1)
            if closing < 0 or (value[closing+1:].strip() and not value[closing+1:].lstrip().startswith('#')):
                raise ValueError(f'Invalid .env quotation at line {number}')
            value = value[1:closing]
        else:
            value = re.split(r'\s+#', value, maxsplit=1)[0].rstrip()
        if key.startswith('RAG_') or key in ('GROQ_API_KEY', 'OPENAI_API_KEY', 'HF_HUB_OFFLINE'):
            values[key] = value
    for key, value in values.items():
        os.environ.setdefault(key, value)
