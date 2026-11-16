# Giao thức chốt trước retrieval

- Corpus: nguyên tác tiếng Anh Alice, PG #11. Benchmark viết với AI hỗ trợ, evidence lấy nguyên đoạn và kiểm chứng tồn tại trong nguồn chuẩn hóa.
- Q01–Q15 là dev (chương I–VIII); Q16–Q20 là test (chương IX–XII). Tách theo chương, nhưng cùng tác phẩm/nhân vật nên vẫn có rò rỉ chủ đề.
- Câu có filter: Q04, Q07, Q13 (dev), Q18 (test). Chương xuất hiện rõ trong câu hỏi, không lấy gold_page/document_id làm filter.
- A: cửa sổ 800 ký tự, overlap 100. B: nhóm đoạn, tối đa 800 ký tự, không overlap; đoạn quá dài ưu tiên tách câu/từ. C: cùng chunk/vector B, chỉ thêm filter được cung cấp trong câu hỏi.
- Cùng model all-MiniLM-L6-v2, cosine, Qdrant local exact, top-3. Không thêm đáp án/evidence vào query.
- Chọn cấu hình bằng dev: ưu tiên Evidence Hit@3, rồi Hit@1, rồi ít chunk; hòa chọn A/B/C theo thứ tự tên. Ghi selection.json trước chạy truy xuất test. Test chạy cả ba để báo cáo, không dùng để chỉnh tham số.
- Gold là toàn bộ đoạn hỗ trợ đáp án. Hit phải đúng document/page VÀ chứa trọn evidence trong một chunk. Nhận định tương đương cần người đọc xác nhận, không tự ghi hit.
- Coherence: 10 unit đầu theo page, vị trí ký tự 100; lấy chunk đầu chứa vị trí này ở từng cấu hình. Chấm 0/1/2 có lý do.
- Grounding: cùng 5 câu test × 3 cấu hình; metadata: toàn bộ 45 hit test. Nhãn thủ công để trống cho học viên đọc và chấm; không suy từ metric.
- Công cụ AI đã đọc câu hỏi test để soạn code/kiểm tra gold, nên đây là split minh họa, không phải test mù độc lập. Không sửa retrieval theo điểm test.
