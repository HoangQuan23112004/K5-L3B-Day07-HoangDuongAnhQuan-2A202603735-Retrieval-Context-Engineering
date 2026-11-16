# Báo cáo Day 7

**Họ và tên:** Hoàng Dương Anh Quân · **MSSV:** 2A202603735 · **Lớp:** L3B.

## Dữ liệu và benchmark

- Nguồn, quyền sử dụng, số trang và số chunk: *Alice's Adventures in Wonderland*, Lewis Carroll, [Project Gutenberg #11](https://www.gutenberg.org/ebooks/11), tác phẩm nguyên gốc public domain tại Hoa Kỳ; giữ thông báo và giấy phép PG trong bản raw. Tái dùng **238 chunk cấu hình B, 69 đơn vị nội dung logic** từ [repo Day 6 của học viên](https://github.com/HoangQuan23112004/K5-L3B-Day06-HoangDuongAnhQuan-2A202603735-DataIngestionEngineering), commit `82080a89e87cf6eeab2c9709d8c50276ce8dd2c7`. Đây là đơn vị văn bản do pipeline chia, không phải trang PDF. Giữ nguyên chunk ID, text, source, page và metadata; provenance tại `data/alice/manifest.json`, nguồn/giấy phép tại `vendor/day6/data/`.
- Vector store, embedding model, phiên bản và số chiều: **Qdrant local cosine**, collection `alice_B`, qdrant-client 1.20.0; **FastEmbed 0.7.4**, model `sentence-transformers/all-MiniLM-L6-v2`, **384 chiều**, ONNX Runtime 1.32.0. Dùng document `.embed` và query `.query_embed` như Day 6. Vì repo Day 6 không công bố snapshot/vectors, tái tạo store từ chunk gốc; mất khoảng **116,87 giây**, gồm tải model/embedding/lưu store. Hash ONNX khớp Day 6; chi tiết tại `results/index-manifest.json` và `results/environment.json`.
- Agent model, cách chạy và phân chia dev/test: **Groq `openai/gpt-oss-20b`**, endpoint OpenAI-compatible, Python 3.12.10; key nạp từ `.env`, embedding vẫn chạy local. Benchmark **24 câu**: dev **15 có đáp án + 2 thiếu evidence**, test **5 có đáp án + 2 thiếu evidence**. Giữ Q01–Q15 dev của Day 6; loại Q16–Q20 test cũ đã lộ, soạn D7-T01–T05 trước thí nghiệm Day 7. Lệnh chạy và cấu hình tại `docs/RUNBOOK.md`, `docs/PROTOCOL.md`, `docs/AGENT_PROTOCOL.md`.
- Cách xác định câu có/thiếu evidence và tiêu chí chấm: câu có đáp án có `expected_answer` và evidence đúng nguồn/trang trong `data/alice/cases.json`; các mục `gold` là bằng chứng thay thế, hỗ trợ thêm `evidence_groups` cho nhiều nhóm bắt buộc. Câu thiếu evidence hỏi serial number đồng hồ, sinh nhật người chị, tuổi Bill hoặc địa chỉ Alice; kiểm tra toàn văn và ghi `absence_reason`, không kết luận chỉ từ top-k. Không truyền gold/đáp án chuẩn vào agent/retriever. Chấm answer **0/1/2**, context **0/1/2**, từng citation **true/false**, abstention theo output thực tế. Nhãn ban đầu **AI-assisted**; Học viên đã kiểm tra lại toàn bộ, `human_verified=true`. Xác nhận lưu riêng tại `results/final-agent/human-verification.json`, không thay điểm hoặc khóa cấu hình trước test.

## Retrieval và thử nghiệm

