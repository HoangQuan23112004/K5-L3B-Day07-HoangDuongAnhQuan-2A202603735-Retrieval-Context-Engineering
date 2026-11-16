# Giao thức thí nghiệm Day 7

Giao thức giai đoạn retrieval, ghi trước khi chạy test retrieval Day 7. Lúc đầu học viên chọn nối agent model sau. Giai đoạn agent Groq đã được thực hiện tiếp theo [AGENT_PROTOCOL.md](AGENT_PROTOCOL.md), với lock và audit riêng trước test agent.

- Corpus: 238 chunk B, nguyên ID/text/source/page/metadata từ Day 6 commit `82080a89e87cf6eeab2c9709d8c50276ce8dd2c7`. 69 đơn vị nội dung logic, không gọi là trang PDF.
- Embedding: FastEmbed 0.7.4, `sentence-transformers/all-MiniLM-L6-v2`, 384 chiều, document `.embed`, query `.query_embed`, như Day 6. Tái tạo Qdrant cosine `alice_B` vì snapshot Day 6 không có trên GitHub; lưu model hash, index manifest và chi phí tái tạo.
- Dev: 15 câu cũ Q01–Q15 + 2 câu thiếu evidence. Test: 5 câu mới D7-T01–T05 + 2 câu thiếu evidence; Q16–Q20 của Day 6 bị loại vì đã lộ trong bài cũ. Test mới do AI hỗ trợ soạn và đã được học viên xác nhận kiểm tra lại; không coi là benchmark do bên thứ ba độc lập xây dựng.
- Gold và expected_answer chỉ dùng để kiểm chứng dữ liệu và tính metric. Agent nhận duy nhất câu hỏi và filter đã cung cấp, không nhận cả case object. Filter chương của các câu dev được giữ từ câu hỏi Day 6, không suy từ gold.
- Ba phương pháp: BM25 (`k1=1.5`, `b=0.75`), dense Qdrant cosine, hybrid RRF (`k=60`, 12 candidate mỗi nhánh). Cùng corpus/index/benchmark, top-3 cho ranking.
- Cấu hình cải thiện: hybrid RRF so với BM25; hybrid-wide top-6/24 candidate/12000 ký tự; BM25-wide top-6/12000 ký tự. Thử thêm budget 1800 ký tự để xem đánh đổi giảm context. Baseline budget 6000 ký tự. Các giả thuyết có trong JSON config; không coi thay top-k là phương pháp retrieval mới.
- Tiêu chí chọn **trước test**: Context Evidence Rate cao nhất, sau đó Evidence Hit@3, rồi Hit@1; hòa chọn budget thấp hơn, rồi top-k thấp hơn, cuối cùng thứ tự config trong script. Báo latency nhưng không dùng vài millisecond nhiễu làm tiêu chí quyết định.
- Hit@k đúng nguồn, đúng trang logic và chứa nguyên evidence; `gold` là các lựa chọn thay thế. `evidence_groups` mở rộng cho multi-hop: phải có đủ mỗi nhóm. Mẫu số retrieval chỉ gồm câu có đáp án chạy thành công; số lỗi và tổng số câu luôn báo riêng.
- Context giữ nguyên chunk kèm nguồn/trang, loại trùng ID, bỏ chunk không vừa budget, không cắt giữa điều kiện. Budget tính ký tự của evidence context, không bao gồm system prompt/câu hỏi/schema tool. So sánh top-3 ranking ngay cả khi final context dùng top-6.
- CLI `freeze --retrieval-only` lưu corpus/cases/config/index/model identity trước test; chỉ baseline và selected được chạy. Lock này không cho phép chạy agent test. Muốn đánh giá agent, cần chạy dev thật, chấm audit, rồi tạo lock agent riêng trước test.
- Chỉ số khớp quote tự động không thay nhãn ngữ nghĩa. Mỗi câu trả lời và citation cần người đọc kiểm chứng. Không suy citation support hay abstention từ ID hoặc từ việc câu hỏi thuộc nhóm thiếu evidence.
- Giai đoạn retrieval ban đầu chưa có điểm chất lượng agent. Kết quả agent hoàn tất sau đó ở `results/final-agent/` và bản tổng hợp ở thư mục gốc. Lỗi HTTP 429 của lần kiểm tra API vẫn giữ riêng, không thay bằng mock hay báo một câu trả lời giả.
