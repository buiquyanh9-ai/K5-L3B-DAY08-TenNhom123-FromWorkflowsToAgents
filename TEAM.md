# Team

## Thông tin nhóm

- Tên nhóm: TenNhom123
- Lớp: L3B
- Repo nhóm: `K5-L3B-DAY08-TenNhom123-FromWorkflowsToAgents` (xem [SUBMISSION.md](SUBMISSION.md))
- URL repo, nhánh nộp, commit chốt: https://github.com/buiquyanh9-ai/K5-L3B-DAY08-TenNhom123-FromWorkflowsToAgents, nhánh `main`, commit chốt: `8465072`

## Thành viên

| STT | Họ tên | MSSV | Email | GitHub | Vai trò |
| --: | ------ | ---- | ----- | ------ | ------- |
|   1 | Lê Quý Toàn | 2A202603941 | lequytoanptit0303@gmail.com | ToanLee5433 | workflow + integration |
|   2 | Nguyễn Thanh Tùng | 2A202603957 | thtung13102004@gmail.com | wewewewe07 | orchestrator + handoff |
|   3 | Bùi Đình Quý Anh | 2A202603969 | buiquyanh9@gmail.com | buiquyanh9-ai | single agent |
|   4 | Trịnh Ngọc Ninh | 2A202603996 | ninh.trinh.dev@gmail.com | ninhtrinhdev | ledger + evaluation |

Gợi ý chia vai:

- Nhóm 6 người: integration; workflow; single agent; orchestrator; ledger/policy/crash; eval/report.
- Nhóm 4 người: workflow + integration; single; orchestrator + handoff; ledger + evaluation.

## Bảng đóng góp

`python -m lab8.check_submission` đọc bảng này bằng máy: giữ nguyên tiêu đề `## Bảng đóng góp` và các cột. Mỗi người một dòng: commit có nội dung và ít nhất một test đã thêm hoặc sửa.

| Người | Vai | Commit | Test đã thêm hoặc sửa |
| --- | --- | --- | --- |
| Lê Quý Toàn | workflow + integration | c439bdc | tests/test_workflow_shape.py, tests/test_public_matrix.py (workflow: single-run 60/60, T11 retry, T12 crash) |
| Nguyễn Thanh Tùng | orchestrator + handoff | 32b2417 | tests/test_orchestrator_custom.py, tests/test_public_matrix.py (orchestrator: single-run 60/60, T11 retry, T12 crash) |
| Bùi Đình Quý Anh | single agent | f93d2ae | tests/test_single_shape.py, tests/test_public_matrix.py (single: single-run 60/60, T11 retry, T12 crash) |
| Trịnh Ngọc Ninh | ledger + evaluation | 8465072 | tests/test_ledger_shapes.py (TC13–TC20: approval và ledger qua run_claim của 3 shape, 30 lượt chạy) |

## Cá nhân

Mỗi thành viên đồng thời tạo một báo cáo riêng trong `report/` theo dạng:

```text
report/team/MSSV_HoTen.md
```

Ví dụ: `report/team/2A202603941_LeQuyToan.md`.

Sao chép mục dưới đây cho từng thành viên.

## 2A202603941_LeQuyToan

### Phần việc phụ trách

- Workflow Shape (`src/lab8/shapes/workflow.py`).
- Cấu hình môi trường và kiểm thử tích hợp (Integration testing).

### Đóng góp cụ thể

- Hiện thực hóa pipeline bồi thường tất định `run_claim` cho workflow tuân thủ nguyên tắc Money stays in code.
- Kết nối cổng thanh toán an toàn `durability.issue_refund`, truyền full quote theo chuẩn T13, T14, bắt và ném lại `InjectedCrash` để phục vụ cơ chế khôi phục lỗi.
- Đảm bảo tuân thủ Trace Contract v1, kiểm soát dữ liệu truy cập qua allowlist tránh rò rỉ PII.
- Bổ sung bộ test tích hợp `src/tests/test_workflow_shape.py` gồm 16 test cases kiểm thử tính tất định, độ biến thiên zero-variance, tính bền vững khi crash và cơ chế chống ghi trùng (idempotency).
- Xác minh và vượt qua 62/62 student tests cho shape workflow trong ma trận bài tập.
- Chạy thử nghiệm và xác nhận suite `crash_test` đạt 20/20 safe points.

### Bằng chứng

- Báo cáo chi tiết: `report/team/2A202603941_LeQuyToan.md`.
- Kết quả test:
  + `tests/test_workflow_shape.py`: 16/16 passed.
  + `tests/test_public_matrix.py -k workflow`: 62/62 passed.
  + `pytest -q`: 75/75 passed.
  + `reports/crash.json`: 20/20 safe points.
  + `lab8.check_submission`: shape workflow định dạng chuẩn và pass 12/12 claims ở seed 11.

## 2A202603957_NguyenThanhTung

### Phần việc phụ trách

- Shape C: `src/lab8/shapes/orchestrator.py` (Orchestrator điều phối các read-only investigators).
- Bảo đảm ranh giới bảo mật qua Handoff allowlist (`make_handoff`).
- Viết test suite `src/tests/test_orchestrator_custom.py`.

### Đóng góp cụ thể

- Hiện thực hóa toàn bộ logic Shape C: phân quyền Orchestrator duy nhất gọi `issue_refund`, investigators chỉ đọc.
- Chặn write tools và lọc bỏ bí mật / PII khỏi Handoff facts và Trace.
- Forward `crash_at` và đảm bảo an toàn khi crash (Crash safety).
- Thêm 5 unit tests kiểm thử độc lập cho Orchestrator và Handoff.

### Bằng chứng

- Code: `src/lab8/shapes/orchestrator.py`.
- Tests: `src/tests/test_orchestrator_custom.py` (5/5 passed).
- Ma trận student: `python -m pytest -q -m student -o addopts= -k orchestrator` đạt 62/62 passed.
- Báo cáo cá nhân chi tiết: `report/team/2A202603957_NguyenThanhTung.md`.

## 2A202603969_BuiDinhQuyAnh

### Phần việc phụ trách

- Shape B: `src/lab8/shapes/single.py` (một agent ReAct, tối đa 8 bước, chỉ dùng tool đọc).
- Người fork và quản lý repo nhóm.

### Đóng góp cụ thể

- Hiện thực shape single bằng `run_react`: model chỉ chọn tool đọc, số tiền lấy từ order row qua `compute_compensation`, không tin số liệu trong ticket.
- Code của shape (không phải model) gọi `durability.issue_refund` với quote đầy đủ, forward `crash_at`, không bắt `InjectedCrash`.
- Thêm `src/tests/test_single_shape.py`: bỏ qua delay ghi trong ticket ở cả 5 seed (C-002), trace không lộ secret/PII (C-010), giữ trong step cap (C-014).

### Bằng chứng

- Code: `src/lab8/shapes/single.py`.
- Tests: `src/tests/test_single_shape.py` (7/7 passed).
- Ma trận student: `python -m pytest -q -m student -o addopts= -k single` đạt 62/62 passed cho shape single.
- Báo cáo cá nhân chi tiết: `report/team/2A202603969_BuiDinhQuyAnh.md`.

