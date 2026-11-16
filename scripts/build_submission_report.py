"""Fill the original repository report structure from recorded results."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.rag.common import load


def rate(value):
    n, total = value['n'], value['N']
    return f'{n}/{total} ({n/total:.1%})' if total else '0/0 (không áp dụng)'


def cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def row(values):
    return '| ' + ' | '.join(cell(value) for value in values) + ' |'


def build():
    root = ROOT/'results/final-agent'
    final = load(root/'final-summary.json')
    env = load(ROOT/'results/environment.json')
    verified = final['human_verified']
    verification = ('Học viên đã kiểm tra lại toàn bộ, `human_verified=true`' if verified
                    else 'Chưa có xác nhận đầy đủ của học viên, `human_verified=false`')
    text = f'''# Báo cáo Day 7

**Họ và tên:** Hoàng Dương Anh Quân · **MSSV:** 2A202603735 · **Lớp:** L3B.

## Dữ liệu và benchmark

- Nguồn, quyền sử dụng, số trang và số chunk: *Alice's Adventures in Wonderland*, Lewis Carroll, [Project Gutenberg #11](https://www.gutenberg.org/ebooks/11), tác phẩm nguyên gốc public domain tại Hoa Kỳ; giữ thông báo và giấy phép PG trong bản raw. Tái dùng **238 chunk cấu hình B, 69 đơn vị nội dung logic** từ [repo Day 6 của học viên](https://github.com/HoangQuan23112004/K5-L3B-Day06-HoangDuongAnhQuan-2A202603735-DataIngestionEngineering), commit `82080a89e87cf6eeab2c9709d8c50276ce8dd2c7`. Đây là đơn vị văn bản do pipeline chia, không phải trang PDF. Giữ nguyên chunk ID, text, source, page và metadata; provenance tại `data/alice/manifest.json`, nguồn/giấy phép tại `vendor/day6/data/`.
- Vector store, embedding model, phiên bản và số chiều: **Qdrant local cosine**, collection `alice_B`, qdrant-client {env['packages']['qdrant-client']}; **FastEmbed {env['packages']['fastembed']}**, model `sentence-transformers/all-MiniLM-L6-v2`, **384 chiều**, ONNX Runtime {env['packages']['onnxruntime']}. Dùng document `.embed` và query `.query_embed` như Day 6. Vì repo Day 6 không công bố snapshot/vectors, tái tạo store từ chunk gốc; mất khoảng **116,87 giây**, gồm tải model/embedding/lưu store. Hash ONNX khớp Day 6; chi tiết tại `results/index-manifest.json` và `results/environment.json`.
- Agent model, cách chạy và phân chia dev/test: **Groq `openai/gpt-oss-20b`**, endpoint OpenAI-compatible, Python {env['python']}; key nạp từ `.env`, embedding vẫn chạy local. Benchmark **24 câu**: dev **15 có đáp án + 2 thiếu evidence**, test **5 có đáp án + 2 thiếu evidence**. Giữ Q01–Q15 dev của Day 6; loại Q16–Q20 test cũ đã lộ, soạn D7-T01–T05 trước thí nghiệm Day 7. Lệnh chạy và cấu hình tại `docs/RUNBOOK.md`, `docs/PROTOCOL.md`, `docs/AGENT_PROTOCOL.md`.
- Cách xác định câu có/thiếu evidence và tiêu chí chấm: câu có đáp án có `expected_answer` và evidence đúng nguồn/trang trong `data/alice/cases.json`; các mục `gold` là bằng chứng thay thế, hỗ trợ thêm `evidence_groups` cho nhiều nhóm bắt buộc. Câu thiếu evidence hỏi serial number đồng hồ, sinh nhật người chị, tuổi Bill hoặc địa chỉ Alice; kiểm tra toàn văn và ghi `absence_reason`, không kết luận chỉ từ top-k. Không truyền gold/đáp án chuẩn vào agent/retriever. Chấm answer **0/1/2**, context **0/1/2**, từng citation **true/false**, abstention theo output thực tế. Nhãn ban đầu **AI-assisted**; {verification}. Xác nhận lưu riêng tại `results/final-agent/human-verification.json`, không thay điểm hoặc khóa cấu hình trước test.

## Retrieval và thử nghiệm

| Cấu hình | Phương pháp, top-k, filter, rerank, context budget | Giả thuyết / thay đổi | Split | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Thời gian / chi phí |
|---|---|---|---|---|---|---|---|
'''
    specs = [
        ('Baseline', 'bm25', 'dev', 'BM25 k1=1.5, b=0.75; k=3; budget 6000 ký tự', 'Đối sánh chính xác tên nhân vật và thuật ngữ trong Alice.'),
        ('Phương pháp 2', 'dense', 'dev', 'Dense cosine qua FastEmbed + Qdrant; k=3; budget 6000 ký tự', 'Embedding khôi phục câu hỏi diễn đạt khác từ khóa.'),
        ('Phương pháp 3', 'hybrid', 'dev', 'Hybrid RRF k=60; 12 candidate/nhánh; top-3; budget 6000 ký tự', 'Kết hợp ngữ nghĩa và từ khóa bằng rank fusion.'),
        ('Cải thiện 1', 'hybrid-wide', 'dev', 'Hybrid RRF; 24 candidate/nhánh; top-6; budget 12000 ký tự', 'Mở candidate/context để giữ evidence ngoài top-3.'),
        ('Cải thiện 2', 'bm25-wide', 'dev', 'BM25; top-6; budget 12000 ký tự', 'Giữ thêm điều kiện, đổi lại context lớn hơn; cấu hình chọn.'),
        ('Thử nghiệm bổ sung', 'bm25-small', 'dev', 'BM25; top-3; budget 1800 ký tự', 'Thử giảm context; đo ảnh hưởng mất evidence do không vừa budget.'),
        ('Cấu hình đã chọn', 'bm25-wide', 'test', 'BM25; top-6; budget 12000 ký tự', 'Đánh giá sau khi đã chốt trên dev.'),
        ('Baseline', 'bm25', 'test', 'BM25; top-3; budget 6000 ký tự', 'Đối chứng trên cùng bộ test.'),
    ]
    for label, config, split, method, hypothesis in specs:
        directory = ROOT/(f'results/groq-retrieval/{config}-dev' if split == 'dev' else f'results/alice/{config}-test')
        result = load(directory/'summary.json')
        method += '; không rerank; filter chapter theo câu hỏi khi có'
        text += row([f'{label} ({config})', method, hypothesis, split, rate(result['hit_at_1']),
                     rate(result['hit_at_3']), rate(result['context_evidence_rate']),
                     f"Median {result['median_ms']:.2f} ms/câu; API retrieval 0 USD"]) + '\n'
    text += '''
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
'''
    for entry in final['runs']:
        audit, summary = entry['audit'], entry['summary']
        grades = audit['grounded_answer']
        searches = summary['search_call_counts']
        text += row([f"{entry['name']} / {entry['split']}", rate(audit['tool_use']),
                     f"{sum(searches)} search; {min(searches)}–{max(searches)}/câu",
                     f"0/1/2: {grades['0']}/{grades['1']}/{grades['2']}; TB {grades['mean']:.3f}/2",
                     rate(audit['citation_validity']), rate(audit['answer_citation_coverage']),
                     rate(audit['abstention']), rate(audit['false_abstention'])]) + '\n'
    text += '''
Bốn run cuối có **17/17, 17/17, 7/7, 7/7 câu chạy thành công; lỗi thực thi cuối = 0**. Trên test, baseline có 5 câu answer=2; wide có 4 câu answer=2 và 1 câu answer=1. Cả hai từ chối đúng 2/2 câu thiếu evidence, không từ chối nhầm câu có đáp án. Với câu có đáp án, từ chối chấm 0; câu lỗi provider được báo riêng và chỉ retry lỗi, không chọn lại các answer sai.

| Query ID | Loại câu | Tool call và kết quả | Câu trả lời và citation | Nhãn, lý do |
|---|---|---|---|---|
'''
    # Include representative dev failures and all 7 test cases per configuration.
    for entry in final['runs']:
        directory = ROOT/entry['directory']
        reviews = {r['query_id']: r for r in load(directory/'reviews.json')}
        for trace in load(directory/'traces.json'):
            if entry['split'] == 'dev' and trace['query_id'] not in ('Q01', 'Q07', 'Q11', 'Q14'):
                continue
            label = reviews[trace['query_id']]
            searches = sum(e['event'] == 'search' for e in trace['events'])
            kind = 'Thiếu evidence' if label['answer_grade'] == 'not_applicable' else 'Có đáp án'
            grade = f"answer={label['answer_grade']}; context={label['context_grade']}; citation={sum(label['citation_support'])}/{len(label['citation_support'])}"
            if label['answer_grade'] == 'not_applicable':
                grade = f"abstention_correct={label['abstention_correct']}; context={label['context_grade']}"
            text += row([f"{trace['query_id']} ({entry['name']}/{entry['split']})", kind,
                         f"{searches} search; {trace['status']}; cuối={trace['events'][-1]['event']}",
                         trace['answer'], f"{grade}. {label['reason']}"]) + '\n'
    text += '''
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

'''
    for entry in final['runs']:
        result = entry['summary']
        text += f"- **{entry['name']}/{entry['split']}:** median {result['median_ms']/1000:.2f} giây/câu; context trung bình {result['average_context_chars']:.0f} ký tự; prompt/completion tokens **{entry['prompt_tokens']:,}/{entry['completion_tokens']:,}**.\n"
    text += '''
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
'''
    for name in ('MSSV_HoTen.md', '2A202603735_HoangDuongAnhQuan.md'):
        (ROOT/'report/individual'/name).write_text(text, encoding='utf-8')
    print('Filled original report format in MSSV_HoTen.md and named submission report.')


if __name__ == '__main__':
    build()
