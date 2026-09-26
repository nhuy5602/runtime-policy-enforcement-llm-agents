# Q2 Ready Research Roadmap

## Mục tiêu

Xây dựng manuscript và research artifact **submission-ready** cho một venue hoặc tạp chí Scopus Q2 trở lên, với hướng làm việc hiện tại là **Runtime Policy Enforcement for LLM Agents Against Indirect Prompt Injection and Tool Misuse**. Đây là chuẩn chất lượng nội bộ, không phải cam kết được nhận: phân hạng Q2, phạm vi venue và phản biện độc lập đều nằm ngoài quyền kiểm soát của nhóm.

Repository này không lưu báo cáo tuần. Mọi workstream bên dưới chỉ phục vụ manuscript, benchmark và artifact tái lập của bài báo.

## Tiêu chí Q2 ready

Trước khi coi manuscript sẵn sàng gửi phản biện ngoài, dự án phải chứng minh:

1. Khoảng trống và đóng góp khác biệt rõ với CaMeL, Fides, Progent, AgentArmor, ClawGuard, ActGov và các defense liên quan.
2. Threat model, policy semantics, baseline và oracle được định nghĩa trước và không thay đổi theo test case.
3. Kết quả dựa trên LLM Agent và benchmark hoặc sandbox độc lập, không chỉ trên fixture policy tự tạo.
4. Báo cáo đồng thời security, utility, overblocking, approval burden và runtime overhead, kèm số lượng case, khoảng tin cậy và failure analysis.
5. Code, manifest, seed, dependency version, command chạy và artifact kết quả có thể tái lập.
6. Manuscript phân biệt rõ kết quả component với kết quả benchmark; không tuyên bố vượt quá bằng chứng.

## Năm phần thực thi

### E1 Literature and contribution map

**Mục tiêu:** chốt research gap và novelty có thể bảo vệ được.

**Đầu ra**

- Bảng related work gồm CaMeL, Fides, Progent, AgentArmor, ClawGuard, ActGov, AgentDojo, InjecAgent và các công trình gần.
- Decision record về contribution hẹp. “Một runtime policy guard tại tool boundary” chỉ là reference implementation, không phải novelty.
- Một trong các candidate contribution phải được chọn và đo được trước khi E2 bắt đầu: policy portability dưới tool-schema evolution, action canonicalization/alias handling, hoặc benchmark domain-specific SOC/OT với cross-channel injection.
- Research questions và hypotheses được operationalize.

**Done khi:** mỗi claim novelty có ít nhất một đối chiếu related work và một đo lường hoặc artifact thực nghiệm tương ứng; R1 xác nhận claim không trùng đóng góp trực tiếp của công trình gần.

### E2 Threat model and policy specification

**Mục tiêu:** xác định chính xác cái gì được bảo vệ, attacker có thể làm gì, và policy nào được cưỡng chế.

**Đầu ra**

- Threat model, trusted computing base và non-goals.
- Policy manifest versioned với task, tool, operation, resource, destination, expiry, call limit và approval semantics.
- Security oracle và utility oracle tách biệt.

**Done khi:** policy có schema validation, policy version/hash và không có rule mơ hồ cần LLM tự diễn giải tại execution boundary.

### E3 Benchmark and dataset protocol

**Mục tiêu:** tạo evaluation corpus độc lập với implementation policy.

**Đầu ra**

- AgentDojo version/commit, model/provider, prompt, tool schema, seed và sampling rule được khóa trước.
- Locked test split và mutation suite cho paraphrase, encoding, role-play, instruction splitting và tool-output injection.
- Case manifest chứa attack carrier, initial state, forbidden end-state oracle và task-success oracle.

**Done khi:** một người khác có thể tải đúng benchmark, chạy cùng command và nhận được cùng tập episode.

### E4 Runtime Policy Guard and instrumentation

**Mục tiêu:** hiện thực gateway an toàn và có thể kiểm toán.

**Đầu ra**