| Cấu hình | Phương pháp, top-k, filter, rerank, context budget | Giả thuyết / thay đổi | Split | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Thời gian / chi phí |
|---|---|---|---|---|---|---|---|
| Baseline (bm25) | BM25 k1=1.5, b=0.75; k=3; budget 6000 ký tự; không rerank; filter chapter theo câu hỏi khi có | Đối sánh chính xác tên nhân vật và thuật ngữ trong Alice. | dev | 12/15 (80.0%) | 14/15 (93.3%) | 14/15 (93.3%) | Median 6.29 ms/câu; API retrieval 0 USD |
| Phương pháp 2 (dense) | Dense cosine qua FastEmbed + Qdrant; k=3; budget 6000 ký tự; không rerank; filter chapter theo câu hỏi khi có | Embedding khôi phục câu hỏi diễn đạt khác từ khóa. | dev | 8/15 (53.3%) | 12/15 (80.0%) | 12/15 (80.0%) | Median 64.64 ms/câu; API retrieval 0 USD |
| Phương pháp 3 (hybrid) | Hybrid RRF k=60; 12 candidate/nhánh; top-3; budget 6000 ký tự; không rerank; filter chapter theo câu hỏi khi có | Kết hợp ngữ nghĩa và từ khóa bằng rank fusion. | dev | 9/15 (60.0%) | 14/15 (93.3%) | 14/15 (93.3%) | Median 64.14 ms/câu; API retrieval 0 USD |
| Cải thiện 1 (hybrid-wide) | Hybrid RRF; 24 candidate/nhánh; top-6; budget 12000 ký tự; không rerank; filter chapter theo câu hỏi khi có | Mở candidate/context để giữ evidence ngoài top-3. | dev | 9/15 (60.0%) | 14/15 (93.3%) | 15/15 (100.0%) | Median 59.28 ms/câu; API retrieval 0 USD |
| Cải thiện 2 (bm25-wide) | BM25; top-6; budget 12000 ký tự; không rerank; filter chapter theo câu hỏi khi có | Giữ thêm điều kiện, đổi lại context lớn hơn; cấu hình chọn. | dev | 12/15 (80.0%) | 14/15 (93.3%) | 15/15 (100.0%) | Median 5.82 ms/câu; API retrieval 0 USD |
| Thử nghiệm bổ sung (bm25-small) | BM25; top-3; budget 1800 ký tự; không rerank; filter chapter theo câu hỏi khi có | Thử giảm context; đo ảnh hưởng mất evidence do không vừa budget. | dev | 12/15 (80.0%) | 14/15 (93.3%) | 12/15 (80.0%) | Median 6.35 ms/câu; API retrieval 0 USD |
| Cấu hình đã chọn (bm25-wide) | BM25; top-6; budget 12000 ký tự; không rerank; filter chapter theo câu hỏi khi có | Đánh giá sau khi đã chốt trên dev. | test | 5/5 (100.0%) | 5/5 (100.0%) | 5/5 (100.0%) | Median 6.78 ms/câu; API retrieval 0 USD |
| Baseline (bm25) | BM25; top-3; budget 6000 ký tự; không rerank; filter chapter theo câu hỏi khi có | Đối chứng trên cùng bộ test. | test | 5/5 (100.0%) | 5/5 (100.0%) | 5/5 (100.0%) | Median 8.74 ms/câu; API retrieval 0 USD |

Ba phương pháp khác nhau là **BM25, dense và hybrid RRF**; thay top-k riêng không được tính là phương pháp mới. Hybrid vừa là phương pháp mới vừa là một thử nghiệm cải thiện. Bảng dùng cùng corpus, query gốc và nhãn; luôn chấm ranking ở cutoff 1/3 kể cả context top-6. Mẫu số là 15 câu dev/5 câu test có đáp án; câu thiếu evidence không nằm trong mẫu số retrieval. Giữ nguyên chunk kèm nguồn/trang, dedup ID, bỏ chunk không vừa budget; budget tính ký tự evidence context, không gồm prompt/schema tool. Filter chapter của Q04/Q07/Q13 dev và các filter đã cung cấp được lấy từ câu hỏi, không suy từ gold; không dùng reranker.

Nguồn số liệu retrieval: `results/groq-retrieval/*-dev/` và `results/alice/bm25-test/`, `results/alice/bm25-wide-test/` của đợt retrieval đã khóa; không dùng latency agent thay cho latency retrieval. Retrieval local không có phí API; chưa quy đổi điện/phần cứng.

Hai lỗi dev, thay đổi và kết quả trước/sau:

