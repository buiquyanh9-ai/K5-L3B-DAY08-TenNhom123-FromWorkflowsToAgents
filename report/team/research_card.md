# Research card

File này nằm cố định ở `report/team/research_card.md`; `python -m lab8.check_submission` đọc cột "Nhóm điền" bằng máy.

Phần này nối tiếp phần mini research ở buổi lý thuyết (slide 62–63). Chọn **một** câu R1–R4, điền 6 dòng, rồi biến nó thành **một ablation** chạy được trong lab: giữ nguyên model (MockLLM), tool, seed, corpus và giá, chỉ thay đổi một biến.

| Câu | Nguồn (thư viện tham khảo, slide 68–69) | Câu hỏi gợi ý cho lab |
| --- | --- | --- |
| R1 · Scaling | Google Research 2026, *Towards a Science of Scaling Agent Systems* | Task claims chủ yếu tuần tự hay song song được? Dự đoán thêm investigator sẽ làm pass rate và cost/success thay đổi thế nào. |
| R2 · Failure taxonomy | MAST, NeurIPS 2025, *Why Do Multi-Agent LLM Systems Fail?* | Các trial fail của swarm (seed 55) thuộc nhóm nào: lỗi giao việc, lệch mục tiêu, hay lỗi kiểm chứng? |
| R3 · Architecture choices | AgentArch, AACL 2026 | Nếu đổi topology mà giữ nguyên mọi thứ khác, biến nào phải cố định để kết luận còn đúng? |
| R4 · Evaluation confounders | EMNLP 2026, *Rethinking Evaluation of MAS Efficiency* | Làm sao chứng minh chênh lệch giữa A/B/C/D là do topology, không phải do prompt, tool hay seed? |

## Phiếu của nhóm

Điền vào cột cuối. Không xóa hai cột đầu.

| Field | Hướng dẫn | Nhóm điền |
| --- | --- | --- |
| CÂU | R1 / R2 / R3 / R4 | |
| SOURCE | Paper/blog, năm, URL, loại bằng chứng (benchmark, production report, blog kinh nghiệm) | |
| CLAIM | Một kết luận gốc của nguồn. Không viết rộng hơn phạm vi paper | |
| BOUNDARY | Model / dataset / setup giới hạn kết luận đó | |
| HYPOTHESIS | Nếu đổi shape A→B (hoặc bật/tắt một thành phần), metric X sẽ đổi theo hướng nào, khoảng bao nhiêu | |
| METHOD | Biến giữ cố định: model, tools, seed, corpus, giá, evaluator. Biến duy nhất được thay đổi: … | |
| FAILURE / METRIC | Một lỗi dự kiến và cách đo nó: pass rate, pass^5, variance, cost/success, leak, bypass | |

## Kết quả ablation

- Lệnh đã chạy (copy nguyên văn): `python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json` (chạy trong `src/`)
- Run id / file report: `src/reports/benchmark.json`, commit `8465072`. Trial duy nhất không pass: `R-swarm-C-002-s55` (`status resolved != denied`). Trial đối chứng cùng claim và seed: `R-workflow-C-002-s55`.
- Kết quả so với hypothesis (đúng / sai / không kết luận được), kèm số liệu: [nhóm xác nhận đúng/sai theo dòng HYPOTHESIS]. Số liệu trên 14 claim × 5 seed = 70 trial mỗi shape, cùng MockLLM, tool, seed, corpus, giá và evaluator:
  - swarm: 69/70 trial pass, pass rate 0.986, pass^5 0.929, variance 0.000816, seed 55 chỉ đạt 0.929 (các seed khác 1.000), cost/success 49.57.
  - workflow: 70/70, pass rate 1.000, pass^5 1.000, variance 0, cost/success 27.86.
  - Trial fail duy nhất của swarm là C-002 ở seed 55: status `resolved` trong khi nhãn là `denied` (claim T02, ticket ghi số ngày trễ khác cột `delay_days`).
- Giới hạn: MockLLM không phải model sản xuất, latency là `unavailable`.

Muốn đi xa hơn một ablation để lấy điểm cộng thì xem [docs/bonus_topics.md](../../docs/bonus_topics.md).
