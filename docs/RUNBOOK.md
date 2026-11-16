# Cách chạy dự án

## 1. Môi trường

Python 3.11+; phiên chạy đã kiểm tra bằng Python 3.12.10 trên Windows. Retrieval dùng CPU local, không cần Docker/API key.

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
./.venv/Scripts/python.exe -m unittest discover -s tests -v
./.venv/Scripts/python.exe -X utf8 -m src.rag validate
```

Nếu lệnh `python` trỏ vào Windows Store, dùng đường dẫn Python thật hoặc `py -3.12`; tại máy hiện tại có `C:/Users/admin/AppData/Local/Programs/Python/Python312/python.exe`. `scripts/run.ps1` ưu tiên `.venv` và bật UTF-8. Linux/macOS dùng `.venv/bin/python -m src.rag ...` thay PowerShell wrapper.

`requirements.txt` pin hai thư viện chính; toàn bộ phiên bản đã chạy nằm tại `results/environment.json` và `requirements-lock.txt`. Máy hiện tại chặn chạy `.ps1`, vì vậy các lệnh chính bên dưới gọi Python trực tiếp.

## 2. Tái dùng Day 6

Đã lưu snapshot dữ liệu cần thiết ở `vendor/day6/`, commit nguồn được ghi trong `data/alice/manifest.json`. Chạy lại phép chuyển schema mà không đổi chunk:

```powershell
./.venv/Scripts/python.exe scripts/prepare_day6.py
./.venv/Scripts/python.exe -X utf8 -m src.rag validate
./.venv/Scripts/python.exe -X utf8 -m src.rag index --provenance 'Rebuild Day 6 B at commit 82080a89e87cf6eeab2c9709d8c50276ce8dd2c7; original snapshot unavailable'
```

Lần đầu FastEmbed tải model ONNX từ Hugging Face, cần Internet. Mặc định cache tại `artifacts/model-cache/`, Qdrant tại `artifacts/qdrant-day6-b/`, collection `alice_B`. Qdrant không ghi đè thư mục index đã có; khi cần tái tạo, chọn `--index artifacts/qdrant-rebuild-2` trước tên lệnh. Các lệnh benchmark/freeze/test của cùng thí nghiệm phải cùng `--index`.

Đã có index thật trong workspace hiện tại. Không chạy lại `index` khi chỉ muốn truy xuất. Qdrant/cache không commit vì có thể tái tạo; giữ manifest cùng kết quả để kiểm chứng.

Schema chunk chuẩn: `id`, `text`, `source_id`, `source`, `page`, `metadata`. `page` của Alice là số đơn vị nội dung logic từ Day 6. Công cụ giữ nguyên text, chunk ID, nguồn và metadata. Xem giải thích hash LF/CRLF trong `vendor/day6/README.md`.

Nếu có bộ vector Day 6 xuất JSON, có thể nhập sang Qdrant/SQLite thay vì tính lại. Định dạng:

```json
{
  "embedding_identity": {
    "provider": "fastembed",
    "model": "sentence-transformers/all-MiniLM-L6-v2",
    "query_method": "query_embed"
  },
  "provenance": "Day 6 collection and snapshot identifier",
  "vectors": {"actual-chunk-id": [0.1, 0.2]}
}
```

Ví dụ trên chỉ minh họa schema, vector thật phải đủ 384 chiều, đúng tất cả chunk ID và đúng model. Lệnh: `./.venv/Scripts/python.exe -X utf8 -m src.rag import-index --vectors path/to/export.json`. Không dùng vector minh họa hoặc ngẫu nhiên để benchmark.

## 3. Benchmark retrieval

Các kết quả có sẵn tại `results/alice/`. Để tái lập, dùng **thư mục output mới**; chương trình từ chối ghi đè một run đã có.

```powershell
# Sau khi model đã tải, tránh các request kiểm tra mạng không cần thiết:
$env:HF_HUB_OFFLINE = '1'
./.venv/Scripts/python.exe scripts/experiments.py dev --output results/reproduction
# Đọc lỗi dev, các trace và giao thức trước khi chốt:
./.venv/Scripts/python.exe scripts/experiments.py finalize --output results/reproduction
```

`dev` chạy BM25/dense/hybrid/hybrid-wide/BM25-wide/BM25-small trên cùng 17 câu. `finalize` chọn theo tiêu chí đã ghi trong `PROTOCOL.md`, tạo `frozen-retrieval.json` rồi chạy baseline và selected trên cùng 7 câu test mới. Không thay cấu hình dựa trên kết quả test. Nếu thay dữ liệu/cases/index sau khi khóa, CLI từ chối chạy test với lock cũ.

Mỗi thư mục run chứa `manifest.json`, `summary.json`, `traces.json`, `traces.jsonl`. JSONL ghi sau từng câu để giữ tiến độ; lỗi có `status: error`, không chuyển thành kết quả retrieval rỗng. Top-3 dùng so sánh ranking; `context_chunks` là context thật được đóng gói ở top-k cấu hình. Câu thiếu evidence không nằm trong mẫu số Hit@k/context rate.

Một lần chạy riêng:

```powershell
./.venv/Scripts/python.exe -X utf8 -m src.rag benchmark --config configs/hybrid.json --split dev --mode retrieval --output results/new-hybrid-dev
```

## 4. Chạy agent Groq

Groq đã được cấu hình qua `.env`: `RAG_PROVIDER=openai`, `RAG_BASE_URL=https://api.groq.com/openai/v1`, `RAG_CHAT_MODEL=openai/gpt-oss-20b`. Điền `GROQ_API_KEY` trong `.env`, giữ FastEmbed cho embedding. Không cần đặt key trong mã hoặc gửi key vào chat.

