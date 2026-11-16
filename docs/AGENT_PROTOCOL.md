# Giao thức hoàn tất benchmark agent

## Phạm vi và so sánh

- Corpus và benchmark giữ nguyên `data/alice/`; không sửa câu test hoặc gold theo kết quả agent.
- Retrieval dev cho 6 cấu hình đã có tại `results/groq-retrieval/`, cùng Groq `openai/gpt-oss-20b` trong manifest. Retrieval chạy local, không gọi chat model.
- Baseline agent: `configs/bm25.json`, top-3, budget 6000 ký tự, tối đa 2 search.
- Cấu hình chọn từ retrieval dev: `configs/bm25-wide.json`, top-6, budget 12000 ký tự, tối đa 4 search. Giữ tiêu chí đã công bố: ưu tiên Context Evidence Rate, rồi Hit@3, Hit@1, budget/top-k. Báo riêng chất lượng câu trả lời sau khi chấm dev, không chọn lại theo test.
- Vòng thử đầu có 429 hàng loạt và lỗi tool-use Q09. Bản sửa thêm pacing/retry và trả kết quả search theo cặp assistant tool call + tool result. Chạy **lại cả hai cấu hình trên dev bằng cùng phiên bản code cuối** để so sánh công bằng; giữ các run cũ làm bằng chứng xử lý lỗi.
- Không thay prompt, tool schema, retrieval, model hay cấu hình sau khi chốt để chạy test. Nếu có lỗi hạ tầng thì chỉ retry/resume câu `error`, giữ lịch sử và công bố số lần thử. Không chạy lại câu trả lời sai để chọn kết quả tốt hơn.

## Chấm và provenance

Codex đọc từng answer, expected answer, context và từng nguồn được cite. Nhãn ban đầu được ghi `review_type: ai_assisted`, `human_verified: false`. Sau khi hoàn tất benchmark, học viên xác nhận đã kiểm tra lại toàn bộ trong hội thoại ngày 16/11/2026; trạng thái hiện tại là `human_verified: true`, giữ nguồn gốc AI-assisted. Xác nhận và hash được lưu tại `results/final-agent/human-verification.json`; không đổi nhãn, điểm, trace hoặc cấu hình. Đây là xác nhận của học viên, không phải đánh giá độc lập của bên thứ ba. File khóa trước test được giữ nguyên, kể cả mô tả trạng thái review tại thời điểm khóa.

- `answer_grade`: 0 sai/không đủ bằng chứng; 1 đúng một phần; 2 đúng và đủ. Từ chối câu có đáp án là 0.
- `context_grade`: 0 không có bằng chứng cần; 1 thiếu điều kiện/nguồn; 2 đầy đủ bằng chứng và provenance. Với câu không có đáp án, 0 nghĩa là không có evidence trả lời thông tin được hỏi, không phải phạt việc tìm đoạn gần chủ đề.
- `citation_support`: mỗi citation một nhãn, xét ID trong context và nội dung nguồn có hỗ trợ phát biểu không. Một câu có thể sai mục tiêu câu hỏi nhưng cite đúng phát biểu đó; không đồng nhất citation validity với answer grade.
- `abstention_correct`: chỉ đúng khi câu thực sự thiếu evidence và output từ chối, không thêm khẳng định vô căn cứ. Ghi rõ nếu từ chối do `search_limit` thay vì model tự gọi tool `abstain`.
- Với lỗi provider: giữ status/error/partial trace, không chuyển thành điểm chất lượng giả.

## Trình tự

### Quyết định chốt sau audit dev, trước test agent

Hai run hoàn tất không có lỗi provider: baseline `bm25-dev-v3` có grounded answer 1.60/2, context 14/15, citation 12/13; wide `bm25-wide-dev` có grounded answer 1.6667/2, context 15/15, citation 12/14. Cả hai từ chối đúng 2/2 câu thiếu evidence và từ chối nhầm 2/15 câu có đáp án.

Giữ BM25-wide làm cấu hình đã chọn theo tiêu chí context đầu tiên đã công bố, kèm điểm answer dev nhỉnh hơn. Không tuyên bố wide tốt hơn ở mọi mặt: citation precision giảm và context lớn hơn. Test agent chạy cả baseline và wide sau lock, không thay cấu hình hoặc chọn lại theo điểm test.

1. Hoàn tất dev baseline và wide; đọc/chấm tất cả 17 câu mỗi run; chạy `audit`.
2. Chạy `freeze` với hai run agent đã audit và retrieval dev của ít nhất 3 phương pháp, cùng corpus/index/model identity.
3. Chạy baseline và wide trên cùng 7 câu test. Chấm đủ 5 câu có đáp án + 2 câu thiếu evidence mỗi cấu hình; chạy `audit`.
4. Tổng hợp bảng retrieval/agent, số lỗi, số lần retry, latency, usage, ưu/nhược điểm và đường dẫn artifact. Phí API để null nếu chưa xác nhận hóa đơn; không suy ra chi phí bằng 0 vì dùng free tier.

Test retrieval cùng bộ câu hỏi đã được công bố trước giai đoạn agent. Agent được sửa dựa trên lỗi dev/Q09 và câu demo; không dùng câu trả lời test agent để tinh chỉnh. Vì nguồn/test do AI hỗ trợ soạn và test retrieval đã xem, kết quả này không được gọi là đánh giá mù hoàn toàn hoặc kiểm chứng độc lập.
