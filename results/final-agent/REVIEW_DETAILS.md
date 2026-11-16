# Chi tiết chấm agent

Reviewer ban đầu: Codex, AI-assisted; human_verified=true. Phần chấm có nguồn gốc AI-assisted và đã được học viên kiểm tra, xác nhận; không đổi điểm sau xác nhận.

| Run | Query | Status | Answer 0/1/2 | Context 0/1/2 | Citation đúng/tổng | Lý do |
|---|---|---|---|---|---|---|
| bm25-dev-v3 | Q01 | answered | 2 | 2 | 1/1 | Đủ hai ý: lọ rỗng và sợ làm chết người bên dưới. Context/citation có cả hai điều kiện. |
| bm25-dev-v3 | Q02 | answered | 2 | 2 | 1/1 | Trả lời đúng chiếc đồng hồ lấy từ túi áo ghi-lê. |
| bm25-dev-v3 | Q03 | answered | 2 | 2 | 1/1 | Đúng nguyên nhân sách không có tranh hay hội thoại; cách diễn giải giá trị sách khớp suy nghĩ Alice trong nguồn. |
| bm25-dev-v3 | Q04 | answered | 2 | 2 | 1/1 | Đúng hành động kiểm tra nhãn poison trước khi uống. |
| bm25-dev-v3 | Q05 | answered | 2 | 2 | 1/1 | Đúng cả độ sâu khoảng 4 inch và chiều dài nửa hành lang. |
| bm25-dev-v3 | Q06 | answered | 2 | 2 | 1/1 | Đúng món quà là thimble và nguồn mô tả Dodo long trọng trao nó. |
| bm25-dev-v3 | Q07 | abstain | 0 | 2 | N/A | Từ chối nhầm do search_limit dù context trang 14 có Dinah là mèo bắt chuột, ăn chim. Không coi context tốt là câu trả lời đúng. |
| bm25-dev-v3 | Q08 | answered | 2 | 2 | 1/1 | Trả lời đúng tên Mary Ann mà Rabbit dùng để gọi nhầm Alice. |
| bm25-dev-v3 | Q09 | answered | 2 | 2 | 1/1 | Đúng lời dọa thả Dinah vào nếu Rabbit đốt nhà; đã hết lỗi tool-use trong run này. |
| bm25-dev-v3 | Q10 | answered | 2 | 2 | 1/1 | Đủ cảnh ngồi trên nấm, khoanh tay, hút chiếc hookah dài; citation đúng đoạn giới thiệu ban đầu. |
| bm25-dev-v3 | Q11 | answered | 1 | 2 | 0/1 | Đúng việc Alice đã nếm trứng nhưng thiếu ý trẻ con ăn nhiều như rắn và thêm không thích trứng sống. Nguồn được cite không hỗ trợ toàn bộ câu trả lời. |
| bm25-dev-v3 | Q12 | answered | 2 | 2 | 1/1 | Đúng quá nhiều tiêu trong súp và không khí làm Alice hắt hơi. |
| bm25-dev-v3 | Q13 | abstain | 0 | 2 | N/A | Từ chối nhầm do search_limit; context trang 35 có Hatter nói butter wouldn't suit the works và March Hare đáp best butter. |
| bm25-dev-v3 | Q14 | answered | 1 | 1 | 1/1 | Chỉ nói ở đáy một cái giếng, thiếu loại treacle-well. Context có sống bằng treacle và vẽ treacle nhưng chưa có đoạn xác định rõ loại giếng. |
| bm25-dev-v3 | Q15 | answered | 2 | 2 | 1/1 | Đúng đủ ba vật thay thế: nhím, hồng hạc và binh lính uốn người. |
| bm25-dev-v3 | D7-D-N1 | abstain | not_applicable | 0 | N/A | Corpus không cung cấp serial number đồng hồ. Output từ chối, không bịa số; kết thúc do search_limit, không phải model chủ động gọi abstain. |
| bm25-dev-v3 | D7-D-N2 | abstain | not_applicable | 0 | N/A | Corpus không có ngày sinh chính xác người chị. Output từ chối, không bịa ngày; trace kết thúc search_limit. |
| bm25-wide-dev | Q01 | answered | 2 | 2 | 1/1 | Đủ hai ý: lọ rỗng và sợ làm chết người bên dưới. Context/citation có cả hai điều kiện. |
| bm25-wide-dev | Q02 | answered | 2 | 2 | 1/1 | Trả lời đúng chiếc đồng hồ lấy từ túi áo ghi-lê. |
| bm25-wide-dev | Q03 | answered | 2 | 2 | 1/1 | Đúng nguyên nhân sách không có tranh hay hội thoại; cách diễn giải giá trị sách khớp suy nghĩ Alice trong nguồn. |
| bm25-wide-dev | Q04 | answered | 2 | 2 | 1/1 | Đúng hành động kiểm tra nhãn poison trước khi uống. |
| bm25-wide-dev | Q05 | answered | 2 | 2 | 1/1 | Đúng cả độ sâu khoảng 4 inch và chiều dài nửa hành lang. |
| bm25-wide-dev | Q06 | answered | 2 | 2 | 1/1 | Đúng món quà là thimble và nguồn mô tả Dodo long trọng trao nó. |
| bm25-wide-dev | Q07 | abstain | 0 | 2 | N/A | Từ chối nhầm do search_limit dù context trang 14 có Dinah là mèo bắt chuột, ăn chim. Không coi context tốt là câu trả lời đúng. |
| bm25-wide-dev | Q08 | answered | 2 | 2 | 1/1 | Trả lời đúng tên Mary Ann mà Rabbit dùng để gọi nhầm Alice. |
| bm25-wide-dev | Q09 | answered | 2 | 2 | 1/1 | Đúng lời dọa thả Dinah vào nếu Rabbit đốt nhà; đã hết lỗi tool-use trong run này. |
| bm25-wide-dev | Q10 | answered | 2 | 2 | 1/1 | Đủ cảnh ngồi trên nấm, khoanh tay, hút chiếc hookah dài; citation đúng đoạn giới thiệu ban đầu. |
| bm25-wide-dev | Q11 | answered | 1 | 2 | 1/1 | Đúng việc Alice đã nếm trứng nhưng thiếu ý trẻ con ăn trứng nhiều như rắn. Không còn chi tiết trứng sống không có căn cứ như baseline. |
| bm25-wide-dev | Q12 | answered | 2 | 2 | 1/1 | Đúng quá nhiều tiêu trong súp và không khí làm Alice hắt hơi. |
| bm25-wide-dev | Q13 | abstain | 0 | 2 | N/A | Từ chối nhầm do search_limit; context trang 35 có Hatter nói butter wouldn't suit the works và March Hare đáp best butter. |
| bm25-wide-dev | Q14 | answered | 2 | 2 | 0/2 | Đáp án treacle-well đúng và đoạn 905ef... trang 38 có trong context xác nhận đầy đủ, nhưng model cite hai đoạn khác không đủ hỗ trợ. Chấm answer/context riêng với citation. |
| bm25-wide-dev | Q15 | answered | 2 | 2 | 1/1 | Đúng đủ ba vật thay thế: nhím, hồng hạc và binh lính uốn người. |
| bm25-wide-dev | D7-D-N1 | abstain | not_applicable | 0 | N/A | Corpus không cung cấp serial number đồng hồ. Output từ chối, không bịa số; kết thúc do search_limit, không phải model chủ động gọi abstain. |
| bm25-wide-dev | D7-D-N2 | abstain | not_applicable | 0 | N/A | Corpus không có ngày sinh chính xác người chị. Output từ chối, không bịa ngày; trace kết thúc search_limit. |
| bm25-test | D7-T01 | answered | 2 | 2 | 1/1 | Đủ bốn nhánh Arithmetic đúng thứ tự tên trong nguồn, không nhầm Reeling/Writhing là nhánh Arithmetic. |
| bm25-test | D7-T02 | answered | 2 | 2 | 1/1 | Đúng nguyên nhân jurors sợ quên tên trước khi phiên tòa kết thúc; không thêm nguyên nhân khác. |
| bm25-test | D7-T03 | answered | 2 | 2 | 1/1 | Đúng cả hai thao tác cộng ba ngày và đổi kết quả sang shillings/pence, không tự bịa kết quả số. |
| bm25-test | D7-T04 | answered | 2 | 2 | 1/1 | Đủ lỗi đặt Lizard đầu chúc xuống và cách lấy ra, đặt lại đúng chiều; chi tiết không cử động được có trong nguồn. |
| bm25-test | D7-T05 | answered | 2 | 2 | 1/1 | Đúng Bill dùng mực chảy trên mặt để viết tiếp; điều kiện còn mực cũng được nguồn hỗ trợ. |
| bm25-test | D7-T-N1 | abstain | not_applicable | 0 | N/A | Toàn văn không nêu tuổi chính xác Bill. Model chủ động gọi abstain với lý do thiếu bằng chứng tuổi, output không bịa số. |
| bm25-test | D7-T-N2 | abstain | not_applicable | 0 | N/A | Không có số nhà/địa chỉ bưu điện Alice trong corpus. Model chủ động gọi abstain, không lấy địa chỉ nhà Rabbit làm địa chỉ Alice. |
| bm25-wide-test-v2 | D7-T01 | answered | 2 | 2 | 1/1 | Đủ bốn nhánh Arithmetic đúng thứ tự tên trong nguồn, không nhầm Reeling/Writhing là nhánh Arithmetic. |
| bm25-wide-test-v2 | D7-T02 | answered | 2 | 2 | 1/1 | Đúng nguyên nhân jurors sợ quên tên trước khi phiên tòa kết thúc; không thêm nguyên nhân khác. |
| bm25-wide-test-v2 | D7-T03 | answered | 2 | 2 | 1/1 | Đúng cả hai thao tác cộng ba ngày và đổi kết quả sang shillings/pence, không tự bịa kết quả số. |
| bm25-wide-test-v2 | D7-T04 | answered | 2 | 2 | 1/1 | Đúng lỗi đặt đầu chúc xuống và lấy ra đặt lại thẳng. Lần thử đầu bị tool_use_failed trước khi có answer; resume chỉ câu error và giữ lịch sử. |
| bm25-wide-test-v2 | D7-T05 | answered | 1 | 2 | 0/1 | Đúng cách dùng mực trên mặt để viết, nhưng thêm trình tự sau khi Queen ném mực Bill mới ngừng viết bằng ngón tay. Nguồn dùng had left off: đã ngừng trước đó. Chấm 1 vì ý chính đúng nhưng chi tiết thời gian không được hỗ trợ. |
| bm25-wide-test-v2 | D7-T-N1 | abstain | not_applicable | 0 | N/A | Corpus không nêu tuổi Bill; output từ chối và không bịa số. Trace kết thúc search_limit, không phải model chủ động abstain. |
| bm25-wide-test-v2 | D7-T-N2 | abstain | not_applicable | 0 | N/A | Corpus không có số nhà/địa chỉ Alice; output từ chối và không gán địa chỉ Rabbit cho Alice. Trace kết thúc search_limit. |