1. **Q04 — evidence ở hạng 4:** BM25 top-3 tìm các đoạn gần chủ đề nhưng bỏ đoạn kiểm tra nhãn poison. Mở top-6 đưa evidence `ea2ed1225b...`, trang logic 4, vào context. Context Evidence Rate tăng **14/15 → 15/15**, Hit@3 vẫn **14/15**. Đây là cải thiện context, không thay đổi định nghĩa Hit@3.
2. **Q11 — budget nhỏ bỏ evidence:** budget 1800 chỉ giữ hai đoạn đầu và bỏ evidence hạng 3 `77f4248a0e...`. Budget 6000 giữ được evidence; context rate **12/15 → 14/15**. Cấu hình giảm budget không cải thiện chất lượng, nên không chọn.
3. **Q09 — hybrid cần evidence ngoài top-3:** hybrid-wide đưa evidence hạng 4 `b198754550...` vào context; context rate **14/15 → 15/15**, nhưng tăng độ dài context và chi phí query embedding.

Chọn **BM25-wide** theo tiêu chí đã công bố trước test: ưu tiên Context Evidence Rate, rồi Hit@3, Hit@1, hòa chọn budget/top-k nhỏ hơn. So với hybrid-wide, BM25-wide có context rate bằng 15/15 nhưng Hit@1 tốt hơn (12/15 so với 9/15). Audit agent dev cho điểm trung bình **1,667/2** so với baseline **1,600/2**, đồng thời citation precision giảm **12/14** so với **12/13**; giữ và báo rõ đánh đổi. Khóa tại `results/final-agent/frozen-agent.json` trước khi chạy test agent; không chọn lại theo kết quả test. Test retrieval đạt context **5/5** ở cả baseline và selected; không suy từ đó rằng câu trả lời agent chắc chắn đúng.

## Agent và đánh giá

- Tool, số lượt gọi, điều kiện dừng, cách chọn context và xử lý lỗi: model gọi **search**, **finish**, **abstain**. Baseline tối đa **2 search**, wide tối đa **4 search**, mỗi lượt model trả một tool call. Gửi kết quả theo cặp assistant tool call/tool result, chỉ giữ context tích lũy cuối trong budget; ưu tiên chunk của query mới. Dừng khi finish hợp lệ, model abstain hoặc hết lượt tìm; ghi rõ `search_limit` nếu từ chối do giới hạn. Citation ID phải thuộc context; nếu model gửi ID riêng, ứng dụng render marker và log `citation_formatting`. Audit ngữ nghĩa riêng, không coi ID hợp lệ là nguồn hỗ trợ. Nội dung tài liệu là dữ liệu, không phải chỉ dẫn. Có User-Agent ứng dụng, pacing Groq 3 giây, bounded retry theo Retry-After/backoff cho 429 và retry lỗi DNS/timeout tạm thời. Resume chỉ câu `error`, giữ nguyên câu đã answered/abstain và lịch sử lần thử.

| Cấu hình / split | Tool use | Số lượt gọi | Grounded answer 0/1/2 và trung bình | Citation hợp lệ | Câu có citation | Abstention đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|
| BM25 baseline / dev | 17/17 (100.0%) | 22 search; 1–2/câu | 0/1/2: 2/2/11; TB 1.600/2 | 12/13 (92.3%) | 13/13 (100.0%) | 2/2 (100.0%) | 2/15 (13.3%) |
| BM25-wide / dev | 17/17 (100.0%) | 31 search; 1–4/câu | 0/1/2: 2/1/12; TB 1.667/2 | 12/14 (85.7%) | 13/13 (100.0%) | 2/2 (100.0%) | 2/15 (13.3%) |
| BM25 baseline / test | 7/7 (100.0%) | 9 search; 1–2/câu | 0/1/2: 0/0/5; TB 2.000/2 | 5/5 (100.0%) | 5/5 (100.0%) | 2/2 (100.0%) | 0/5 (0.0%) |
| BM25-wide / test | 7/7 (100.0%) | 13 search; 1–4/câu | 0/1/2: 0/1/4; TB 1.800/2 | 4/5 (80.0%) | 5/5 (100.0%) | 2/2 (100.0%) | 0/5 (0.0%) |

Bốn run cuối có **17/17, 17/17, 7/7, 7/7 câu chạy thành công; lỗi thực thi cuối = 0**. Trên test, baseline có 5 câu answer=2; wide có 4 câu answer=2 và 1 câu answer=1. Cả hai từ chối đúng 2/2 câu thiếu evidence, không từ chối nhầm câu có đáp án. Với câu có đáp án, từ chối chấm 0; câu lỗi provider được báo riêng và chỉ retry lỗi, không chọn lại các answer sai.

