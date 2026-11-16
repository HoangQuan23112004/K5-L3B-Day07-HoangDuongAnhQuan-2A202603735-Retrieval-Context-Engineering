"""Build the report from recorded runs; never invent missing agent metrics."""
import hashlib
import importlib.metadata
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.rag.common import load, save


def fraction(metric):
    return f"{metric['n']}/{metric['N']} ({100*metric['rate']:.1f}%)" if metric['rate'] is not None else 'N/A'


def build():
    output = ROOT/'results/alice'
    names = ['bm25', 'dense', 'hybrid', 'hybrid-wide', 'bm25-wide', 'bm25-small']
    rows = []
    for split, configs in [('dev', names), ('test', ['bm25', load(output/'selection.json')['selected']])]:
        for name in dict.fromkeys(configs):
            summary = load(output/f'{name}-{split}/summary.json')
            cfg = load(ROOT/f'configs/{name}.json')
            rows.append(f"| {name} | {split} | {cfg['top_k']} / {cfg['budget_chars']} | {fraction(summary['hit_at_1'])} | {fraction(summary['hit_at_3'])} | {fraction(summary['context_evidence_rate'])} | {summary['median_ms']:.2f} | {summary['average_context_chars']:.0f} |")
    model_hashes = {str(p.relative_to(ROOT/'artifacts/model-cache')): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (ROOT/'artifacts/model-cache').rglob('*') if p.is_file() and p.name in ('model.onnx', 'config.json', 'tokenizer.json', 'tokenizer_config.json', 'special_tokens_map.json')}
    environment = {'python': platform.python_version(), 'platform': platform.platform(),
                   'packages': {name: importlib.metadata.version(name) for name in ['fastembed', 'qdrant-client', 'onnxruntime', 'numpy', 'tokenizers']},
                   'model_files_sha256': model_hashes,
                   'source_git_commit': '82080a89e87cf6eeab2c9709d8c50276ce8dd2c7',
                   'agent_status': 'Deferred by user; no live agent benchmark performed'}
    save(ROOT/'results/environment.json', environment)
    (ROOT/'requirements-lock.txt').write_text(subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True), encoding='utf-8')
    save(ROOT/'results/index-manifest.json', load(ROOT/'artifacts/qdrant-day6-b.manifest.json'))
    save(ROOT/'results/provider-check.json', {'provider': 'OpenAI-compatible at api.openai.com', 'operation': 'embedding connectivity check',
         'model': 'text-embedding-3-small', 'inputs': 1, 'status': 'error', 'http_status': 429,
         'note': 'Observed live before Day 6 local integration. Not a benchmark result. No credential or raw provider error body retained.',
         'groq_status': 'Adapter and configuration added; no live Groq call without a configured Groq key.'})
    reviews = {
        'D7-T01': 'Nguồn liệt kê đầy đủ Ambition, Distraction, Uglification, Derision trong lời Mock Turtle; có ID, nguồn và trang logic 52.',
        'D7-T02': 'Lời Gryphon nói họ viết tên vì sợ quên trước khi hết phiên tòa; context giữ nguyên nguồn và trang logic 60.',
        'D7-T03': 'Đoạn có đủ ba ngày và hành động cộng rồi đổi sang shillings/pence; context giữ điều kiện và nguồn, trang logic 61.',
        'D7-T04': 'Đoạn mô tả đặt Lizard đầu chúc xuống và lấy ra đặt lại đúng chiều; đủ cả lỗi lẫn cách sửa, trang logic 64.',
        'D7-T05': 'Đoạn có inkstand do Queen ném và Bill dùng mực chảy trên mặt để viết; đủ bằng chứng, trang logic 67.',
    }
    context_audit = []
    for name in ('bm25', 'bm25-wide'):
        traces = load(output/f'{name}-test/traces.json')
        for trace in traces:
            cid = trace['query_id']
            context_audit.append({'config': name, 'query_id': cid, 'review_type': 'ai_assisted', 'human_verified': False,
                'context_grade': 2 if cid in reviews else None,
                'reason': reviews.get(cid, 'Câu thiếu evidence: cần agent thật để kiểm tra từ chối; retrieval tìm được đoạn liên quan không chứng minh có đáp án.'),
                'agent_answer_grade': None, 'abstention_correct': None})
    save(output/'context-audit.json', context_audit)
    body = '''# Báo cáo Day 7 — Hoàng Dương Anh Quân

- MSSV: **2A202603735** · Lớp **L3B**.
- Phạm vi đã thực hiện: code agent và benchmark retrieval thật. Theo lựa chọn của học viên, nối model trả lời để bước sau; **chưa hoàn thành benchmark agent thật để nộp toàn bộ yêu cầu Day 7**.

## Dữ liệu, embedding và vector store

Tái dùng corpus Alice’s Adventures in Wonderland (Lewis Carroll, Project Gutenberg #11) từ repo Day 6 của học viên, commit `82080a89e87cf6eeab2c9709d8c50276ce8dd2c7`. Cấu hình Day 6 đã chọn là B: **238 chunk**, giữ nguyên ID, text, source, page, metadata. Corpus có **69 đơn vị nội dung logic**, mỗi đơn vị ít nhất 1500 ký tự theo manifest Day 6; không phải trang PDF. Bản raw giữ thông báo Project Gutenberg, tác phẩm nguyên gốc public domain tại Hoa Kỳ; không dùng ảnh/bản dịch. Snapshot tại `vendor/day6/`; manifest Day 7 tại `data/alice/manifest.json`.

Embedding thật: `sentence-transformers/all-MiniLM-L6-v2`, **384 chiều**, FastEmbed 0.7.4/ONNX CPU, document `.embed` và query `.query_embed` đúng cách Day 6. Qdrant local cosine collection `alice_B`. Repo Day 6 không công bố snapshot/vector, vì vậy tái tạo collection từ chunk gốc, không tuyên bố đã tải nguyên database cũ. Tái tạo mất khoảng **116.87 giây**, gồm tải model và embedding, không gọi API trả phí; manifest ở `results/index-manifest.json`. Hash từng file model, phiên bản runtime/thư viện có tại `results/environment.json`; lock dependencies tại `requirements-lock.txt`. SQLite cosine cũng có adapter và test, nhưng các số benchmark dưới đây dùng Qdrant.

## Benchmark và chống rò rỉ

24 câu: **dev 15 có đáp án + 2 thiếu evidence; test 5 có đáp án + 2 thiếu evidence**. Tái dùng Q01–Q15 của Day 6 làm dev. Q16–Q20 cũ bị loại vì giao thức Day 6 xác nhận đã được xem; soạn D7-T01–T05 mới trước khi chạy retrieval dev, kèm evidence/source/page. Bốn câu thiếu evidence hỏi thông tin sát tác phẩm nhưng không có trong toàn văn; ghi lý do kiểm tra ở từng case. Nhãn do AI hỗ trợ, chưa được người độc lập xác nhận.

Gold/expected_answer không được truyền cho model hoặc retriever. Filter chapter của Q04/Q07/Q13 giữ từ thông tin chương đã có trong câu hỏi. Mọi phương pháp dùng cùng corpus/index/nhãn. Hit@k yêu cầu đúng nguồn, đúng trang logic, chứa trọn evidence. `gold` là các bằng chứng thay thế; có hỗ trợ `evidence_groups` cho đủ nhiều nhóm bắt buộc. Mẫu số chỉ 15/5 câu có đáp án chạy thành công; mọi run này không có lỗi. Hai câu thiếu evidence mỗi split chỉ được ghi trace retrieval, chưa chấm abstention khi chưa có agent.

Giao thức tại `docs/PROTOCOL.md` được ghi trước test. Chọn theo Context Evidence Rate, rồi Hit@3, Hit@1, hòa ưu tiên budget/top-k nhỏ hơn. Lưu `results/alice/frozen-retrieval.json` trước hai run test; cấu hình được chọn là **BM25-wide, top-6, budget 12000 ký tự**, baseline là BM25 top-3/budget 6000. Không chỉnh retrieval sau khi xem test.

## Kết quả retrieval và context

BM25 dùng k1=1.5, b=0.75, Unicode tokenization. Dense truy vấn model thật và Qdrant. Hybrid hợp nhất bằng RRF k=60, không cộng trực tiếp score khác thang. Hybrid-wide lấy 24 candidate mỗi nhánh. Mỗi pipeline vẫn xuất top-3 để so ranking khi context dùng top-6.

| Cấu hình | Split | top-k / budget ký tự | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Median ms | Context TB ký tự |
|---|---|---|---|---|---|---|---|\n'''
    body += '\n'.join(rows)
    body += '''

Mỗi cấu hình tốn **0 USD phí API retrieval**; không quy đổi điện/phần cứng. Thời gian gồm xử lý query, query embedding nếu dùng và mở/đóng Qdrant; median giảm ảnh hưởng lượt load model đầu. Context budget tính cả ID/nguồn/trang trong evidence context, không bao gồm system prompt/câu hỏi/schema tool. Thời gian từ các run ngắn không đủ để khẳng định hơn kém vài millisecond.

## Thử nghiệm cải thiện và phân tích lỗi dev

1. **Q04, bằng chứng nằm ngoài top-3 BM25.** Baseline xếp các đoạn liên quan chai/poison ở trang logic 4 lên đầu nhưng đoạn mô tả kiểm tra nhãn trước khi uống nằm hạng **4**, ID bắt đầu `ea2ed1225b`. Giả thuyết: top-6 giữ đủ điều kiện. BM25-wide lấy được đoạn hạng 4; Context Evidence Rate tăng **14/15 → 15/15**, Hit@3 vẫn 14/15. Đây là cấu hình context khác, không tính thành phương pháp retrieval thứ tư.
2. **Q11, evidence bị context budget loại bỏ.** BM25-small budget 1800 giữ hai đoạn đầu `9c597ff0df...`, `047adf02bf...`, bỏ evidence hạng 3 `77f4248a0e...`. Budget 6000 giữ đủ cả ba đoạn; Context Evidence Rate toàn dev **12/15 → 14/15**. Thử giảm context không cải thiện chất lượng, nên không chọn. Không cắt đoạn để ép evidence vừa budget vì có thể mất điều kiện.
3. **Q09, hybrid mặc định thiếu đoạn trả lời.** Hybrid-wide đưa evidence hạng 4 `b198754550...` vào context, tăng **14/15 → 15/15**. Đổi lại trung bình context khoảng gấp đôi và cần query embedding, trong khi BM25-wide đạt context tương đương với Hit@1 dev tốt hơn. Dense riêng bỏ lỡ Q02/Q09/Q14, ví dụ Q02 bị các lần White Rabbit xuất hiện khác chiếm top-3; dense không luôn tốt hơn lexical trên bộ câu hỏi có từ khóa đặc trưng.

Ba thử nghiệm cải thiện được đo riêng: hybrid so baseline BM25; hybrid-wide mở candidate/context; BM25-wide mở context. Các kết quả không tăng điểm đều giữ lại trong bảng. Theo tiêu chí chốt trước, chọn BM25-wide trên dev. Test cho cả baseline và selected đều **5/5** ở ranking/context; vì chỉ 5 câu, không kết luận selected cải thiện test. Selected gửi context trung bình lớn hơn, là chi phí cần đánh giá lại khi nối agent.

## Audit context test

Đã đọc các đoạn hỗ trợ cả 5 câu có đáp án cho baseline và selected; nhãn AI-assisted/lý do ở `results/alice/context-audit.json`, **human_verified=false**. Mỗi cấu hình có 5 nhãn context=2, 0 nhãn=1, 0 nhãn=0. Các lý do cụ thể: bốn nhánh Arithmetic; juror sợ quên tên; cộng ngày rồi quy đổi shillings/pence; Lizard bị đặt ngược và sửa lại; Bill dùng mực trên mặt viết tiếp. Học viên cần đối chiếu nguồn và xác nhận trước nộp. Đây là audit context, không phải nhãn câu trả lời của agent.

## Agent, trace và phần còn lại

`src/rag/agent.py` có vòng lặp model/tool thật qua HTTP adapter Ollama/OpenAI-compatible/Groq, với `search`, `finish`, `abstain`. Tối đa số search trong JSON config; tìm lại khi chưa đủ evidence, ưu tiên chunk từ query mới, dedup ID và giữ nguyên provenance trong budget. Tài liệu được coi là dữ liệu không đáng tin, không thực thi chỉ dẫn trong đó. Answer chỉ nhận khi từng citation ID có trong context và xuất hiện dưới dạng `[id]`; cần người chấm xác nhận nguồn hỗ trợ từng phát biểu.

Lưu query, tool args/results, context cuối, answer/citation, lỗi, elapsed time, provider usage. `traces.jsonl` flush mỗi câu; lỗi giữ partial events. Kết nối lỗi không bị thay thành mock/empty success. CLI `audit` kiểm tra nhãn và tổng hợp grounded answer/citation/abstention; agent test chỉ chạy sau dev thật và audited agent lock, retrieval lock không đủ.

**Theo lựa chọn của học viên, chưa nối model và chưa chạy benchmark agent thật.** Mọi grounded-answer/tool-use/citation-support/abstention metric hiện chưa có, không báo 0% hoặc 100% thay cho chưa đo. Một lần kiểm tra embedding API thật nhận HTTP 429, lưu ở `results/provider-check.json`; sau đó toàn bộ embedding benchmark dùng model local, không ảnh hưởng kết quả retrieval. Đã bổ sung cấu hình Groq `openai/gpt-oss-20b` qua endpoint tương thích OpenAI; xem `docs/GROQ.md`. Chưa có lần gọi Groq thật để xác nhận tương thích của model/account.

## Tái lập và giới hạn

Xem `docs/RUNBOOK.md`. Lệnh chính: `python scripts/prepare_day6.py`, `python -m src.rag index --provenance ...`, `python scripts/experiments.py dev`, đọc lỗi dev, rồi `python scripts/experiments.py finalize`. Dùng output/index mới khi tái lập, không ghi đè kết quả đã công bố. Test tự động đã chạy **33 test thành công**, gồm SQLite, Qdrant thật ở mức integration với vector fixture, adapter Groq và agent mock; các mock chỉ kiểm tra code, không được tính vào điểm chất lượng agent.

Giới hạn: cùng một tác phẩm/nhân vật, test nhỏ và AI hỗ trợ soạn; exact quote chưa nhận diện evidence diễn đạt tương đương; BM25 chưa tách từ tiếng Việt; whole-chunk budget có thể bỏ evidence; chưa có grounded agent benchmark. Không làm bonus tài liệu đa phương thức 100 trang. Để hoàn tất toàn bộ bài nộp, cần key/model thật, dev audit, lock agent và test agent cho baseline/selected, sau đó đọc và chấm tối thiểu 5 câu có đáp án + 2 câu thiếu evidence cùng citation/reason.
'''
    report = ROOT/'report/individual/2A202603735_HoangDuongAnhQuan.md'
    report.write_text(body, encoding='utf-8')
    print(report.relative_to(ROOT))


if __name__ == '__main__':
    if (ROOT/'results/final-agent/final-summary.json').exists():
        from build_final_report import build as build_final
        build_final()
    else:
        build()
