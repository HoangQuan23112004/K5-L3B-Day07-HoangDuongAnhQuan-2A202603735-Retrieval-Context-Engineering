# Dot-source this script to keep configuration in the current terminal:
# . ./scripts/use-groq.ps1
$env:RAG_PROVIDER = 'openai'
$env:RAG_BASE_URL = 'https://api.groq.com/openai/v1'
$env:RAG_CHAT_MODEL = 'openai/gpt-oss-20b'
$env:RAG_EMBEDDING_BACKEND = 'fastembed'
$env:RAG_EMBEDDING_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
$env:RAG_VECTOR_STORE = 'qdrant'
Write-Host 'Groq configured. Set GROQ_API_KEY in this terminal, then run ./scripts/run.ps1 ask ...'
