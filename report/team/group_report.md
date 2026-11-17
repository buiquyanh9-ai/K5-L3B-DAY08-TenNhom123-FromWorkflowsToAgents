# Báo cáo nhóm — Lab 8 LogiX-VN

Tối đa 5 trang ngoài phụ lục. Số liệu lấy từ file trong `src/reports/`, không chép tay từ terminal.

## 1. Thông tin nhóm

- Tên nhóm: TenNhom123
- Thành viên: xem `TEAM.md`
- Commit chốt (trùng `report/team/decision_adr.md`): `8465072` (commit chứa `src/reports/benchmark.json`, bằng chứng của ADR). Các commit sau đó chỉ bổ sung test ledger (`tests/test_ledger_shapes.py`) và báo cáo, không đổi code shape.

## 2. Mục tiêu và cách tiếp cận

**Bài toán.** LogiX-VN nhận claim hoàn phí vận chuyển. Nhóm xử lý cùng một quy trình theo bốn kiến trúc (workflow, single agent, orchestrator, swarm) với cùng chữ ký `run_claim`, rồi chọn kiến trúc ít tự chủ nhất mà vẫn làm được việc dựa trên số đo, không mặc định "multi-agent tốt hơn". Ở cả bốn shape, số tiền, approval, trần theo đơn và chống ghi trùng do code của host quyết định (`compute_compensation`, `durability.issue_refund`); model chỉ đọc và soạn chữ. Chữ trong ticket là dữ liệu của người dùng, không phải lệnh.

**Chia việc.** Nhóm có bốn thành viên:

| Thành viên | Phần việc |
| --- | --- |
| Lê Quý Toàn | Shape `workflow` và tích hợp |
| Nguyễn Thanh Tùng | Shape `orchestrator` và handoff |
| Bùi Đình Quý Anh | Shape `single` (vòng ReAct) |
| Trịnh Ngọc Ninh | Ledger, crash, benchmark, ADR |

Swarm là shape tham chiếu có sẵn, dùng để đối chứng cost và variance.

**Thứ tự làm.** Theo lịch sử commit của repo: orchestrator và workflow được viết trước (CP2), sau đó single, rồi cả nhóm xử lý ledger và crash (CP3, CP4): `crash_at` được truyền vào `issue_refund` và không bắt `InjectedCrash`. Cuối cùng là benchmark bốn shape × năm seed, tự kiểm trên `student_drop/`, test ledger TC13–TC20 và ADR (CP5).

## 3. Giải pháp

Mô tả ba shape nhóm viết (workflow, single, orchestrator): mỗi shape đọc gì, quyết định gì, gọi host ra sao. Chỉ rõ ranh giới code / model (tham khảo [docs/architecture.md](../../docs/architecture.md)), cách handoff được sanitize và trace ghi những event nào.

**Shape A — workflow** (`src/lab8/shapes/workflow.py`). Các bước Python cố định, không gọi model (`mean_model_calls` = 0):

1. Đọc claim bằng `get_claim_view` (không `SELECT *`). Claim không tồn tại thì `failed`; thiếu `order_id` thì `needs_info`, không ghi ledger.
2. `lookup_order` theo principal của claim. Đơn không nhìn thấy thì `escalated`.
3. `compute_compensation` tính quote từ dòng order, bỏ qua số ngày ghi trong ticket. Quote bằng 0 thì `denied`, không gọi host.
4. Quote lớn hơn 0 thì gọi `durability.issue_refund(conn, claim_id, <quote đầy đủ>, crash_at=crash_at)`. Host chặn thì `denied`; xung đột số tiền thì `failed`; thành công thì `resolved`.

