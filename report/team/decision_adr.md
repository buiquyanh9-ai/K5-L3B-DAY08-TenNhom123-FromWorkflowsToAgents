# Decision record

Điền sau dấu `:` trên cùng dòng, không xóa nhãn. Giảng viên và `python -m lab8.check_submission` (chạy trong `src/`) đọc các dòng này bằng máy. Không đổi tên hay dời file này khỏi `report/team/`.
`Shape chọn` phải là đúng một trong: `workflow`, `single`, `orchestrator`, `swarm`. Đây là shape được chấm cổng hidden.

- Shape chọn: workflow
- Commit hash: 8465072
- Run id dẫn chứng: R-workflow-C-001-s11 (benchmark public 4 shape x 14 claim x seed 11,22,33,44,55; `src/reports/benchmark.json`)
- Pass rate / pass^5 / seed min-max / variance: 1.000 / 1.000 / 1.000-1.000 / 0.000000
- Cost per success (mô phỏng, VND): 27.86
- Crash safety: 20/20 (src/reports/crash.json, đo trên swarm); với workflow, T11 (gọi lại) và T12 (crash rồi resume) xanh trong `pytest -q -m student -o addopts= -k workflow`
- Secret leak / approval bypass: 0 / 0 (0 `leak_suspect_trials` trên `student_drop/` 40 claim x 5 seed; mọi trial public pass, không có refund thiếu approval)

Ví dụ một dòng đã điền: `- Shape chọn: workflow`, `- Crash safety: 20/20 (src/reports/crash.json)`.

## Vì sao shape này

Nhóm chọn `workflow` (shape A). Trên cùng 14 claim public và cùng 5 seed, `workflow`, `single` và `orchestrator` đều đạt pass rate 1.000 và pass^5 1.000, variance 0; chỉ `swarm` thấp hơn (0.986, pass^5 0.929) vì tin số ngày trong ticket ở seed 55 (T02). Khi chất lượng ngang nhau, `workflow` rẻ nhất: cost/success 27.86 VND mô phỏng, so với `single` 39.29, `orchestrator` 47.23, `swarm` 49.57. Số bước trung bình 2.79, không có lời gọi model nào (`mean_model_calls` = 0). Số tiền do `compute_compensation` tính và `durability.issue_refund` ghi, nên không có chỗ nào để model quyết định tiền. Đây là kiến trúc ít tự chủ nhất mà vẫn làm được việc.

## Có đáng đổi lấy multi-agent không

Trên dữ liệu hiện có thì không: `orchestrator` không nhỉnh hơn về pass rate nhưng đắt hơn khoảng 1.7 lần, và `swarm` vừa đắt nhất vừa có variance khác 0. Nhóm sẽ xem lại quyết định nếu: (1) bộ hidden cho thấy `workflow` dưới ngưỡng 0.75 ở nhóm claim cần đọc ticket nhiều bước mà luật cứng không phủ; (2) có nghiệp vụ mới với policy thay đổi thường xuyên, khi đó việc cập nhật luật cố định tốn hơn dùng agent; (3) một shape khác có pass rate hidden cao hơn đủ lớn để bù phần cost và variance. Hiện chưa có bằng chứng nào trong ba điều này.

## Trace và bằng chứng

`workflow` ghi các event: `error` (claim không tồn tại), `order_lookup` (chỉ `visible` và `reason`), `quote` (`amount_vnd`, `reason`, `clause_ids`, `parts`), `decision` (status, reason) và `crash` (điểm crash). Cố ý **không** ghi: dòng claim thô, dòng order thô, nội dung ticket, SĐT, địa chỉ, tên hàng, ghi chú nội bộ và `parent_secret`, vì đây là các chuỗi cấm trong `docs/metrics.md`. Với `orchestrator`, trace chỉ ghi handoff đã qua `make_handoff` (allowlist), không ghi parent context. Bằng chứng không lộ secret: chạy `student_drop/` cho cả ba shape, `leak_suspect_trials` = 0 (200 trial mỗi shape), và `traces/` không chứa chuỗi `CANARY_SECRET`. Lưu ý: đây là tự kiểm không có nhãn; kết luận chính thức do grader của giảng viên.

## Giới hạn

MockLLM không phải model sản xuất; `workflow` không gọi model nên kết quả không nói gì về chất lượng model thật. Latency để `unavailable`. Bộ public chỉ 14 claim và ba shape cùng đạt 1.000, nên chênh lệch giữa chúng chủ yếu là về cost, chưa chứng minh được khác biệt về độ đúng. `crash.json` đo trên swarm; với ba shape của nhóm, bằng chứng crash là test T11 và T12. Số cost là mô phỏng, không phải hóa đơn API. Không sửa JSON cho đủ 0.75.
