# Code

Triển khai tại [`rag/`](rag/):

- `providers.py`: FastEmbed local và HTTP adapter cho Ollama/OpenAI-compatible.
- `qdrant_store.py`, `retrieval.py`: Qdrant/SQLite, dense cosine, BM25, hybrid RRF, context packing.
- `agent.py`: vòng lặp tool calling, search/finish/abstain, citation ID và budget guards.
- `evaluation.py`, `cli.py`: benchmark, trace, audit thủ công, khóa cấu hình trước test.

Chạy từ thư mục gốc: `python -m src.rag --help`. Xem [RUNBOOK](../docs/RUNBOOK.md).