**Shape B — single agent** (`src/lab8/shapes/single.py`). Một vòng ReAct tối đa 8 bước (`run_react`). Hàm `decide` đóng vai model: chỉ chọn tool đọc theo thứ tự `get_claim_view`, `lookup_order`, `lookup_refund_history`, `compute_compensation`, rồi đề xuất số tiền lấy từ quote, không lấy từ ticket. Mỗi lần chọn tool đều tính một lời gọi model vào `Budget` nên cost so sánh được. Vòng ReAct không có quyền gọi `issue_refund`; sau vòng lặp, code của shape gọi `issue_refund` với quote đầy đủ và forward `crash_at`. Lỗi trong vòng ReAct được bắt và trả `failed`, riêng `InjectedCrash` được ghi trace rồi ném lại.

**Shape C — orchestrator** (`src/lab8/shapes/orchestrator.py`). Orchestrator dựng handoff bằng `lab8.handoff.make_handoff` với allowlist, `facts` để rỗng và chỉ ba tool đọc: `lookup_order`, `lookup_policy`, `compute_compensation`. `run_readonly_investigators` chạy các tool đó; investigator không có registry ghi. Orchestrator lấy order view và quote từ kết quả investigator rồi gọi `issue_refund` với quote đầy đủ và `crash_at`. Handoff không mang `parent_secret`, header thô hay dòng claim đầy đủ qua ranh giới.

**Ranh giới code và model (chung cho cả ba).** Số tiền do `compute_compensation` tính. Approval, trần hoàn theo đơn và idempotency (`refund:{claim_id}`) do `durability.issue_refund` kiểm trong một transaction SQLite. Shape luôn truyền quote đầy đủ và để host trừ phần đã hoàn trước đó (T13, T14), nên không trừ hai lần. Shape tự từ chối (quote bằng 0, thiếu order) thì không ghi `policy_denied`; chỉ host ghi.

**Trace.** Mọi nhánh return, kể cả `needs_info` và `escalated`, đều ghi trace đúng contract v1 (`run_id` khớp, `events` là list) qua `lab8.trace.Trace`. Event chính: `order_lookup` (chỉ `visible` và `reason`), `quote`, `decision`, `crash`; `single` thêm `observations` và `react`; `orchestrator` thêm `handoff` đã sanitize và `investigator`. Trace không ghi nội dung ticket, SĐT, địa chỉ, tên hàng, ghi chú nội bộ hay `parent_secret`. Tự kiểm trên `student_drop/` cho kết quả 0 `leak_suspect` ở cả ba shape.

## 4. Kết quả

Bảng so sánh 4 shape trên bộ public (từ `src/reports/benchmark.json`): pass rate, pass^5, seed min–max, variance, cost/success, mean/p95 steps. Kèm crash safety (`src/reports/crash.json`) và, nếu có, kết quả tự kiểm trên `student_drop/`.

Bộ public: 14 claim × 5 seed (`11,22,33,44,55`) = 70 trial mỗi shape, cùng MockLLM, tool, giá và evaluator. Nguồn: `src/reports/benchmark.json` (commit `8465072`).

| Shape | Pass rate | Pass^5 | Seed min–max | Variance | Cost/success (VND mô phỏng) | Mean steps | p95 steps |
| --- | --- | --- | --- | --- | --- | --- | --- |
| workflow | 1.000 | 1.000 | 1.000–1.000 | 0.000000 | 27.86 | 2.79 | 3 |
| single | 1.000 | 1.000 | 1.000–1.000 | 0.000000 | 39.29 | 3.71 | 4 |
| orchestrator | 1.000 | 1.000 | 1.000–1.000 | 0.000000 | 47.23 | 2.79 | 3 |
| swarm (đối chứng) | 0.986 | 0.929 | 0.929–1.000 | 0.000816 | 49.57 | 2.80 | 3 |

Swarm fail đúng một trial (`R-swarm-C-002-s55`): ở seed 55 nó tin số ngày trong ticket thay vì `delay_days` (T02). Ba shape của nhóm đạt 70/70. Giá là mô phỏng, không phải hóa đơn API; latency là `unavailable`.