| Query ID | Loại câu | Tool call và kết quả | Câu trả lời và citation | Nhãn, lý do |
|---|---|---|---|---|
| Q01 (BM25 baseline/dev) | Có đáp án | 1 search; answered; cuối=answer | The jar was empty, and Alice avoided dropping it because she feared it might kill someone below the well. [7955ad96fba62da3f769c8322d9ff57c06fd1e8f1738155d433cec84fc92c6b6] | answer=2; context=2; citation=1/1. Đủ hai ý: lọ rỗng và sợ làm chết người bên dưới. Context/citation có cả hai điều kiện. |
| Q07 (BM25 baseline/dev) | Có đáp án | 2 search; abstain; cuối=search_limit | Không đủ bằng chứng để trả lời. | answer=0; context=2; citation=0/0. Từ chối nhầm do search_limit dù context trang 14 có Dinah là mèo bắt chuột, ăn chim. Không coi context tốt là câu trả lời đúng. |
| Q11 (BM25 baseline/dev) | Có đáp án | 1 search; answered; cuối=answer | Alice admitted that she had tasted eggs, though she didn’t like them raw. [77f4248a0eb7d5df0225c736fb137d5633fb93374ae17e60a63fcba331c237e4] | answer=1; context=2; citation=0/1. Đúng việc Alice đã nếm trứng nhưng thiếu ý trẻ con ăn nhiều như rắn và thêm không thích trứng sống. Nguồn được cite không hỗ trợ toàn bộ câu trả lời. |
| Q14 (BM25 baseline/dev) | Có đáp án | 1 search; answered; cuối=answer | The Dormouse said the three sisters lived at the bottom of a well. [2e1176084b8d4ab010d2ea5ccd6462f269250970ffcbd166cd184252bfebf9c8] | answer=1; context=1; citation=1/1. Chỉ nói ở đáy một cái giếng, thiếu loại treacle-well. Context có sống bằng treacle và vẽ treacle nhưng chưa có đoạn xác định rõ loại giếng. |
| Q01 (BM25-wide/dev) | Có đáp án | 1 search; answered; cuối=answer | The jar was empty, and Alice avoided dropping it because she feared it might kill someone underneath. [7955ad96fba62da3f769c8322d9ff57c06fd1e8f1738155d433cec84fc92c6b6] | answer=2; context=2; citation=1/1. Đủ hai ý: lọ rỗng và sợ làm chết người bên dưới. Context/citation có cả hai điều kiện. |
| Q07 (BM25-wide/dev) | Có đáp án | 4 search; abstain; cuối=search_limit | Không đủ bằng chứng để trả lời. | answer=0; context=2; citation=0/0. Từ chối nhầm do search_limit dù context trang 14 có Dinah là mèo bắt chuột, ăn chim. Không coi context tốt là câu trả lời đúng. |
| Q11 (BM25-wide/dev) | Có đáp án | 2 search; answered; cuối=answer | Alice admitted that she had tasted eggs. [77f4248a0eb7d5df0225c736fb137d5633fb93374ae17e60a63fcba331c237e4] | answer=1; context=2; citation=1/1. Đúng việc Alice đã nếm trứng nhưng thiếu ý trẻ con ăn trứng nhiều như rắn. Không còn chi tiết trứng sống không có căn cứ như baseline. |
| Q14 (BM25-wide/dev) | Có đáp án | 1 search; answered; cuối=answer | The Dormouse said the three sisters lived in a treacle‑well. [2e1176084b8d4ab010d2ea5ccd6462f269250970ffcbd166cd184252bfebf9c8] [05f3b7d909a1003e908bec49f9ccb267b0cac7e5422849a9e6c343bdf47d0fe1] | answer=2; context=2; citation=0/2. Đáp án treacle-well đúng và đoạn 905ef... trang 38 có trong context xác nhận đầy đủ, nhưng model cite hai đoạn khác không đủ hỗ trợ. Chấm answer/context riêng với citation. |
| D7-T01 (BM25 baseline/test) | Có đáp án | 1 search; answered; cuối=answer | The Mock Turtle lists the four branches of Arithmetic as Ambition, Distraction, Uglification, and Derision. [c778e44b8969b05255e0dae39e7b080a6857bf7e25971d89a6ba4ad94676102f] | answer=2; context=2; citation=1/1. Đủ bốn nhánh Arithmetic đúng thứ tự tên trong nguồn, không nhầm Reeling/Writhing là nhánh Arithmetic. |
| D7-T02 (BM25 baseline/test) | Có đáp án | 1 search; answered; cuối=answer | The jurors write their own names on the slates because they fear they might forget them before the trial ends. [52df49b8955d3fee54598b9d546f629346011429ccf1a67fce71c96e8ca49de0] | answer=2; context=2; citation=1/1. Đúng nguyên nhân jurors sợ quên tên trước khi phiên tòa kết thúc; không thêm nguyên nhân khác. |
| D7-T03 (BM25 baseline/test) | Có đáp án | 1 search; answered; cuối=answer | They added the three dates together and then reduced the sum to shillings and pence. [4e3a4a7ea769c0be16e552a13122c253ceeb839d7bd9d3579cbe40b2d6da1b79] | answer=2; context=2; citation=1/1. Đúng cả hai thao tác cộng ba ngày và đổi kết quả sang shillings/pence, không tự bịa kết quả số. |
| D7-T04 (BM25 baseline/test) | Có đáp án | 1 search; answered; cuối=answer | Alice had put the Lizard in the jury‑box upside‑down, with its head downwards, which made it unable to move. She quickly removed it and turned it right‑side‑up again, fixing the mistake. [5ae97a93b30de4296cebf117501894116b17502433c59c2809b258c9cdca0391] | answer=2; context=2; citation=1/1. Đủ lỗi đặt Lizard đầu chúc xuống và cách lấy ra, đặt lại đúng chiều; chi tiết không cử động được có trong nguồn. |
| D7-T05 (BM25 baseline/test) | Có đáp án | 1 search; answered; cuối=answer | Bill resumed writing on his slate by using the ink that was trickling down his face, hastily beginning again as long as it lasted. [4dc73d58a323236207af1a75aea539a79e6809f8b985de91578b3dab16397d9e] | answer=2; context=2; citation=1/1. Đúng Bill dùng mực chảy trên mặt để viết tiếp; điều kiện còn mực cũng được nguồn hỗ trợ. |
| D7-T-N1 (BM25 baseline/test) | Thiếu evidence | 2 search; abstain; cuối=abstain | Không đủ bằng chứng để trả lời. | abstention_correct=True; context=0. Toàn văn không nêu tuổi chính xác Bill. Model chủ động gọi abstain với lý do thiếu bằng chứng tuổi, output không bịa số. |
| D7-T-N2 (BM25 baseline/test) | Thiếu evidence | 2 search; abstain; cuối=abstain | Không đủ bằng chứng để trả lời. | abstention_correct=True; context=0. Không có số nhà/địa chỉ bưu điện Alice trong corpus. Model chủ động gọi abstain, không lấy địa chỉ nhà Rabbit làm địa chỉ Alice. |
| D7-T01 (BM25-wide/test) | Có đáp án | 1 search; answered; cuối=answer | The Mock Turtle lists the four branches of Arithmetic as Ambition, Distraction, Uglification, and Derision. [c778e44b8969b05255e0dae39e7b080a6857bf7e25971d89a6ba4ad94676102f] | answer=2; context=2; citation=1/1. Đủ bốn nhánh Arithmetic đúng thứ tự tên trong nguồn, không nhầm Reeling/Writhing là nhánh Arithmetic. |
| D7-T02 (BM25-wide/test) | Có đáp án | 1 search; answered; cuối=answer | They write their names so they won’t forget them before the trial ends – the jurors fear that they might lose track of who they are and jot them down as a precaution. [52df49b8955d3fee54598b9d546f629346011429ccf1a67fce71c96e8ca49de0] | answer=2; context=2; citation=1/1. Đúng nguyên nhân jurors sợ quên tên trước khi phiên tòa kết thúc; không thêm nguyên nhân khác. |
| D7-T03 (BM25-wide/test) | Có đáp án | 1 search; answered; cuối=answer | They added the three dates together and then reduced the sum to shillings and pence. [4e3a4a7ea769c0be16e552a13122c253ceeb839d7bd9d3579cbe40b2d6da1b79] | answer=2; context=2; citation=1/1. Đúng cả hai thao tác cộng ba ngày và đổi kết quả sang shillings/pence, không tự bịa kết quả số. |
| D7-T04 (BM25-wide/test) | Có đáp án | 1 search; answered; cuối=answer | Alice had put the Lizard head‑down in the jury‑box. She noticed this, removed it, and set it back upright so it could move properly. [5ae97a93b30de4296cebf117501894116b17502433c59c2809b258c9cdca0391] | answer=2; context=2; citation=1/1. Đúng lỗi đặt đầu chúc xuống và lấy ra đặt lại thẳng. Lần thử đầu bị tool_use_failed trước khi có answer; resume chỉ câu error và giữ lịch sử. |
| D7-T05 (BM25-wide/test) | Có đáp án | 1 search; answered; cuối=answer | After the Queen hurled an inkstand at him, Bill stopped writing with a single finger and then quickly resumed writing on his slate by using the ink that was trickling down his face, writing as long as the ink would last. [4dc73d58a323236207af1a75aea539a79e6809f8b985de91578b3dab16397d9e] | answer=1; context=2; citation=0/1. Đúng cách dùng mực trên mặt để viết, nhưng thêm trình tự sau khi Queen ném mực Bill mới ngừng viết bằng ngón tay. Nguồn dùng had left off: đã ngừng trước đó. Chấm 1 vì ý chính đúng nhưng chi tiết thời gian không được hỗ trợ. |
| D7-T-N1 (BM25-wide/test) | Thiếu evidence | 4 search; abstain; cuối=search_limit | Không đủ bằng chứng để trả lời. | abstention_correct=True; context=0. Corpus không nêu tuổi Bill; output từ chối và không bịa số. Trace kết thúc search_limit, không phải model chủ động abstain. |
| D7-T-N2 (BM25-wide/test) | Thiếu evidence | 4 search; abstain; cuối=search_limit | Không đủ bằng chứng để trả lời. | abstention_correct=True; context=0. Corpus không có số nhà/địa chỉ Alice; output từ chối và không gán địa chỉ Rabbit cho Alice. Trace kết thúc search_limit. |

