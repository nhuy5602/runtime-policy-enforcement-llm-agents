# Q2 Ready Research Roadmap

## Mục tiêu

Xây dựng manuscript và research artifact **submission-ready** cho một venue hoặc tạp chí Scopus Q2 trở lên. Sau R1 ngày 27 tháng 09 năm 2026, hướng làm việc là ứng viên **Security Regression Testing of Indirect Prompt-Injection Defenses under Versioned Agent Tool Contracts**; nó chưa phải contribution đã khóa. Semantic mediation fidelity chỉ còn là artifact stress/measurement của reference guard. Đây là chuẩn chất lượng nội bộ, không phải cam kết được nhận: phân hạng Q2, phạm vi venue và phản biện độc lập đều nằm ngoài quyền kiểm soát của nhóm.

Repository này không lưu báo cáo tuần. Mọi workstream bên dưới chỉ phục vụ manuscript, benchmark và artifact tái lập của bài báo.

Project có hai tầng giao hàng:

1. **Research tier:** submission candidate cho venue/tạp chí Q2+ nếu vượt qua
   literature, live-evidence, thống kê và reproducibility gates.
2. **Course tier:** bài báo và bài trình bày hoàn chỉnh theo yêu cầu môn học,
   kể cả khi research tier chưa đủ bằng chứng để submit.

## Tiêu chí Q2 ready

Trước khi coi manuscript sẵn sàng gửi phản biện ngoài, dự án phải chứng minh:

1. Khoảng trống và đóng góp khác biệt rõ với runtime PEP, AgentSpec, PACT, RAC, TraceGrant, CaMeL, Fides, Progent, AgentArmor, ClawGuard và ActGov.
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
- Candidate contribution đang được audit là paired security-regression benchmark: cùng IPI case ở `v0 -> v1` contract migration, scored bằng harmful-effect oracle; không được khóa trước literature stop gate.
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
- Manifest ghép cặp `v0`/`v1` buộc cùng case, planned no-injection benign arm, defense, model configuration, seed, reset và oracle; có counterbalance order và không thay case khi `not_scored`. Arm này chỉ thành control hợp lệ khi initial state và utility oracle riêng được version/pin.

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

- So sánh B0–B6 và P0/P1/P2 trên cùng model/runtime/case; phase hiện tại
  đã có B0, B1, B2, B4, P0, P1, P2 cùng bốn ablation offline. B3/B5/B6,
  held-out drift và full LLM efficacy vẫn pending.
- Metrics security/utility/overhead, paired statistics, confidence intervals, charts và failure cases.
- Manuscript, bibliography, appendix, reproduction guide và artifact release.

**Done khi:** toàn bộ bảng/biểu đồ có source artifact, mọi claim kết quả dẫn tới run manifest và phần limitations giải thích external validity.

## Ba phần phản biện

### R1 Novelty and literature review

**Câu hỏi phản biện:** bài báo khác CaMeL, Fides, Progent, AgentArmor, ClawGuard và ActGov ở điểm nào; có claim nào đã được nghiên cứu trước không?

**Pass khi:** contribution statement chỉ mô tả điều có thể đo và reference list không có metadata sai.

### R2 Methods and statistical review

The locked estimands, independent cluster rule, McNemar/bootstrap procedures,
Holm families, missingness bounds, precision/power gates, and stopping rule are
specified in [`paper/statistical_analysis_plan.md`](paper/statistical_analysis_plan.md).

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

`E1 -> R1 -> E2 + E3 -> T1 -> E4 -> R2 -> E5 -> T2 -> R3`, với các review là
cổng bắt buộc; R1 hiện **mở lại** và cấm full billable benchmark cho đến khi
candidate có literature-audit record. Không được chuyển sang claim LLM efficacy
khi chưa có full run, held-out migration và raw redacted traces.

## Trạng thái hiện tại

Hướng cố định: **Security Regression Testing of Indirect Prompt Injection
Defenses under Versioned Agent Tool Contracts**. R1 đánh giá đóng góp trong
hướng này; không cho phép tự đổi đề tài.

Review tiếp nhận chat ngày 07/10: nguồn task-cluster và runtime đã được nối
manifest → child → validator → statistics; adapter chỉ nhận pair-level verdict
`scored`, không chỉ hai endpoint hợp lệ riêng lẻ. Môi trường historical còn
phụ thuộc cp1252/UTF-8 mode, được kiểm tra trước request. Ngân sách được sửa
về USD 10 tổng theo ủy quyền trong thread. Những mục theo ngày bên dưới là
lịch sử, không phải xác nhận lại kết quả của chat khác.

Ưu tiên khoa học kế tiếp: thêm phòng thủ F (frozen policy) và M (migrated cùng
policy) có thực thi, cùng một migration liên quan authorization có nguồn gốc
rõ. Pilot hiện vẫn là U/D0 không phòng thủ + rename-only: dùng kiểm tra đường
chạy và negative control. Passing tests hay thiếu API key không quyết định
tính sẵn sàng cho claim về suy giảm phòng thủ.