- **Crash safety:** `src/reports/crash.json` cho `crash_safety` = 20/20. File này đo trên kịch bản của swarm; với ba shape của nhóm, bằng chứng là test T11 (gọi lại), T12 (crash rồi resume) trong ma trận student và `tests/test_ledger_shapes.py` (TC13–TC20, 30 lượt chạy, đều xanh).
- **Test:** cổng host `python -m pytest -q`: 105 passed; ma trận student `python -m pytest -q -m student -o addopts=`: 255 passed.
- **Tự kiểm trên `student_drop/` (40 claim × 5 seed, không nhãn):** workflow, single, orchestrator mỗi shape 200 trial, 0 trial `error`, 0 `leak_suspect`. Không có pass rate vì không có nhãn; kết quả chính thức do giảng viên chấm.

Quyết định kiến trúc và lý do: xem `report/team/decision_adr.md`. Phiếu nghiên cứu và ablation: xem `report/team/research_card.md`.

## 5. Khó khăn và cách xử lý

Lỗi gặp phải (kèm lệnh, output hoặc ảnh chụp) và cách nhóm xử lý.

Các điểm dưới đây gom từ báo cáo cá nhân của từng thành viên và từ kết quả chạy test.

**1. Trừ tiền hai lần ở T14 (đã hoàn 30.000, quyền lợi mới 150.000).** Nếu shape tự trừ phần đã hoàn rồi mới gọi `issue_refund`, host trừ thêm lần nữa nên số tiền sai. Nhóm xử lý bằng cách mọi shape truyền **quote đầy đủ** vào `durability.issue_refund` và để host đối soát trần theo đơn. Kiểm chứng: `test_t13`, `test_t14` trong ma trận student và `tests/test_ledger_shapes.py::test_tc17` (ghi 120.000, `proposal_amount` giữ 150.000). (Toàn, Quý Anh)

**2. `InjectedCrash` bị nuốt bởi `except Exception` (T12).** Một `try/except` quá rộng làm crash không kích hoạt, nên T12 báo "crash did not fire". Nhóm xử lý bằng cách chỉ bắt `InjectedCrash` để ghi trace (`trace.write()`) rồi `raise`, và truyền `crash_at` xuống `issue_refund` ở cả ba shape. Lần chạy `pytest -m student -k single` khi `single.py` còn là stub cho 62 failed và đúng thông báo trên. Kiểm chứng: sau khi `single` được hoàn thiện ma trận student ra 255 passed; `tests/test_ledger_shapes.py::test_tc19` kiểm ba điểm crash; khi cố ý bỏ `crash_at` trong `workflow.py` thì ba test TC19 của workflow đỏ. (Toàn, Quý Anh, Ninh)

**3. Trace không được lộ dữ liệu nhạy cảm.** Grader quét thư mục `traces/` tìm `CANARY_SECRET_*`, SĐT, địa chỉ, ghi chú nội bộ. Nhóm xử lý bằng cách chỉ đọc dữ liệu qua `get_claim_view` và `lookup_order` (allowlist), không serialize dòng claim hay order thô; orchestrator chỉ ghi handoff đã sanitize. Kiểm chứng: `test_single_trace_has_no_raw_secret_or_pii`, `test_orchestrator_resolves_cleanly_without_secret_leak`, và tự kiểm `student_drop/` cho 0 `leak_suspect`. (Toàn, Tùng, Quý Anh)

**4. Trạng thái của vòng ReAct (`single`).** `run_react` chỉ truyền kết quả tool gần nhất cho `decide()`, nên `decide()` không biết các bước trước. Nhóm xử lý bằng cách giữ trạng thái trong closure của `decide()` và đặt thứ tự tool cố định. (Quý Anh)

**5. Xung đột khi gộp `TEAM.md`.** Nhiều thành viên cùng sửa `TEAM.md` nên bị conflict khi merge; Quý Anh gộp lại và giữ đúng tiêu đề `## Bảng đóng góp` để `check_submission` đọc được. (Quý Anh)