- Đường dẫn trace, nhãn, lệnh chạy, thời gian và chi phí: bốn thư mục run cuối là `results/final-agent/bm25-dev-v3/`, `bm25-wide-dev/`, `bm25-test/`, `bm25-wide-test-v2/`. Mỗi thư mục có `manifest.json`, `traces.json`, `traces.jsonl`, `summary.json`, `reviews.json`, `audit.json`; nhãn từng câu còn được tổng hợp tại `results/final-agent/REVIEW_DETAILS.md`. `human-verification.json` ghi xác nhận của học viên cho **48 nhãn agent**, không sửa trace, điểm hay khóa. Các run lỗi cũ vẫn được giữ: lần đầu 5 thành công/12 lỗi 429; resumed 16 thành công/1 lỗi Q09; baseline v2 có 5 lỗi mạng; wide test ban đầu có lỗi tool-use D7-T04, v2 chỉ retry câu đó.

```powershell
# Chạy một câu và lưu trace:
./.venv/Scripts/python.exe -X utf8 -m src.rag ask "What was in the ORANGE MARMALADE jar?" --config configs/bm25-wide.json
# Tái lập dùng thư mục output MỚI; trước test phải có audit dev và freeze phù hợp:
./.venv/Scripts/python.exe -X utf8 -m src.rag benchmark --config configs/bm25.json --split dev --mode agent --output artifacts/reproduction-baseline-dev
./.venv/Scripts/python.exe -X utf8 -m src.rag benchmark --config configs/bm25-wide.json --split dev --mode agent --output artifacts/reproduction-wide-dev
# Tổng hợp/kiểm chứng bộ kết quả đã lưu, không gọi API:
./.venv/Scripts/python.exe scripts/build_final_report.py
./.venv/Scripts/python.exe scripts/validate_final_results.py
```

