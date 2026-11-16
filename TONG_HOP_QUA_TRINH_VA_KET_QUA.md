# Tổng hợp quá trình thực hiện và kết quả Day 7

**Học viên:** Hoàng Dương Anh Quân · **MSSV:** 2A202603735 · **Lớp:** L3B.

Bản tổng hợp được tạo từ kết quả chạy thật trong repository, gồm retrieval, agent Groq, trace, nhãn và audit. Nhãn ban đầu do Codex hỗ trợ chấm; học viên đã xác nhận kiểm tra lại toàn bộ trong hội thoại. Trạng thái hiện tại: **AI-assisted, human_verified=true**. Xác nhận được lưu tại `results/final-agent/human-verification.json`. Các run cũ được giữ lại, không thay lỗi bằng dữ liệu giả.

## 1. Mục tiêu và dữ liệu đầu vào

Xây Agentic RAG tiếp nối Day 6: tìm bằng chứng từ tài liệu, trả lời có nguồn, thử ít nhất ba phương pháp retrieval và so sánh trên dev trước khi đánh giá test.

Nguồn Day 6 do học viên cung cấp: [repository Data Ingestion Engineering](https://github.com/HoangQuan23112004/K5-L3B-Day06-HoangDuongAnhQuan-2A202603735-DataIngestionEngineering), commit `82080a89e87cf6eeab2c9709d8c50276ce8dd2c7`. Tác phẩm là *Alice’s Adventures in Wonderland*, Lewis Carroll, Project Gutenberg #11; bản raw giữ thông báo/giấy phép PG. Giữ nguyên **238 chunk cấu hình B** với ID, text, metadata, nguồn và **69 đơn vị nội dung logic**. Không gọi các đơn vị này là trang PDF.

Repo Day 6 không công bố snapshot Qdrant hoặc vectors. Dự án tái tạo Qdrant local `alice_B` bằng đúng **FastEmbed 0.7.4 / all-MiniLM-L6-v2 / 384 chiều**, document `.embed` và query `.query_embed`. Hash ONNX trùng với manifest Day 6: `bbd7b466f6d58e646fdc2bd5fd67b2f5e93c0b687011bd4548c420f7bd46f0c5`. Tái tạo mất khoảng 116.87 giây, gồm tải model, embedding và lưu store; không gọi API embedding trả phí.

Benchmark **24 câu**: 15 có đáp án + 2 thiếu evidence trên dev; 5 có đáp án + 2 thiếu evidence trên test. Tái dùng Q01–Q15 dev của Day 6; loại test cũ Q16–Q20 vì đã lộ. Tạo D7-T01–T05 trước khi chạy retrieval dev. Câu thiếu evidence hỏi serial number đồng hồ, sinh nhật người chị, tuổi Bill và địa chỉ nhà Alice; từng case có lý do kiểm tra trong corpus. Gold/expected answer chỉ dùng đánh giá, không truyền cho agent/retriever.

## 2. Các bước đã thực hiện

| Bước | Công việc | Kết quả / bằng chứng |
|---|---|---|
| 1 | Đọc đề, rubric, benchmark và starter | Xác định schema, yêu cầu ba phương pháp, dev/test và audit citation |
| 2 | Kết nối dữ liệu Day 6 | `vendor/day6/`, `data/alice/manifest.json`; giữ nguyên ID/text/metadata |
| 3 | Cài runtime và dependency | Python 3.12, FastEmbed/Qdrant trong `.venv`; `requirements-lock.txt` |
| 4 | Tạo vector store thật | Qdrant cosine 384 chiều; `results/index-manifest.json` |
| 5 | Viết retrieval và context packing | BM25, dense, hybrid RRF; dedup, whole-chunk budget, nguồn/trang |
| 6 | So sánh 6 cấu hình dev | `results/groq-retrieval/`; giữ cả cấu hình không cải thiện |
| 7 | Nối Groq | `openai/gpt-oss-20b` qua endpoint OpenAI-compatible; FastEmbed vẫn local |
| 8 | Sửa lỗi vận hành | `.env` tự nạp, User-Agent, lỗi mạng rõ nguyên nhân, pacing/retry/resume |
| 9 | Sửa giao thức tool | Gửi assistant tool call và tool result đúng cặp, context tích lũy có budget |
| 10 | Chạy lại hai agent trên dev | Cùng phiên bản code; đọc/chấm tất cả câu, không chọn lại câu sai |
| 11 | Chốt trước test | `results/final-agent/frozen-agent.json` và `docs/AGENT_PROTOCOL.md` |
| 12 | Chạy/chấm test, tổng hợp | Hai cấu hình × 7 câu; trace, reviews, audit và báo cáo này |

## 3. Thiết kế hệ thống

Luồng thực thi: **câu hỏi → Groq chọn tool search → retrieval local → context có nguồn → Groq finish/abstain → kiểm tra citation → câu trả lời và trace**.

BM25 dùng Unicode tokenization, k1=1.5, b=0.75. Dense dùng query embedding thật và Qdrant cosine. Hybrid hợp nhất hai bảng xếp hạng bằng **RRF k=60**, không cộng score khác thang. Mặc định hybrid lấy 12 candidate mỗi nhánh, wide lấy 24. Context loại trùng ID, giữ nguyên chunk và nguồn/trang, bỏ chunk không vừa budget. Budget tính ký tự evidence context; không bao gồm prompt, câu hỏi và schema tool.

Agent có ba tool `search`, `finish`, `abstain`. Baseline top-3/budget 6000/tối đa 2 search; wide top-6/budget 12000/tối đa 4 search. Kết quả search được trả qua message role `tool`, liên kết tool call trước đó; chỉ context tích lũy mới nhất gửi model để không nhân budget qua nhiều lượt. Tài liệu được coi là dữ liệu, không thực thi chỉ dẫn trong tài liệu. Citation chỉ được nhận nếu ID thuộc context; nếu model gửi ID riêng mà thiếu marker trong answer, ứng dụng render marker và ghi event `citation_formatting`. Kiểm tra cấu trúc này không chứng minh nguồn hỗ trợ nghĩa của câu trả lời; phần đó được audit riêng.

## 4. Kết quả retrieval trên dev

Mẫu số ranking/context gồm 15 câu có đáp án. Dù pipeline lấy top-6 để đóng context, ranking vẫn so ở top-1/top-3. Hai câu thiếu evidence không nằm trong mẫu số này.

| Cấu hình | Phương pháp | top-k | Budget ký tự | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Median ms |
|---|---|---|---|---|---|---|---|
| bm25 | bm25 | 3 | 6000 | 12/15 (80.0%) | 14/15 (93.3%) | 14/15 (93.3%) | 6.29 |
| dense | dense | 3 | 6000 | 8/15 (53.3%) | 12/15 (80.0%) | 12/15 (80.0%) | 64.64 |
| hybrid | hybrid | 3 | 6000 | 9/15 (60.0%) | 14/15 (93.3%) | 14/15 (93.3%) | 64.14 |
| hybrid-wide | hybrid | 6 | 12000 | 9/15 (60.0%) | 14/15 (93.3%) | 15/15 (100.0%) | 59.28 |
| bm25-wide | bm25 | 6 | 12000 | 12/15 (80.0%) | 14/15 (93.3%) | 15/15 (100.0%) | 5.82 |
| bm25-small | bm25 | 3 | 1800 | 12/15 (80.0%) | 14/15 (93.3%) | 12/15 (80.0%) | 6.35 |

BM25-wide được chọn từ retrieval dev theo giao thức đã công bố: ưu tiên Context Evidence Rate, rồi Hit@3, Hit@1, hòa ưu tiên budget/top-k nhỏ hơn. Baseline BM25 top-3 vẫn được đánh giá cùng test để thấy đánh đổi. Không coi thay top-k là phương pháp retrieval mới.

Hai lỗi retrieval dev đã đối chiếu: **Q04** có evidence ở hạng 4, nên top-3 thiếu nhưng top-6 giữ được; **Q11** ở cấu hình budget 1800, evidence hạng 3 bị bỏ do không vừa budget, còn budget 6000 giữ được. Hybrid-wide cũng đưa evidence Q09 hạng 4 vào context. Tăng context có thể cải thiện khả năng giữ evidence nhưng tăng đầu vào model; không bảo đảm câu trả lời tốt hơn.

## 5. Kết quả agent thật và audit

Tất cả bảng dưới đây lấy từ `summary.json` và `audit.json` của từng run. Grounded 0/1/2 là số câu có đáp án ở mỗi mức; citation validity được đọc đối chiếu nội dung nguồn. Phần chấm có nguồn gốc AI-assisted và đã được học viên kiểm tra, xác nhận; không đổi điểm sau xác nhận.

| Cấu hình | Split | Chạy thành công | Grounded 0/1/2 | Điểm TB | Citation hợp lệ | Từ chối đúng | Từ chối nhầm | Median giây/câu |
|---|---|---|---|---|---|---|---|---|
| BM25 baseline | dev | 17/17 | 2/2/11 | 1.600/2 | 12/13 (92.3%) | 2/2 (100.0%) | 2/15 (13.3%) | 16.59 |
| BM25-wide | dev | 17/17 | 2/1/12 | 1.667/2 | 12/14 (85.7%) | 2/2 (100.0%) | 2/15 (13.3%) | 16.29 |
| BM25 baseline | test | 7/7 | 0/0/5 | 2.000/2 | 5/5 (100.0%) | 2/2 (100.0%) | 0/5 (0.0%) | 14.86 |
| BM25-wide | test | 7/7 | 0/1/4 | 1.800/2 | 4/5 (80.0%) | 2/2 (100.0%) | 0/5 (0.0%) | 56.31 |

Trên dev, điểm trung bình wide thay đổi **+0.067/2** so với baseline. Trên test, wide **thấp hơn baseline**, chênh lệch **-0.200/2**. Không chọn lại cấu hình hoặc sửa prompt theo kết quả test. Bộ test chỉ có 5 câu có đáp án nên kết quả này chưa chứng minh ưu thế tổng quát. Context trung bình test: baseline **2186 ký tự**, wide **5098 ký tự**; context lớn hơn không tự bảo đảm chất lượng câu trả lời/citation cao hơn.


Chi tiết lượt tìm, usage và các phản hồi 429 trong bốn run cuối:

| Cấu hình/split | Tổng lượt search | Search/câu min–max | Prompt tokens | Completion tokens | Phản hồi 429 đã ghi | Lỗi mạng đã ghi |
|---|---|---|---|---|---|---|
| BM25 baseline/dev | 22 | 1–2 | 34,806 | 5,589 | 0 | 0 |
| BM25-wide/dev | 31 | 1–4 | 72,392 | 6,155 | 21 | 3 |
| BM25 baseline/test | 9 | 1–2 | 13,840 | 2,708 | 0 | 0 |
| BM25-wide/test | 13 | 1–4 | 32,948 | 3,295 | 2 | 3 |

### Ví dụ đã đối chiếu trace

- **Câu trả lời có nguồn — Q01:** `The jar was empty, and Alice avoided dropping it because she feared it might kill someone below the well. [7955ad96fba62da3f769c8322d9ff57c06fd1e8f1738155d433cec84fc92c6b6]`. Đoạn trang logic 1 xác nhận lọ rỗng và Alice sợ làm chết người bên dưới; nhãn answer=2, context=2 và citation_support=true.
- **Thiếu bằng chứng — D7-D-N1:** hỏi serial number của đồng hồ White Rabbit. Output: `Không đủ bằng chứng để trả lời.`. Đây là thông tin không có trong corpus; cuối trace là `search_limit`, nên ghi rõ từ chối do giới hạn tìm, không tuyên bố model chủ động nhận biết thiếu thông tin.
- **Lỗi chất lượng — Q07:** hỏi vì sao các con vật không thích nghe về Dinah. Output: `Không đủ bằng chứng để trả lời.` dù context có Dinah là mèo bắt chuột/ăn chim. Nhãn answer=0, context=2; đây là false abstention, không được loại khỏi điểm chất lượng.


`cost_usd` giữ null vì chưa đối chiếu hóa đơn/bảng giá áp dụng cho tài khoản. Tokens ở trên là usage API thực tế ghi được, không tự gán API miễn phí thành 0 USD. Elapsed time gồm chờ pacing, backoff, DNS và timeout. Vì kết nối có nhiều gián đoạn, median này không phải tốc độ thuần của retrieval/model và không đủ để khẳng định cấu hình nào nhanh hơn vài giây; context/tokens và số lượt tìm phản ánh rõ đánh đổi hơn. Những request bị provider từ chối trước khi có usage không có token count xác nhận; run lịch sử và trace lỗi được giữ riêng.

## 6. Những lỗi đã gặp và cách xử lý

| Hiện tượng | Nguyên nhân quan sát được | Thay đổi / kết quả |
|---|---|---|
| Không thấy `.env` | Ban đầu chỉ có file mẫu, code chưa nạp file | Tạo `.env`, thêm bộ nạp literal; ưu tiên CLI > terminal > file; key không vào Git |
| HTTP 403 | Cloudflare trả mã 1010 với User-Agent mặc định Python | Thêm `Day7-AgenticRAG/1.0`; kiểm tra cùng endpoint/key trả HTTP 200 |
| HTTP 401 invalid_api_key | Key được gửi không được chấp nhận; kiểm tra file cho HTTP 200 | Hướng dẫn xóa biến key cũ trong terminal để dùng key `.env`; không kết luận file key hỏng |
| URLError | Có lần DNS lookup thất bại; thông báo cũ che nguyên nhân | Phân loại DNS/TLS/timeout/reset/proxy; kiểm tra lại kết nối, giữ nguyên key |
| Câu demo bị từ chối dù đáp án đúng | Model gửi answer và citation ID riêng, thiếu marker trong văn bản | Render marker từ ID đã xác thực; không nới việc kiểm tra ID hoặc tự bịa nguồn |
| 12/17 câu lỗi lần đầu | HTTP 429 rate_limit_exceeded sau 5 câu đầu | Pacing 3 giây, chờ Retry-After, bounded backoff và resume vào output mới |
| Q09 còn tool_use_failed | Lỗi sau bước search trong giao thức cũ | Trả tool result theo cặp assistant/tool; Q09 sau sửa trả lời có nguồn đúng |
| Answered nhưng sai hoặc thiếu căn cứ | Retrieval có evidence không đảm bảo model dùng đúng | Chấm từng câu và từng citation; giữ các lỗi trong audit, không suy điểm từ status |

Run lịch sử `artifacts/agent-bm25-dev` có 5 thành công/12 lỗi; run resumed có 16 thành công/1 lỗi Q09. Một lần thử bổ sung tại `results/final-agent/bm25-dev` vẫn còn lỗi Q09. Sau khi sửa giao thức, chạy **mới toàn bộ baseline và wide**; không trộn kết quả khác phiên bản code để so sánh cuối. Các status `abstain` do `search_limit` được phân biệt trong trace/reason với model chủ động nhận biết thiếu evidence.

## 7. Đường dẫn bằng chứng và tái lập

- Dữ liệu/cases: `data/alice/chunks.json`, `data/alice/cases.json`, `data/alice/manifest.json`.
- Retrieval dev 6 cấu hình: `results/groq-retrieval/`.
- Agent baseline dev cuối: `results/final-agent/bm25-dev-v3/` (v2 có 5 lỗi mạng; v3 giữ thành công và chỉ retry lỗi).
- Agent wide dev: `results/final-agent/bm25-wide-dev/`.
- Lock trước test: `results/final-agent/frozen-agent.json`.
- Agent test: `results/final-agent/bm25-test/`, `results/final-agent/bm25-wide-test-v2/`; run wide ban đầu `bm25-wide-test/` giữ lỗi provider của D7-T04. V2 chỉ retry câu error, không thay sáu kết quả đã có.
- Mỗi run: manifest, traces JSON/JSONL, summary, reviews có reason/citation_reasons và audit tổng hợp.
- Tổng hợp máy đọc: `results/final-agent/final-summary.json`; nhãn từng câu: `results/final-agent/REVIEW_DETAILS.md`.
- Môi trường/model hash: `results/environment.json`, `results/index-manifest.json`, `requirements-lock.txt`; code hash cuối có trong final-summary.

Bộ kiểm thử code đã chạy **47 test thành công**, gồm kiểm tra SQLite/Qdrant với vector fixture, nạp cấu hình, lỗi mạng, retry/rate-limit, resume, giao thức tool và citation guards. Các mock/fixture chỉ chứng minh hành vi code, không được dùng để chấm chất lượng agent thật. Kết quả kiểm tra ở `results/validation.json`.

Lệnh tái lập nằm trong `docs/RUNBOOK.md`. Dùng thư mục output mới và cùng dữ liệu/index/model/config; `freeze` kiểm tra identity và hash của audit. Retry/resume chỉ chạy lại câu `error`, không thay thế câu trả lời sai bằng lần trả lời tốt hơn. `.env`, vector store và cache model bị Git bỏ qua; source/dataset/manifests cho phép tái tạo.

## 8. Giới hạn và xác nhận của học viên

- Học viên đã xác nhận kiểm tra lại toàn bộ nhãn, answer/context/citation: **human_verified=true**. Đây là xác nhận của học viên, không phải đánh giá độc lập của bên thứ ba. Xác nhận diễn ra sau các lần chạy, không thay cấu hình hoặc kết quả benchmark.
- Corpus và câu hỏi đều thuộc một tác phẩm; test chỉ có 5 câu có đáp án + 2 thiếu evidence. Không khái quát tỷ lệ trên tập nhỏ thành độ chính xác chung của hệ thống.
- Test retrieval đã được xem trước khi hoàn tất agent; các sửa lỗi agent dựa trên dev/Q09/demo, không dùng test agent để tuning. Không gọi đây là benchmark mù hoàn toàn.
- Exact-quote retrieval metric có thể bỏ sót đoạn diễn đạt tương đương; audit semantic vẫn cần thiết.
- Không làm bonus tài liệu đa phương thức 100 trang; 69 đơn vị logic Alice không thay thế điều kiện này.
- Không đưa ra điểm chấm cuối theo rubric thay giảng viên; báo cáo cung cấp bằng chứng và kết quả đo được.