- Tool dispatcher là đường duy nhất đến executor.
- Argument/destination canonicalization, explicit deny on parse failure, capability expiry/session binding và approval workflow hoàn chỉnh.
- Audit trace append-only hoặc tamper-evident đã được kiểm thử; nếu chưa có cơ chế đó, phải gọi đúng là audit trace thường. Trace gồm input hash, policy hash, normalized call, decision, state diff và result.

**Done khi:** tool bypass test thất bại, approved action tiêu quota đúng lúc thực thi và action trái policy không tạo side effect.

### E5 Experimental analysis and manuscript

**Mục tiêu:** tạo bằng chứng thực nghiệm và bài báo hoàn chỉnh.

**Đầu ra**

- So sánh B0, B1, B2, P và ablation trên cùng model/runtime/case.
- Metrics security/utility/overhead, paired statistics, confidence intervals, charts và failure cases.
- Manuscript, bibliography, appendix, reproduction guide và artifact release.

**Done khi:** toàn bộ bảng/biểu đồ có source artifact, mọi claim kết quả dẫn tới run manifest và phần limitations giải thích external validity.

## Ba phần phản biện

### R1 Novelty and literature review

**Câu hỏi phản biện:** bài báo khác CaMeL, Fides, Progent, AgentArmor, ClawGuard và ActGov ở điểm nào; có claim nào đã được nghiên cứu trước không?

**Pass khi:** contribution statement chỉ mô tả điều có thể đo và reference list không có metadata sai.

### R2 Methods and statistical review

**Câu hỏi phản biện:** baseline có công bằng, oracles có độc lập, hypotheses có quyết định rule, sample/CI/statistical test có phù hợp không?

**Pass khi:** policy/test split đã khóa trước, metrics có numerator/denominator, approval outcome được định nghĩa và mọi kết luận định lượng có uncertainty.

### R3 Security and validity review

**Câu hỏi phản biện:** có đường bypass, policy overreach, sensitive-data leak, circularity hoặc external-validity claim nào không?

**Pass khi:** threat-to-validity table có construct/internal/external/statistical validity; không gọi component fixture là LLM benchmark.

## Hai phần kiểm thử

### T1 Policy and sandbox tests

**Kiểm tra**

- JSON/schema validation, duplicate ID/capability và invalid policy rejection.
- Tool/argument/destination/session/expiry/call-limit enforcement.
- Approval lifecycle, executor side effect và direct-call bypass.

**Pass khi:** toàn bộ test deterministic pass; action `DENY` không tạo state change; action `REQUIRE_APPROVAL` chỉ thực thi sau approval hợp lệ.

### T2 Reproducibility and benchmark tests

**Kiểm tra**

- Clean-environment run từ pinned dependency/manifest.
- Result hash, config, seed, model version, dataset version và policy version được ghi.
- Benchmark smoke test trước full run; regression test đối chiếu expected result schema.

**Pass khi:** CI chạy sạch, artifact được tái tạo được và benchmark result không phụ thuộc trạng thái cục bộ không khai báo.

## Thứ tự thực hiện

`E1 -> R1 -> E2 + E3 -> T1 -> E4 -> R2 -> E5 -> T2 -> R3`, với các review là cổng bắt buộc; không chuyển sang thí nghiệm tuyên bố efficacy khi R1 chưa chốt contribution.

## Trạng thái hiện tại

- E1: đang có manuscript và related-work foundation; cần literature matrix hoàn chỉnh và quyết định contribution hẹp sau khi đối chiếu công trình 2025–2026.
- E2: policy fixture sơ bộ có sẵn; approval lifecycle và episode semantics đã có component test; session/expiry/argument constraint chưa hiện thực.
- E3: chưa khóa AgentDojo runtime, model và test split.
- E4: component prototype có audit/effect oracle sơ bộ; chưa phải complete mediation hoặc integration với tool thật.
- E5: mới có component validation; chưa có benchmark result để trả lời RQ1–RQ3.
- R1–R3: audit ban đầu đã xác định các thiếu sót cần khắc phục.
- T1: schema, episode replay, approval transaction, audit/effect invariant và mock-dispatch authorization đã có; cần integration tests trên tool adapter thật.
- T2: GitHub Actions kiểm tra JSON và self-test; chưa có benchmark reproducibility run.