Đã chạy agent thật và lưu trace/audit tại `results/final-agent/`. Model cần hỗ trợ function tool calling và trả một tool call mỗi lượt. Prompt yêu cầu tìm bằng chứng trước, dùng `finish` để trả answer/citations hoặc `abstain` khi thiếu evidence. Kết quả tool được gửi theo cặp assistant/tool, giữ context tích lũy có budget.

Chạy một câu qua Groq với `.env` hiện tại:

```powershell
./.venv/Scripts/python.exe -X utf8 -m src.rag ask 'What was in the ORANGE MARMALADE jar?' --config configs/bm25-wide.json
```

Các cấu hình Ollama/OpenAI dưới đây chỉ dùng khi chủ động chọn provider khác.

Ollama, sau khi bạn đã cài/chạy server và có model tool calling:

```powershell
$env:RAG_PROVIDER = 'ollama'
$env:RAG_BASE_URL = 'http://localhost:11434'
$env:RAG_CHAT_MODEL = '<ten-model-da-tai>'
./.venv/Scripts/python.exe -X utf8 -m src.rag ask 'What was in the ORANGE MARMALADE jar?' --config configs/bm25-wide.json --output artifacts/answer.json
```

API tương thích OpenAI:

```powershell
$env:RAG_PROVIDER = 'openai'
$env:RAG_BASE_URL = 'https://api.openai.com/v1'
$env:RAG_CHAT_MODEL = '<ten-model-ho-tro-tool-calling>'
# Cấu hình RAG_API_KEY hoặc OPENAI_API_KEY qua biến môi trường cục bộ.
./.venv/Scripts/python.exe -X utf8 -m src.rag ask 'Why did Alice dislike the book?' --config configs/bm25-wide.json
```

Chat provider tách biệt với embedding. **Giữ FastEmbed all-MiniLM-L6-v2 cho index Alice** khi đổi chat model; không đổi sang OpenAI embedding cho query trên index cũ. Nếu cố ý dùng remote embedding, đặt `RAG_EMBEDDING_BACKEND=remote`, model phù hợp và tạo index riêng. CLI tự đọc `.env` ở thư mục gốc; copy `.env.example` sang `.env` nếu chưa có. Biến môi trường terminal được ưu tiên hơn file.

Trace lưu tool calls, query, filter, kết quả, context cuối, citation, elapsed time và provider usage. Credential không ghi vào trace. Kết quả chỉ được đánh dấu `answered` khi citation ID có trong context và trong answer; kiểm tra này chưa chứng minh nguồn hỗ trợ nội dung.

## 5. Chấm agent và chốt test

Đợt hoàn tất của dự án dùng các run tại `results/final-agent/`: baseline dev `bm25-dev-v3`, selected dev `bm25-wide-dev`, baseline test `bm25-test`, selected test `bm25-wide-test-v2`; lock `frozen-agent.json`. Các file `reviews.json`/`audit.json` lưu nhãn và kết quả, với `review_type=ai_assisted`, `human_verified=true` sau khi học viên xác nhận đã kiểm tra lại toàn bộ. Xác nhận được lưu tại `results/final-agent/human-verification.json`; nhãn mới hoặc nhãn đã thay đổi không tự được xác nhận. Xem `TONG_HOP_QUA_TRINH_VA_KET_QUA.md` và `results/final-agent/REVIEW_DETAILS.md` để đọc kết quả. Các lệnh dưới mô tả quy trình cho run mới; không ghi đè thư mục kết quả đã có.

Tái tổng hợp báo cáo từ kết quả cuối đã lưu:

```powershell
./.venv/Scripts/python.exe scripts/build_final_report.py
```

