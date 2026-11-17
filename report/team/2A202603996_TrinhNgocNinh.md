# Báo cáo cá nhân — 2A202603996_TrinhNgocNinh

## 1. Thông tin thành viên

- Họ tên: Trịnh Ngọc Ninh
- MSSV: 2A202603996
- Email: ninh.trinh.dev@gmail.com
- GitHub: ninhtrinhdev

## 2. Phần việc phụ trách

Ledger và đánh giá (eval): kiểm tra ba shape `workflow`, `single`, `orchestrator` dùng đúng cổng ghi tiền của host (`durability.issue_refund`), chạy benchmark so sánh bốn shape, và điền quyết định kiến trúc trong `report/team/decision_adr.md`.

## 3. Đóng góp cụ thể

- **Review ledger trên ba shape.** Với từng shape, tôi kiểm các điểm sau trong code:
  - truyền quote đầy đủ vào `issue_refund`, không tự trừ phần đã hoàn trước (T13, T14);
  - truyền `crash_at` vào `issue_refund` và không bắt `InjectedCrash` (ghi trace rồi `raise`);
  - không gọi `issue_refund` khi quote bằng 0;
  - `amount_conflict` được trả về `failed`, từ chối của host trả về `denied`.
  Không thấy lỗi chặn ở `workflow` và `orchestrator`. Khi `single` còn là stub (mọi claim trả `failed`, T12 báo "crash did not fire"), tôi báo cho nhóm; sau khi bản `single` được push tôi chạy lại và kiểm tra tương tự.
- **Chạy các bộ test.** Cổng host `python -m pytest -q`: 75 passed. Ma trận student `python -m pytest -q -m student -o addopts=`: 255 passed, 0 failed. Chạy riêng từng shape với `-k workflow`, `-k orchestrator`, `-k single`.
- **Chạy benchmark public** 4 shape × 14 claim × 5 seed (`11,22,33,44,55`) và commit `src/reports/benchmark.json` (commit `8465072`).
- **Tự kiểm trên `student_drop/`** (claim không nhãn, 40 claim × 5 seed) cho cả ba shape: 0 trial `error`, `leak_suspect_trials` = 0, và thư mục `traces/` không chứa chuỗi `CANARY_SECRET`.
- **Điền `decision_adr.md`:** đề xuất chọn `workflow` vì cùng đạt pass 1.000 và pass^5 1.000 như `single` và `orchestrator`, nhưng rẻ nhất (cost/success 27.86 VND mô phỏng, so với 39.29, 47.23 và 49.57 của swarm).
- **Test đã thêm:** `src/tests/test_ledger_shapes.py`, tám nhóm tình huống TC13 đến TC20 chạy qua `run_claim` của `workflow`, `single`, `orchestrator` (30 lượt chạy, đều xanh):
  - TC13 không có approval, TC14 approval hết hạn, TC15 approval của claim khác: không có dòng ledger, có audit `policy_denied`;
  - TC16 quote 150.000 nhưng approval 100.000: shape báo quote đầy đủ, ledger ghi 100.000;
  - TC17 đã hoàn 30.000, quyền lợi 150.000: ghi 120.000, không trừ hai lần;
  - TC18 gọi lại cùng claim nhiều lần: một dòng ledger, một audit `refund_committed`;
  - TC19 crash ở cả ba điểm (`before_effect`, `after_effect_before_checkpoint`, `after_checkpoint`) rồi resume: đúng một refund;
  - TC20 retry với số tiền khác: giữ số tiền đã commit, shape trả `failed`, có audit `amount_conflict`.
  Tôi thử cố ý bỏ `crash_at` trong `workflow.py`: ba test TC19 của workflow báo đỏ, rồi khôi phục file. Cổng host `pytest -q` sau khi thêm: 105 passed; ma trận student vẫn 255 passed.

## 4. Bằng chứng

- Commit `8465072` (benchmark public). File `src/reports/benchmark.json`, run id dẫn chứng `R-workflow-C-001-s11`.
- Kết quả benchmark public (từ `benchmark.json`):

  | Shape | Pass | Pass^5 | Variance | Cost/success |
  | --- | --- | --- | --- | --- |
  | workflow | 1.000 | 1.000 | 0 | 27.86 |
  | single | 1.000 | 1.000 | 0 | 39.29 |
  | orchestrator | 1.000 | 1.000 | 0 | 47.23 |
  | swarm | 0.986 | 0.929 | 0.000816 | 49.57 |

- `src/reports/crash.json`: `crash_safety` = 20/20. File này đo kịch bản trên swarm; với ba shape của nhóm, bằng chứng là T11 (gọi lại cùng claim) và T12 (crash rồi resume) xanh trong ma trận student.
- `python -m lab8.check_submission`: phần ADR hết FAIL sau khi điền.

## 5. Công cụ AI đã dùng

Tôi dùng Claude Code (trợ lý AI trong terminal) để: đọc và tóm tắt đề, README và docs; đọc code ba shape cùng `durability.py` để đối chiếu với checklist ledger; chạy benchmark và tự kiểm `student_drop/`; và soạn nháp ADR từ số liệu `benchmark.json`.

Cách tôi tự kiểm tra kết quả: tự chạy lại `pytest` (cổng host và ma trận student) trên máy mình, đối chiếu từng con số trong ADR với `src/reports/benchmark.json`, chạy lại `check_submission`, và sửa lại những chỗ nhận định chưa có bằng chứng (ví dụ ghi rõ `crash.json` đo trên swarm chứ không phải ba shape của nhóm).

## 6. Tự đánh giá

- Làm được: cả ba shape qua cổng host và ma trận student; benchmark public có bằng chứng commit; ADR có số liệu đối chiếu được.
- Hạn chế: bộ public chỉ 14 claim và ba shape cùng đạt 1.000, nên chưa phân biệt được độ đúng giữa chúng, chỉ phân biệt được cost. Tự kiểm `student_drop/` không có nhãn nên không cho pass rate; kết quả chính thức do giảng viên chấm. Các test ledger mới chỉ chạy trên `workflow`, `single`, `orchestrator`, chưa chạy trên swarm. `crash.json` chỉ đo swarm.
- Nếu làm lại: viết test idempotency và crash cho cả ba shape ngay từ đầu, và để benchmark chạy trước khi chốt ADR để tránh sửa hash.
