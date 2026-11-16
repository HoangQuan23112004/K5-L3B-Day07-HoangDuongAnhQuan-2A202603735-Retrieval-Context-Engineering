# Day 6 snapshot

Nguồn: [repo của Hoàng Dương Anh Quân](https://github.com/HoangQuan23112004/K5-L3B-Day06-HoangDuongAnhQuan-2A202603735-DataIngestionEngineering), commit `82080a89e87cf6eeab2c9709d8c50276ce8dd2c7`.

Chỉ lưu các file dữ liệu và provenance cần tái tạo. `results/run.json`, `selection.json` là **kết quả Day 6**, không phải kết quả Day 7. Mã Day 7 do dự án này hiện thực. Nguồn và quyền sử dụng tác phẩm xem `data/SOURCES.md`, `data/manifest.json` và thông báo gốc trong `starter/data/alice.txt`.

Git blob của bản Alice trên GitHub dùng LF; hash raw trong manifest Day 6 được tính trên bản Windows CRLF. Hai hash khác nhau do xuống dòng, nội dung tác phẩm giữ nguyên. Số `page` là 69 đơn vị nội dung logic do Day 6 tạo, không phải số trang PDF. Repo không công bố thư mục Qdrant hoặc embedding vectors; Day 7 tái tạo collection bằng đúng model và 238 chunk cấu hình B.

`benchmark/PROTOCOL.md` của Day 6 xác nhận test cũ đã được xem. Day 7 chỉ tái dùng 15 câu dev và tạo 5 câu test mới; không lấy điểm test cũ làm kết quả độc lập.