**6. `crash.json` chỉ đo swarm.** Crash suite 20 điểm của repo chạy trên kịch bản swarm, nên không chứng minh trực tiếp độ an toàn của ba shape nhóm viết. Nhóm bổ sung bằng chứng bằng T11, T12 và `tests/test_ledger_shapes.py` (TC13–TC20, 30 lượt chạy). (Ninh)

## 6. Tổng hợp đóng góp

Chi tiết đóng góp của từng thành viên nằm trong `TEAM.md` (bảng đóng góp) và báo cáo cá nhân `report/team/MSSV_HoTen.md`.

## 7. Hạn chế và hướng cải thiện

MockLLM không phải model sản xuất; latency là `unavailable`. Nêu thêm giới hạn của nhóm và điều kiện làm kết luận thay đổi.

**Giới hạn của kết quả**

- **MockLLM, không phải model sản xuất.** `workflow` không gọi model nên kết quả của nó không nói gì về chất lượng model thật; với `single` và `orchestrator`, "model" là hàm quyết định cố định theo seed. Cost là giá mô phỏng, không phải hóa đơn API; latency là `unavailable`.
- **Bộ public nhỏ.** 14 claim × 5 seed = 70 trial mỗi shape, và ba shape của nhóm cùng đạt 1.000, nên chênh lệch giữa chúng chủ yếu là cost và số bước, chưa chứng minh được khác biệt về độ đúng. Kết luận chọn `workflow` dựa trên cost thấp nhất khi chất lượng ngang nhau.
- **Chưa có pass rate hidden.** Tự kiểm trên `student_drop/` (40 claim × 5 seed, không nhãn) chỉ cho biết không có trial `error` và không có `leak_suspect`; nhóm không biết các nhóm khó (injection, homoglyph, approval mượn của claim khác, đơn hoàn trùng) được xử lý đúng bao nhiêu. Điểm hidden do giảng viên chấm.
- **Bằng chứng crash.** `crash.json` (20/20) đo kịch bản của swarm. Với ba shape của nhóm, bằng chứng là T11, T12 và `tests/test_ledger_shapes.py` (TC13–TC20), chưa có crash suite 20 điểm chạy trực tiếp trên từng shape.
- **Test ledger mới chỉ chạy trên ba shape của nhóm**, chưa chạy trên swarm.

**Điều kiện làm quyết định thay đổi**

- Nếu bộ hidden cho `workflow` pass rate dưới ngưỡng 0.75 ở các nhóm claim cần đọc ticket nhiều bước mà luật cứng không phủ, nhóm sẽ xem lại `single` hoặc `orchestrator`.
- Nếu nghiệp vụ có policy đổi thường xuyên, chi phí cập nhật luật cố định của `workflow` có thể vượt chi phí dùng agent.
- Nếu một shape khác có pass rate hidden cao hơn đủ lớn để bù cost và variance cao hơn, quyết định đảo lại.

**Hướng cải thiện**

- Mở rộng bộ claim, đặc biệt các nhóm lỗi trong hidden, và thêm test cho TC01–TC12 và TC21–TC26 ở cấp shape.
- Chạy crash suite 20 điểm trực tiếp trên từng shape của nhóm.
- Bổ sung kiểm tra tự động rằng trace không chứa chuỗi cấm cho cả ba shape, không chỉ dựa vào cờ `leak_suspect`.

## 8. Tài liệu tham khảo

- Cemri, M., Pan, M. Z., Yang, S. và cộng sự. *Why Do Multi-Agent LLM Systems Fail?* arXiv:2503.13657, 2025 (NeurIPS 2025 Datasets and Benchmarks). https://arxiv.org/abs/2503.13657
- `docs/business_rules.md`, `docs/contracts.md`, `docs/metrics.md`, `docs/architecture.md` trong repo của lab.
- Mã nguồn starter của lab: `src/lab8/` (host, MockLLM, `swarm_reference.py`), bộ public `src/data/public_claims.jsonl`.
