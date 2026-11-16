# Nguồn và cách sử dụng

- [Project Gutenberg #11](https://www.gutenberg.org/ebooks/11): *Alice's Adventures in Wonderland*, Lewis Carroll, nguyên tác 1865, tác giả mất 1898. Catalog ghi public domain tại Hoa Kỳ. File `starter/data/alice.txt` giữ toàn bộ thông báo và giấy phép PG; chỉ lấy phần nội dung chương để embedding. Không dùng bản dịch hoặc ảnh minh họa. Có thể đối chiếu quyền và điều kiện sử dụng trong header/footer raw.
- [Qdrant Python local mode](https://github.com/qdrant/qdrant-client#local-mode): dùng `QdrantClient(path=...)` lưu bền, cosine, payload filter, local exact search; không tự quản một SQLite thay vector store.
- [FastEmbed](https://qdrant.github.io/fastembed/): ONNX CPU embedding. Model được tải thật, không fallback sang mock.
- [Model card all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2): semantic embedding tiếng Anh 384 chiều. Bản ONNX do FastEmbed phân giải được ghi tên snapshot và hash file trong `run.json`.


