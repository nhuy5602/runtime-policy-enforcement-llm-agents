# Ma trận định vị nghiên cứu — bản E1

**Cập nhật ngày 26 tháng 09 năm 2026.** Ma trận này là artifact cho cổng R1; nó không phải systematic literature review hoàn chỉnh. Mỗi claim trong manuscript phải được cập nhật sau khi R1 hoàn tất.

## Kết luận định vị tạm thời

Một hệ thống chặn tool call theo policy ở execution boundary **không còn là đóng góp mới đủ mạnh**. CaMeL, Fides, Progent, AgentArmor, ClawGuard và ActGov đều đã nghiên cứu system-level hoặc runtime enforcement cho LLM Agent. Vì vậy prototype trong repository chỉ đóng vai trò reference monitor và T1 component harness.

Trước khi chạy E2–E5, nhóm phải chốt một contribution hẹp có thể bị bác bỏ, ví dụ:

1. đánh giá policy portability khi tool schema, alias API hoặc serialization thay đổi;
2. action canonicalization và detection của policy drift ở tool boundary;
3. benchmark/case study theo ngữ cảnh SOC/OT, với trust boundary, action oracle và trade-off vận hành khác biệt rõ.

Không được tuyên bố “first runtime policy guard”, “first least-privilege defense”, “first approval mechanism” hoặc “first AgentDojo defense”.

## Ma trận công trình gần

| Công trình | Bằng chứng chính | Chồng lấp với hướng ban đầu | Hệ quả đối với bài báo |
|---|---|---|---|
| CaMeL (`debenedetti2025camel`) | Tách control/data flow và capability để hạn chế data exfiltration; được đánh giá trên AgentDojo. | Capability-based protection chống prompt injection. | Không claim capability, least privilege hoặc data/control separation là mới. |
| Fides (`costa2025fides`) | Information-flow control với confidentiality/integrity labels và deterministic enforcement. | System-level defense, policy enforcement, trade-off security–utility. | Không claim provenance/taint hoặc deterministic policy enforcement là mới nếu không có khác biệt thực chứng rõ. |
| Progent (`shi2025progent`) | Programmable privilege policy trên tool call, policy update và evaluation trên agent benchmarks. | Runtime privilege control, policy DSL, approval/ràng buộc action. | Không claim policy DSL, dynamic privilege control hoặc approval là primitive mới. |
| AgentArmor (`wang2025agentarmor`) | Phân tích runtime trace theo CFG/DFG/PDG và type-based policy enforcement. | Runtime trace và fine-grained security constraints. | Cần chứng minh action canonicalization/policy drift khác trace analysis hoặc chọn một scope domain khác. |
| ClawGuard (`zhao2026clawguard`) | Rule do người dùng xác nhận, enforced ở mọi tool-call boundary; đánh giá trên AgentDojo và benchmark injection khác. | Tool-boundary enforcement chống indirect prompt injection, security–utility evaluation. | Không thể dùng “runtime tool guard chống IPI” làm novelty tổng quát. |
| ActGov (`zhang2026actgov`) | Validation từng action với task-scoped policy; policy construction/verification; AgentDojo và AgentDyn. | Task-scoped policy và validation trước side effect. | Cần tránh claim task-scoped action authorization hoặc dynamic workflow validation là chưa có. |
| AgentDojo (`debenedetti2024agentdojo`) | Benchmark động gồm task, security case và defense/attack paradigms. | Benchmark đích cho evaluation. | Phải pin commit/version, model, prompt, policy, split và scorer trước full run. |
| InjecAgent (`zhan2024injecagent`) | Corpus IPI cho tool-integrated Agent. | Nguồn diversity cho attack carrier và exfiltration/direct harm. | Không thay thế utility evaluation; chỉ dùng khi tool/runtime tương thích hoặc công bố adapter. |

## R1 checklist trước khi khóa claim

- [ ] Mỗi claim contribution có dòng “closest prior work”, điểm khác biệt và cách đo.
- [ ] Có ít nhất một baseline công bằng hoặc lý do tái lập không khả thi được ghi rõ.
- [ ] Candidate contribution có failure criterion; nếu test không đạt, paper báo trade-off/kết quả âm thay vì đổi claim hậu nghiệm.
- [ ] Không có câu nào dùng “novel/first” nếu không có tìm kiếm có hệ thống chứng minh.
- [ ] `references.bib` là nguồn metadata duy nhất; manuscript không duy trì danh sách tác giả độc lập dễ lệch.