Groq có thể trả HTTP 429 khi vượt giới hạn request/token. Adapter giãn cách request Groq 3 giây, retry tối đa 3 lần theo `Retry-After` (tối đa 60 giây mỗi lần; thiếu header thì backoff 5/10/20 giây). Thời gian chờ nằm trong elapsed time và trace giữ các lần bị giới hạn. Nếu quota cần chờ lâu hơn hoặc hết retry, run ghi lỗi và dừng gửi thêm request cho các câu còn lại.

Nếu run cũ có câu lỗi, chạy tiếp vào **thư mục mới** với `--resume-from`; code giữ nguyên câu đã `answered`/`abstain`, chỉ gọi lại câu `error`, kiểm tra cùng model/config/index/dataset và giữ trace lần thử cũ. Ví dụ:

```powershell
./.venv/Scripts/python.exe -X utf8 -m src.rag benchmark --config configs/bm25.json --split dev --mode agent --resume-from artifacts/agent-bm25-dev --output artifacts/agent-bm25-dev-resumed
```

Khi audit/freeze, dùng thư mục resumed mới cho cấu hình đó. Chỉ chốt khi `errors=0`; tỷ lệ 100% trên phần chạy thành công không thay cho hoàn thành toàn bộ run.

```powershell
./.venv/Scripts/python.exe -X utf8 -m src.rag benchmark --config configs/bm25.json --split dev --mode agent --output artifacts/agent-bm25-dev
./.venv/Scripts/python.exe -X utf8 -m src.rag benchmark --config configs/bm25-wide.json --split dev --mode agent --output artifacts/agent-selected-dev
```

Sao chép `reviews.template.json`, đọc từng trace và điền nhãn: `answer_grade` 0/1/2, `context_grade` 0/1/2, `citation_support` boolean tương ứng từng citation, `citation_reasons`, `abstention_correct` boolean cho câu thiếu evidence, và `reason`. Không tự suy nhãn từ ID hay từ việc hệ thống từ chối. Giữ `not_applicable` ở trường không áp dụng.

```powershell
./.venv/Scripts/python.exe -X utf8 -m src.rag audit --run artifacts/agent-bm25-dev --reviews artifacts/bm25-reviews.json
./.venv/Scripts/python.exe -X utf8 -m src.rag audit --run artifacts/agent-selected-dev --reviews artifacts/selected-reviews.json
./.venv/Scripts/python.exe -X utf8 -m src.rag freeze --selected configs/bm25-wide.json --baseline configs/bm25.json --reason '<ly-do-tu-ket-qua-dev-va-audit>' --dev-results artifacts/agent-bm25-dev artifacts/agent-selected-dev results/alice/bm25-dev results/alice/dense-dev results/alice/hybrid-dev results/alice/bm25-wide-dev --output artifacts/frozen-agent.json
./.venv/Scripts/python.exe -X utf8 -m src.rag benchmark --config configs/bm25.json --split test --mode agent --lock artifacts/frozen-agent.json --output artifacts/agent-baseline-test
./.venv/Scripts/python.exe -X utf8 -m src.rag benchmark --config configs/bm25-wide.json --split test --mode agent --lock artifacts/frozen-agent.json --output artifacts/agent-selected-test
```

**Nếu đổi chat provider/model so với manifests retrieval có sẵn**, hãy chạy lại retrieval dev với kết nối model mới trong thư mục khác trước khi freeze agent; lock kiểm tra cả cấu hình model. Nếu bạn đã dùng câu test mới để chỉnh agent, cần tạo test mới trước đánh giá độc lập.

Sau khi đọc/chấm test, chạy `audit` tương tự để lấy grounded answer/citation/abstention. Bản hoàn tất và đường dẫn run cuối nằm ở `TONG_HOP_QUA_TRINH_VA_KET_QUA.md`; nhãn AI-assisted đã được học viên kiểm tra và xác nhận, không đổi nguồn gốc thành nhãn độc lập của bên thứ ba. Các run cũ lỗi và lần kiểm tra embedding API HTTP 429 được giữ để đối chiếu.

## 6. Giới hạn đã biết

- BM25 dùng Unicode word tokens, chưa tách từ tiếng Việt. Alice là corpus tiếng Anh.
- Qdrant local mở/đóng kết nối cho từng query để không giữ file lock trên Windows; benchmark gồm chi phí này.
- Context whole-chunk có thể bỏ evidence khi budget nhỏ; trace thể hiện chunk nào được gửi.
- Agent dùng tối đa số lượt search cấu hình; model trả nhiều tool call một lượt, JSON lỗi hoặc lỗi provider được ghi rõ thành `error`. Chưa có vòng sửa output model tự động.
- Giá dịch vụ retrieval là 0 USD vì chạy local; không quy đổi điện/phần cứng. Chi phí API agent để null cho đến khi có usage và bảng giá đã xác nhận.
- Không thực hiện bonus đa phương thức 100 trang; 69 trang logic Alice không đáp ứng yêu cầu tài liệu đa phương thức đó.
