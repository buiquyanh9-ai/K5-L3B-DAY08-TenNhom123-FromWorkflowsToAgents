# Báo cáo cá nhân — Vai 3: Orchestrator + Handoff

> *Lưu ý: Đổi tên file này thành `MSSV_HoTen.md` (Ví dụ: `20241234_NguyenVanAn.md`) và cập nhật thông tin cá nhân của bạn.*

## 1. Thông tin thành viên

- Họ tên: [Điền họ và tên của bạn]
- MSSV: [Điền MSSV của bạn]
- Email: [Điền email của bạn]
- GitHub: [Điền GitHub username của bạn]

## 2. Phần việc phụ trách

- **Vai trò:** Vai 3 — Orchestrator + Handoff (Chuyên viên Điều phối Đa tác tử & Ranh giới Bảo mật).
- **Mã nguồn chịu trách nhiệm:**
  - `src/lab8/shapes/orchestrator.py`: Hiện thực hóa toàn bộ Shape C (Orchestrator điều phối các read-only investigators).
  - `src/tests/test_orchestrator_custom.py`: Viết bộ unit test kiểm thử ranh giới Handoff, tính bảo mật không rò rỉ secret/PII, và các nhánh xử lý nghiệp vụ.
- **Phối hợp nhóm:**
  - Phối hợp cùng Vai 1 (Integration) để đảm bảo shape Orchestrator tuân thủ đúng Output Contract v1 và Trace Contract v1.
  - Phối hợp cùng Vai 4 (Ledger & Eval) để chạy kiểm thử crash và benchmark so sánh hiệu năng.

## 3. Đóng góp cụ thể

1. **Hiện thực hóa Shape C (`src/lab8/shapes/orchestrator.py`):**
   - Thiết kế luồng xử lý phân tách rõ ràng quyền hạn: Orchestrator là bên duy nhất quyết định và gọi `durability.issue_refund`, các Investigators chỉ được cấp quyền đọc.
   - Xây dựng gói Handoff thông qua `lab8.handoff.make_handoff` với allowlist nghiêm ngặt (`ALLOWED_FIELDS` và `FACT_KEYS`).
   - Sử dụng `lab8.runtime.run_readonly_investigators` để thực thi các tool chỉ đọc: `lookup_order`, `lookup_policy`, `compute_compensation`.
   - Bảo đảm ranh giới an toàn: Forward `crash_at` vào host gate, không bắt nuốt `InjectedCrash` để hệ thống kiểm thử crash hoạt động chính xác.
   - Hoàn tất mọi kết quả trả về bằng `lab8.shapes.common.finish()`.
2. **Xây dựng bộ kiểm thử cá nhân (`src/tests/test_orchestrator_custom.py`):**
   - `test_handoff_rejects_write_tools_explicitly`: Kiểm tra Handoff từ chối cấp write tools (`issue_refund`).
   - `test_handoff_sanitization_removes_unallowed_keys`: Kiểm tra việc tự động loại bỏ các trường không được phép (parent_secret, PII).
   - `test_orchestrator_resolves_cleanly_without_secret_leak`: Kiểm tra claim hợp lệ (C-001) được duyệt hoàn tiền 35.000đ và Trace không chứa bất kỳ chuỗi `CANARY_SECRET_` nào.
   - `test_orchestrator_handles_missing_order_id`: Kiểm tra claim thiếu `order_id` (C-004) trả về `needs_info`.
   - `test_orchestrator_escalates_on_principal_mismatch`: Kiểm tra claim sai chủ sở hữu (C-005) trả về `escalated`.

## 4. Bằng chứng

- **Mã nguồn Shape Orchestrator:** [`src/lab8/shapes/orchestrator.py`](../src/lab8/shapes/orchestrator.py)
- **File Test đóng góp:** [`src/tests/test_orchestrator_custom.py`](../src/tests/test_orchestrator_custom.py) (5/5 tests passed).
- **Kết quả kiểm thử sinh viên (Ma trận Student):**
  - Lệnh: `python -m pytest -q -m student -o addopts= -k orchestrator`
  - Kết quả: **62/62 passed** trên 12 cases public × 5 seeds cùng T11 (retry) và T12 (crash resume).
- **Kết quả kiểm tra format nộp bài:**
  - Lệnh: `python -m lab8.check_submission`
  - Kết quả: `[ OK ] shape orchestrator: format đúng, 12/12 claim public pass ở seed 11`.

## 5. Công cụ AI đã dùng

- **Công cụ:** Antigravity AI Assistant.
- **Mục đích sử dụng:**
  - Hỗ trợ phân tích mã nguồn starter kit và giải thích cơ chế Handoff allowlist.
  - Hỗ trợ xây dựng khung test suite `test_orchestrator_custom.py`.
- **Tự kiểm tra & Đảm bảo liêm chính:**
  - Tự rà soát toàn bộ logic kiểm tra quyền `principal_id` và tính toàn vẹn của Trace.
  - Kiểm tra trực tiếp bằng pytest và đối chiếu với `docs/contracts.md` và `docs/business_rules.md`.

## 6. Tự đánh giá

- Hoàn thành 100% nhiệm vụ của Vai 3: Orchestrator + Handoff.
- Đảm bảo đầy đủ 3 điều kiện must-pass cho shape Orchestrator (không approval bypass, không rò rỉ canary secret, an toàn khi crash).
- Mức độ đóng góp: Đạt yêu cầu cao nhất cho thành viên phụ trách kiến trúc đa tác tử có điều phối.