- E1: **mở lại**; generic runtime guard và semantic-mediation stress chỉ là baseline/artifact. Xem `paper/r1_reopening_20260927.md`.
- E2: policy fixture sơ bộ có sẵn; approval lifecycle và episode semantics đã có component test; session/expiry/argument constraint chưa hiện thực.
- E3: v2 source-qualified selection, effect oracle, paired `v0`/`v1` preflight và result-bundle contract đã khóa 6 paired units/12 planned episodes; contract fail-closed fixed denominator/self-consistency và recompute attack endpoint, nhưng chưa chứng minh runtime provenance/capture và còn phơi bày thiếu arm-specific no-injection state + executable utility oracle. Audit 03/10 từng ghi mismatch pre-state ở cả ba selected binding. Fixture đó được giữ nguyên, nhưng adjudication 05/10 chạy 3 process mới × 3 case trong môi trường có source/runtime provenance được ghi lại (không chứng thực độc lập bước cài dependency/build) và tái tạo đúng tất cả carrier/injection-map/pre-state hash; vì vậy chỉ kết luận mismatch cũ bị **mâu thuẫn bởi bằng chứng mới**, không suy đoán nguyên nhân. Điều này không mở historical v2 plan: trước runtime vẫn cần benign initial state + utility oracle thật, driver bind manifest, reset/trace provenance, baseline công bằng, D1 và các gate khoa học còn lại.
- E3 bổ sung 06/10: contract prospective [agentdojo_v2_no_injecagent_default_control_contract.py](experiments/agentdojo_v2_no_injecagent_default_control_contract.py) đã pin source/default-map/default-carrier digest và pre-state cho 3 selected case, rồi gọi trực tiếp upstream utility dispatcher với terminal output + typed function trace. Đây là no-InjecAgent default-carrier control, không phải carrier-absent hay benign theo nghĩa ngữ nghĩa: input {} của AgentDojo vẫn merge default carrier content. Ba negative và ba GroundTruthPipeline positive controls đều chỉ là source-only instrument calibration (0 LLM/provider/network/remote job); positive post-state không được freeze vì có biến thiên runtime nên scorer tương lai phải validate typed post-state trực tiếp. V1 historical vẫn bất biến/fail-closed; bước tiếp theo là manifest/result-bundle v2 và driver bind đầy đủ provenance, không phải chạy benchmark.
- E3 trace compatibility 06/10: trước khi v2 manifest có thể đưa default-control vào paired v0/v1, contract [agentdojo_v2_utility_trace_normalization_contract.py](experiments/agentdojo_v2_utility_trace_normalization_contract.py) đã pin map đảo v1-exposed-name → canonical-v0-name, giữ nguyên arguments và buộc raw/canonical trace digest witness. Sáu controls chỉ rename local GroundTruthPipeline trace để kiểm tra interface với utility scorer; không phải v1 runtime, LLM, carrier hay registry evidence. Manifest/bundle v2 sau đó phải consume witness này, nếu không raw v1 trace sẽ fail-closed.
- E3 preregistration 06/10: [agentdojo_paired_v2_execution_manifest.py](experiments/agentdojo_paired_v2_execution_manifest.py) đã khóa 6 pair/12 episode prospective (3 attack + 3 no-InjecAgent default-control, mỗi pair v0/v1) và counterbalance 3 v0-first/3 v1-first. Control arm bind exact default pre-state, utility scorer, raw/canonical trace và normalization witness; attack arm vẫn bind effect oracle riêng. Không so sánh chéo attack/control endpoint.
- E3 driver 07/10: [agentdojo_paired_v2_driver.py](experiments/agentdojo_paired_v2_driver.py) đã trở thành entry point canonical cho fixed-denominator orchestration và dry-run. Driver chạy mỗi episode đúng một lần, fail-closed thành `not_run`, không fabricate evidence và không tạo paid request khi capture bridge chưa được cung cấp. Đây vẫn chưa phải runtime provenance hay LLM evidence.
- Capture bridge 07/10: [experiments/agentdojo_paired_v2_capture_bridge.py](experiments/agentdojo_paired_v2_capture_bridge.py) đã nối manifest v2 với AgentDojo thật qua fresh child process cho từng episode. Bridge pin clean commit/runtime, tắt retry OpenAI, và ghi typed pre/post/reset, carrier/default-control, registry/migration, request/response, raw/canonical trace và redacted provenance. Test local chạy được một attack pair + một default-control pair (4 episode) qua fake OpenAI-compatible server; chưa có Runpod billing.
- Pilot gate 07/10: [experiments/agentdojo_paired_v2_driver.py](experiments/agentdojo_paired_v2_driver.py) chỉ cho capture mode chạy 1 pair mỗi arm (4 episode), giữ đủ 12-row denominator, dừng provider sau lỗi đầu tiên, và yêu cầu parent/child cùng runtime CPython 3.12.13/Pydantic 2.11.4. Presentation deck và Runpod pilot vẫn chưa được coi là bằng chứng efficacy.
- R2 statistical plan 07/10: [`paper/statistical_analysis_plan.md`](paper/statistical_analysis_plan.md) now freezes the v2 estimand, pair/source-cluster units, exact McNemar, clustered bootstrap, Holm families, fixed-denominator missingness handling, precision/power gates, and no outcome-based stopping. [`experiments/agentdojo_paired_v2_statistics_adapter.py`](experiments/agentdojo_paired_v2_statistics_adapter.py) now enforces that boundary; it intentionally emits no complete rows until the live driver supplies `source_cluster_id`. The current six-pair design and four-episode pilot remain descriptive by construction.
- Course fallback 07/10: [paper/imrad_manuscript.md](paper/imrad_manuscript.md) và [paper/course_project_checklist.md](paper/course_project_checklist.md) đã được tạo để tách deliverable môn học khỏi research-tier claims.
- E4: component prototype có P0/P1/P2, audit/effect oracle sơ bộ; chưa phải complete mediation hoặc integration với tool thật.
- E5: trace-replay pilot đã đo PDER_schema/AFER_adapter; chưa có full LLM result để trả lời RQ1–RQ5.
- R1–R3: audit ban đầu đã xác định các thiếu sót cần khắc phục.
- T1: schema, episode replay, approval transaction, audit/effect invariant và mock-dispatch authorization đã có; cần integration tests trên tool adapter thật.
- T2: GitHub Actions kiểm tra JSON và self-test; chưa có benchmark reproducibility run.
