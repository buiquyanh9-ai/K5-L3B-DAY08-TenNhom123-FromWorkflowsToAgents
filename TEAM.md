# Team

## Thông tin nhóm

- Tên nhóm:
- Lớp: L3B
- Repo nhóm: `K5-L3B-DAY08-TenNhom-FromWorkflowsToAgents` (xem [SUBMISSION.md](SUBMISSION.md))
- URL repo, nhánh nộp, commit chốt: `https://github.com/buiquyanh9-ai/K5-L3B-DAY08-TenNhom-FromWorkflowsToAgents`, nhánh `feat/toan-workflow-integration`

## Thành viên

| STT | Họ tên | MSSV | Email | GitHub | Vai trò |
| --: | ------ | ---- | ----- | ------ | ------- |
|   1 | Lê Quý Toàn | 2A202603941 | lequytoanptit0303@gmail.com | ToanLee5433 | workflow + integration |
|   2 |        |      |       |        |         |

Gợi ý chia vai:

- Nhóm 6 người: integration; workflow; single agent; orchestrator; ledger/policy/crash; eval/report.
- Nhóm 4 người: workflow + integration; single; orchestrator + handoff; ledger + evaluation.

## Bảng đóng góp

`python -m lab8.check_submission` đọc bảng này bằng máy: giữ nguyên tiêu đề `## Bảng đóng góp` và các cột. Mỗi người một dòng: commit có nội dung và ít nhất một test đã thêm hoặc sửa.

| Người | Vai | Commit | Test đã thêm hoặc sửa |
| --- | --- | --- | --- |
| Lê Quý Toàn | workflow + integration | 93f5606 | tests/test_workflow_shape.py, tests/test_public_matrix.py (workflow: single-run 60/60, T11 retry, T12 crash) |

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
  + `pytest -q`: 70/70 passed.
  + `reports/crash.json`: 20/20 safe points.
  + `lab8.check_submission`: shape workflow định dạng chuẩn và pass 12/12 claims ở seed 11.