Chi tiết lệnh audit/freeze/test và bộ tái lập tại `docs/RUNBOOK.md`; giao thức chốt tại `docs/AGENT_PROTOCOL.md`. Thời gian và usage của từng run:

- **BM25 baseline/dev:** median 16.59 giây/câu; context trung bình 2305 ký tự; prompt/completion tokens **34,806/5,589**.
- **BM25-wide/dev:** median 16.29 giây/câu; context trung bình 4689 ký tự; prompt/completion tokens **72,392/6,155**.
- **BM25 baseline/test:** median 14.86 giây/câu; context trung bình 2186 ký tự; prompt/completion tokens **13,840/2,708**.
- **BM25-wide/test:** median 56.31 giây/câu; context trung bình 5098 ký tự; prompt/completion tokens **32,948/3,295**.

Phí API agent `cost_usd=null` vì chưa đối chiếu hóa đơn/giá áp dụng của tài khoản; không giả định 0 USD. Elapsed time gồm pacing/backoff/DNS/timeout, không phải tốc độ thuần của model; các request không có usage xác nhận được giữ trong trace lỗi. Môi trường và model hash tại `results/environment.json`, `results/index-manifest.json`, `requirements-lock.txt`. Đã chạy **47 test code thành công**; mock/fixture chỉ kiểm chứng code, không dùng để báo chất lượng agent thật.

