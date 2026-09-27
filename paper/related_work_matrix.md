# Ma trận định vị nghiên cứu — bản E1

**Cập nhật ngày 27 tháng 09 năm 2026 — R1 mở lại.** Ma trận này là artifact
cho cổng R1; nó không phải systematic literature review hoàn chỉnh. Mỗi claim
trong manuscript phải được cập nhật sau khi R1 hoàn tất.

## Kết luận định vị tạm thời

Một hệ thống chặn tool call theo policy ở execution boundary **không còn là đóng góp mới đủ mạnh**. CaMeL, Fides, Progent, AgentArmor, ClawGuard và ActGov đều đã nghiên cứu system-level hoặc runtime enforcement cho LLM Agent. Vì vậy prototype trong repository chỉ đóng vai trò reference monitor và T1 component harness.

Trước khi chạy E2–E5, nhóm phải chốt một contribution hẹp có thể bị bác bỏ, ví dụ:

1. security-regression evaluation của IPI defenses khi tool contract thay đổi qua phiên bản;
2. benchmark/case study theo ngữ cảnh SOC/OT, với trust boundary, action oracle và trade-off vận hành khác biệt rõ;
3. một replication/negative result được định vị trung thực nếu không còn gap đủ hẹp.

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

## Closest-prior additions for the 2026 freeze

These rows were added after checking the full 2026 MCP-PEP paper and the
newer runtime-policy/authorization papers. They narrow the novelty claim; they
do not establish that the proposed work is "first".

| Work | What it already covers | What remains a defensible extension here |
|---|---|---|
| Wang, Zhu & Li, *Runtime Policy Enforcement for MCP-Based LLM Agents* (`wang2026mcp_runtime_policy`) | MCP PEP; path/sensitive-data/high-risk/rate rules; cross-step labels; tamper-evident audit; DeepSeek 1050-run primary study; four-backend observation; local stdio MCP test. | Measure post-adapter semantic fidelity and check-to-execution/TOCTOU containment with state-diff or adapter attestation. The paper explicitly leaves full adapter-level calibration and residual check-to-execution races as future work. |
| Wang, Poskitt & Sun, *AgentSpec* (`agentspec2026`) | Declarative runtime-enforcement DSL with ALLOW/DENY/CONFIRM semantics and configurable safety constraints. | Treat approval workload and post-effect semantic fidelity as measured endpoints; do not claim a new enforcement DSL. |
| Fan et al., *PACT* (`pact2026`) | Argument-level provenance/capability contracts; AgentDojo evaluation across five models. | Separate pre-dispatch provenance correctness from post-adapter effect equivalence; compare against PACT only if an executable baseline is available. |
| Zhang et al., *ActGov* (`zhang2026actgov`) | Task-scoped action validation and policy construction/verification on AgentDojo/AgentDyn. | Test interface evolution and adapter-induced semantic remapping, not generic task-scoped validation. |
| Zhang et al., *RAC* (`rac2026`) | Workflow-level authorization lineage/drift consistency, including LLM-generated workflows. | Evaluate effect-level semantic fidelity at the tool-adapter boundary; avoid claiming workflow authorization drift as new. |
| Wu & Gong, *Policy-Invisible Violations* (`phantom_policy2026`) | Hidden world-state/policy context and Sentinel-style enforcement. | Use hidden-state cases as an external stress condition only; do not claim the policy-invisible failure class as new. |
| Liao et al., *TraceGrant* (`tracegrant2026`) | Contract-governed task-effect lifecycle with pre-execution boundaries and post-execution task verification; 949 AgentDojo and 400 ASB attack cases. | Do not claim runtime contracts or generic post-effect verification as new; isolate adapter/schema semantic fidelity and report it as a measurement extension. |
| Lin et al., *VIGIL* (`lin2026vigil`) | Verify-before-commit defense against tool-stream injection and SIREN benchmark with 959 cases. | Do not claim verify-before-commit or tool-stream IPI evaluation as new; test paired contract-version regression instead. |
| Santos-Grueiro, *CXI* (`santosgrueiro2026cxi`) | Field, effect and invocation authority bound to one action manifest; reports live AgentDojo episodes. | Do not claim exact-effect authorization; score whether an existing defense regresses after a contract migration. |
| Zheng & Yang, *CONTINUITY* (`zheng2026continuity`) | Transformation witnesses, policy evolution and effect-bound permits across component transitions. | Do not claim transformation integrity; any extension must be a real-agent IPI evaluation, not another witness mechanism. |
| Assidiqi et al. (`assidiqi2026drift`) | Schema, policy and toolset drift with end-state task success. | Do not rebrand generic drift adaptation; require IPI and harmful-effect security regression in the candidate protocol. |

### R1 decision on 27 September 2026

**Do not freeze Pivot A.** Semantic mediation fidelity under adapter/schema
drift is retained only as a component stress/measurement artifact because
VIGIL, CXI, CONTINUITY and Assidiqi et al. materially narrow its novelty. The
working candidate is a paired security-regression evaluation of IPI defenses
under versioned tool contracts; it remains unclaimed until the literature-audit
stop gate in `paper/r1_reopening_20260927.md` passes. Approval-event burden may
remain a secondary outcome, not a replacement novelty claim.

## R1 checklist trước khi khóa claim

- [ ] Mỗi claim contribution có dòng “closest prior work”, điểm khác biệt và cách đo.
- [ ] Có ít nhất một baseline công bằng hoặc lý do tái lập không khả thi được ghi rõ.
- [ ] Candidate contribution có failure criterion; nếu test không đạt, paper báo trade-off/kết quả âm thay vì đổi claim hậu nghiệm.
- [ ] Không có câu nào dùng “novel/first” nếu không có tìm kiếm có hệ thống chứng minh.
- [ ] `references.bib` là nguồn metadata duy nhất; manuscript không duy trì danh sách tác giả độc lập dễ lệch.
