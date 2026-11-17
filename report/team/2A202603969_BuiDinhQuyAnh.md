# Báo cáo cá nhân — 2A202603969_BuiDinhQuyAnh

## 1. Thông tin thành viên

- Họ tên: Bùi Đình Quý Anh
- MSSV: 2A202603969
- Email: buiquyanh9@gmail.com
- GitHub: buiquyanh9-ai

## 2. Phần việc phụ trách

Shape B — `single` (một agent ReAct): `src/lab8/shapes/single.py` và test riêng `src/tests/test_single_shape.py`. Đồng thời là người fork và quản lý repo nhóm.

## 3. Đóng góp cụ thể

- Commit chính: `f93d2ae` — feat(single): implement ReAct single-agent shape and add single tests.
- Cài shape single bằng `lab8.runtime.run_react` với `max_steps=8`. `decide()` chỉ chọn tool đọc theo thứ tự `get_claim_view` → `lookup_order` → `lookup_refund_history` → `compute_compensation`, rồi trả về đề xuất.
- Test đã thêm: `src/tests/test_single_shape.py`
  - `test_single_ignores_delay_written_in_ticket` (C-002, 5 seed): ticket khai trễ 5 ngày, DB ghi 2 ngày → single phải `denied` ở mọi seed.
  - `test_single_trace_has_no_raw_secret_or_pii` (C-010): trace không chứa `CANARY_SECRET`, SĐT, địa chỉ, mã nội bộ.
  - `test_single_stays_within_step_cap` (C-014): số tool call ≤ 8.

Quyết định kỹ thuật:

1. **Số tiền chỉ lấy từ order row + `compute_compensation`**, không dùng số ngày trễ hay điều khoản ghi trong ticket. Ticket là dữ liệu người dùng, không phải lệnh.
2. **Model không bao giờ gọi `issue_refund`.** Sau vòng ReAct, code của shape mới gọi `durability.issue_refund` với **quote đầy đủ** (không tự trừ phần đã hoàn), để host tự cap theo đơn (T13, T14).
3. **Truyền `crash_at` vào `issue_refund` và không bắt `InjectedCrash`**: ghi trace rồi ném lại, để T12 và crash suite đo đúng.
4. **State lưu trong closure của `decide()`** vì `run_react` chỉ truyền kết quả tool gần nhất.
5. **Trace chỉ ghi field đã qua allowlist** (order view của `lookup_order`, quote, số đã hoàn), không ghi ticket hay claim row thô.
6. Mọi nhánh return (`failed`, `needs_info`, `escalated`, `denied`, `resolved`) đều đi qua `common.finish()` để trace và `RunResult` đúng contract.

## 4. Bằng chứng

- Ma trận student của single: `python -m pytest -q -m student -o addopts= -k "single and not workflow and not orchestrator and not swarm"` → **62 passed**.
- Test riêng: `python -m pytest -q -m student -o addopts= tests/test_single_shape.py` → **7 passed**.
- Cổng host: `python -m pytest -q` → **54 passed**, không có `failed`.
- Ví dụ run id: `R-single-C-001-s11` → `resolved`, `proposal_amount` 35000, 6 model call, 4 tool call.
- Benchmark thử single vs swarm (bộ public, 14 claim × seed 11,22,33,44,55; số chính thức ở `src/reports/benchmark.json` của nhóm):

| Shape | pass rate | pass^5 | seed variance | cost/success (VND giả lập) | mean steps |
| --- | ---: | ---: | ---: | ---: | ---: |
| single | 1.000 | 1.000 | 0.0 | 39.29 | 3.71 |
| swarm | 0.986 | 0.929 | 0.0008 | 49.57 | 2.80 |

Swarm fail đúng 1 trial (C-002, seed 55) vì tin số ngày trễ trong ticket; single không bị lỗi này. Cost là giả lập từ MockLLM, không phải hóa đơn API.

## 5. Công cụ AI đã dùng

- Công cụ: Claude.
- Dùng vào việc: Chủ yếu là đọc đề và giải thích; gợi ý và hỗ trợ viết code `single.py` theo docstring và `swarm_reference.py`; viết khung test `test_single_shape.py`; giải thích tiêu chí chấm `trial_pass`.
- Cách tự kiểm tra: tự chạy ma trận student (62 passed), test riêng (7 passed), cổng host (xanh); chạy tay `python -m lab8.run --shape single` cho các claim C-001…C-014 và đối chiếu với `expected` trong `data/public_claims.jsonl`; mở file trace trong `src/traces/` để kiểm tra không có secret/PII; thử crash C-012 rồi chạy lại để thấy vẫn chỉ một refund.
- Số liệu benchmark lấy từ output thật của `lab8.benchmark`, không do AI tự đặt ra.

## 6. Tự đánh giá

Gợi ý: mức độ hiểu ReAct / idempotency / trần theo đơn, phần nào làm tốt, phần nào còn dựa vào AI, nếu làm lại sẽ làm gì khác

...