- Kết quả trước/sau, ví dụ lỗi, đánh đổi và giới hạn: baseline dev **1,600/2 → wide 1,667/2**, context **14/15 → 15/15**, nhưng citation **92,3% → 85,7%**. Test baseline **2,000/2**, wide **1,800/2**; giữ nguyên lựa chọn trước test, không sửa prompt/cấu hình để nâng điểm test. Wide D7-T05 nêu đúng cách dùng mực nhưng thêm trình tự thời gian không khớp nguồn; chấm answer=1, citation=false. Q07/Q13 dev có đủ context nhưng hết lượt tìm nên từ chối nhầm; Q14 wide trả lời đúng nhưng cite các đoạn không đủ hỗ trợ. Những ví dụ này cho thấy retrieval/context tốt chưa bảo đảm answer/citation tốt.

Giới hạn: chỉ một tác phẩm và 5 câu test có đáp án; benchmark do AI hỗ trợ soạn và học viên đã kiểm tra, không coi là bộ đánh giá độc lập của bên thứ ba. Test retrieval đã được xem trước giai đoạn agent; sửa agent dựa trên dev/demo, không dùng test agent để tuning. Không khái quát điểm tập nhỏ thành độ chính xác chung. Xác nhận human verification diễn ra sau benchmark, không thay thời điểm chốt hoặc kết quả. `README.md` giữ nguyên bản gốc; quá trình triển khai chi tiết nằm riêng trong `TONG_HOP_QUA_TRINH_VA_KET_QUA.md`.

## Thử thách nâng cao (nếu thực hiện)

**Không thực hiện phần nâng cao; không đề nghị điểm bonus.** Bảng dưới là trạng thái không áp dụng, không phải kết quả đo 0% hoặc tuyên bố đạt ngưỡng 90%.

- Tài liệu, nguồn, quyền sử dụng, số trang và phiên bản: không có bộ tài liệu nâng cao từ 100 trang đa phương thức. Corpus Alice của phần cơ bản có 69 đơn vị logic, không thay thế yêu cầu tài liệu nâng cao.
- Cách xử lý text, bảng, ảnh, biểu đồ; phạm vi index và phần chưa xử lý: phần cơ bản chỉ index text; không thực hiện pipeline bảng/ảnh/biểu đồ cho thử thách nâng cao.
- Cách chia benchmark, schema evidence, model và cấu hình đã chốt trên dev: không có benchmark nâng cao riêng; không dùng kết quả test cơ bản làm kết quả bonus.

| Nhóm test | Đạt / tổng | Tỷ lệ | Lỗi / nhận xét |
|---|---|---|---|
| Bảng | Không áp dụng | Không đo | Không thực hiện phần nâng cao |
| Ảnh, sơ đồ | Không áp dụng | Không đo | Không thực hiện phần nâng cao |
| Biểu đồ | Không áp dụng | Không đo | Không thực hiện phần nâng cao |
| Multi-hop | Không áp dụng | Không đo | Không có benchmark nâng cao riêng |
| Text | Không áp dụng | Không đo | Kết quả text cơ bản đã báo ở các mục trên |
| Thiếu bằng chứng | Không áp dụng | Không đo | Kết quả cơ bản không được tính làm bonus |
| **Toàn bộ** | Không áp dụng | Không đo | Không đề nghị điểm nâng cao |

- Trace, nhãn và evidence từng câu; thời gian, chi phí, lỗi hệ thống: không có artifact nâng cao; các artifact đã nêu thuộc phần cơ bản.
- Giới hạn, cách tái lập và đường dẫn benchmark: không áp dụng cho phần nâng cao. Tái lập phần cơ bản theo `docs/RUNBOOK.md`, benchmark `data/alice/cases.json`.
