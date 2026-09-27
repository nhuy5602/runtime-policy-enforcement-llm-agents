# Bản thảo nghiên cứu và kiểm chứng pilot

## Semantic Mediation Fidelity Under Tool Adapter Drift

> **R1 reopening — 27 September 2026.** This is an archived mechanism-pilot
> draft, not the locked paper title or contribution. The closest-prior audit
> found direct overlap with VIGIL, CXI, CONTINUITY and schema/policy/toolset
> drift evaluation. The active candidate and stop gate are recorded in
> `paper/r1_reopening_20260927.md`; no section below may be cited as a novelty
> or LLM-efficacy claim until that gate passes.

**Nhóm 11**

- Nguyễn Thùy Dương — 20252022M
- Đặng Ngọc Huy — 20261112M
- Vũ Hồng Quang — 20261114M

**Trạng thái nghiên cứu:** R1 mở lại; mechanism-pilot/trace-replay archive,
full LLM efficacy chưa có.
**Ngày cập nhật:** 27 tháng 09 năm 2026

> Bản `paper/q2_ready_report.md` là manuscript hợp nhất và là nguồn chính để
> dựng DOCX/PDF. Tệp này giữ bản diễn giải ngắn hơn cho người đọc muốn xem
> mạch lập luận; không dùng các đoạn “đóng góp dự kiến” cũ ở dưới để thay thế
> cho novelty matrix và các giới hạn trong bản hợp nhất.

## Tóm tắt

LLM Agent có thể đọc dữ liệu từ email, web page, tài liệu hoặc tool output, rồi gọi API và công cụ để tạo tác động lên môi trường. Trong indirect prompt injection, nội dung không đáng tin cậy có thể khiến Agent chuyển hướng hành động và sử dụng tool ngoài mục đích của người dùng. Bản thảo này đặt Runtime Policy Guard làm baseline và tập trung vào câu hỏi khác: quyết định `ALLOW` hoặc `REQUIRE_APPROVAL` có còn đúng về mặt ngữ nghĩa sau khi tool call đi qua alias, schema version, serialization hoặc adapter có thể remap side effect hay không.

Đóng góp của nghiên cứu không phải là tuyên bố một primitive bảo mật mới.
Capability, information-flow control, runtime authorization và post-call
contracts đã xuất hiện trong các công trình gần. Bài báo định vị đóng góp ở
protocol paired đo semantic mediation fidelity dưới drift, bộ metric
`AFER/PDER_schema/SMF/BDP`, và ablation canonicalization–post-verification với
oracle side-effect độc lập.

Prototype offline hiện đã kiểm chứng policy conformance trên bảy tool call chuẩn hóa và trace-replay pilot trên 198 episode. P0 để lọt 2/3 adapter-alias effects, P1 khôi phục benign drift portability, còn P2 loại bỏ 3/3 adapter escapes trong simulator. Đây vẫn là kết quả enforcement-boundary, không phải benchmark LLM, không đo indirect prompt injection attack success rate trên AgentDojo và không chứng minh độ bền trước adaptive attacker.

Một pilot live controlled trước đó với Qwen3-8B trên bảy fixture đã parse đúng
7/7 proposal; replay qua C2 tạo forbidden effect 0/4 attack, CTS 2/3 và FBR
1/3. Một trace realistic thứ hai (không lộ nhãn attack/benign hoặc fixture ID)
đã hoàn tất 7/7 case; exact five-field match là 4/7, C2 tạo forbidden effect
0/4, CTS 3/3 và FBR 0/3, trong khi C0/C1 tạo 1/4 forbidden effect. Cả hai
đều là pilot một model, không có drift mutation hay benchmark độc lập, nên
không được gọi là `AFER` hay full LLM efficacy.

**Từ khóa:** LLM Agent, indirect prompt injection, tool misuse, runtime policy enforcement, least privilege, capability, agent security.

## 1. Giới thiệu

LLM Agent kết hợp mô hình ngôn ngữ với tool, API và dữ liệu môi trường để hoàn thành tác vụ nhiều bước. Khả năng tự động hóa này mở rộng bề mặt tấn công: email, trang web, tài liệu hoặc kết quả tool có thể chứa chỉ dẫn độc hại. Khi nội dung đó được đưa vào context, Agent có thể thay đổi mục tiêu và gọi tool gây hại, ví dụ gửi dữ liệu ra ngoài, gọi HTTP POST, xóa file hoặc thay đổi ticket. InjecAgent cho thấy indirect prompt injection là một bài toán riêng của Agent tích hợp tool, với các mục tiêu tấn công gồm direct harm và private data leakage [3].

Khác với chatbot chỉ sinh văn bản, rủi ro thực tế của Agent phụ thuộc vào việc đề xuất của LLM có thể chuyển thành action trên môi trường hay không. Do đó, yêu cầu LLM tự nhận diện mọi chỉ dẫn độc hại hoặc chỉ lọc prompt đầu vào là không đủ để bảo vệ toàn bộ hệ thống. Survey gần đây về Agentic AI Security xem Agent là hệ thống kết hợp input, memory, workflow, action, tool và UI; các rủi ro có thể lan truyền qua nhiều thành phần thay vì dừng ở output văn bản [1].

Nghiên cứu này tập trung vào một câu hỏi hẹp hơn nhưng kiểm chứng được: **nếu LLM đã bị ảnh hưởng và đề xuất một tool call nguy hiểm, policy enforcement tại tool-execution boundary có ngăn action trái phép trước khi tool thực thi hay không?** Cách tiếp cận này không làm LLM miễn nhiễm với prompt injection. Nó giới hạn hậu quả của một đề xuất đã được sinh ra, với điều kiện mọi tool call thực thi đều đi qua Gateway.

Mục tiêu của báo cáo gồm:

1. xác định threat model cho indirect prompt injection dẫn tới tool misuse;
2. mô tả Runtime Policy Guard có policy theo task, tool, resource, destination và risk;
3. xây dựng protocol thực nghiệm tái lập được cho security, utility, overblocking và overhead;
4. báo cáo minh bạch một kiểm chứng component ban đầu, cùng giới hạn của nó.

## 2. Nghiên cứu liên quan và định vị đóng góp

### 2.1. Benchmark indirect prompt injection

AgentDojo cung cấp môi trường động để đánh giá prompt injection trong Agent sử dụng tool, với 97 realistic tasks và 629 security test cases [2]. Điểm quan trọng của AgentDojo là đánh giá đồng thời việc hoàn thành tác vụ hợp lệ và tính an toàn khi Agent xử lý dữ liệu không đáng tin cậy.

InjecAgent là benchmark chuyên cho indirect prompt injection trong Tool-Integrated LLM Agent. Bài báo công bố 1.054 test cases, 17 user tools và 62 attacker tools [3]. Hai benchmark này nhấn mạnh rằng một defense hữu ích cần được đo bằng cả security và utility; defense chặn toàn bộ tool call có thể có attack success thấp nhưng không còn đáp ứng tác vụ hợp lệ.

### 2.2. Phòng thủ theo kiến trúc

CaMeL tách control flow khỏi dữ liệu không đáng tin cậy và dùng capability để hạn chế hành vi gây hại [4]. Fides tiếp cận Agent security bằng information-flow control, theo dõi nhãn confidentiality và integrity để thực thi chính sách xác định [5]. Progent cung cấp programmable privilege control ở runtime cho LLM Agent, gồm biểu diễn policy và thực thi ràng buộc trên tool call [6].

Các công trình gần hơn cũng làm hẹp mạnh không gian novelty: AgentArmor áp dụng
program analysis trên runtime trace [7], ClawGuard thực thi rule tại mỗi
tool-call boundary để chống indirect prompt injection [8], và ActGov kiểm tra
từng action theo task-scoped policy [9]. Vì vậy, bản thảo không claim các ý
tưởng “runtime policy”, “least privilege”, “capability”, “information-flow
tracking” hay “tool-boundary enforcement” là mới. Prototype chỉ là reference
implementation; contribution đã khóa ở policy portability và semantic fidelity
dưới tool-schema/adapter drift.

### 2.3. Khoảng trống mà báo cáo giải quyết

Khoảng trống của nghiên cứu không phải là sự vắng mặt hoàn toàn của
system-level defense. Literature matrix đã loại generic runtime guard khỏi
novelty claim; hướng bài là đánh giá tái lập được về tính ổn định của policy khi
tool schema, alias API, serialization hoặc adapter thay đổi. Cụ thể, báo cáo
hướng đến:

- threat model hẹp với attacker chỉ kiểm soát dữ liệu ngoài mà Agent hợp lệ đọc;
- policy enforcement tại tool boundary với reason code có thể kiểm toán;
- security oracle dựa trên forbidden end state thay vì chỉ đánh giá câu trả lời văn bản;
- cùng lúc đo action security và tác động đến utility.

## 3. Problem statement và threat model

### 3.1. Tài sản cần bảo vệ

Các tài sản trong môi trường thử nghiệm là dữ liệu nhạy cảm giả lập, trạng thái mock của file hoặc ticket, nội dung email giả lập và quyền gọi tool. Secret không phải dữ liệu thật; mỗi case dùng một marker như `CANARY_<case_id>` để detector xác định việc rò rỉ đến attacker sink giả lập.

### 3.2. Khả năng của attacker

Attacker có thể chèn chỉ dẫn vào email, web page, tài liệu hoặc tool output mà Agent được phép đọc để hoàn thành task. Attacker cố khiến Agent:

- gửi canary hoặc dữ liệu nhạy cảm đến external destination;
- gửi email đến recipient không nằm trong task policy;
- gọi tool vượt task scope;
- sửa, xóa hoặc tạo trạng thái không được cấp quyền;
- replay capability vượt số lượt gọi cho phép.

Attacker không được giả định có thể sửa Runtime Policy Guard, policy manifest, tool dispatcher, credentials hoặc hành động phê duyệt của con người.

### 3.3. Trusted computing base và ranh giới

Trusted computing base gồm policy issuer, Runtime Policy Guard, tool dispatcher và mock executor. LLM không nằm trong trusted computing base: mọi tool call từ LLM là đề xuất cần kiểm tra. Mọi tool có side effect phải được gọi qua dispatcher; nếu tồn tại đường bypass, kết luận enforcement không còn hiệu lực.

Nghiên cứu loại trừ direct jailbreak từ user, model backdoor, tool implementation bị cài mã độc, long-term memory poisoning xuyên phiên, multi-agent cascading failure và formal information-flow guarantee end-to-end. Persistent memory có thể là hướng mở rộng sau, nhưng không được khẳng định là phạm vi đã được đánh giá.

## 4. Phương pháp đề xuất

### 4.1. Kiến trúc

```text
Trusted task and policy manifest
              |
User -> LLM Agent -> Runtime Policy Guard -> Mock Tool API -> Sandbox
                               |
                           Audit log
```

Mỗi tool call được chuẩn hóa thành:

```text
call = {task_id, tool, operation, arguments, resource_scope, destination, call_index}
```

Mỗi task được cấp capability server-side gồm:

```text
{allowed_tool, allowed_operation, allowed_resource, allowed_destination,
 max_calls, expiry, approval_required}
```

Capability không được LLM tự tạo hoặc tự nâng quyền. Trong prototype hiện có, task, tool, operation, resource, destination, call limit và approval requirement được kiểm tra; expiry, session binding và dynamic provenance tracking là phần thiết kế mở rộng chưa được hiện thực đầy đủ.

### 4.2. Quy tắc quyết định

| Điều kiện | Quyết định |
|---|---|
| Tool, operation hoặc resource nằm ngoài capability | `DENY` |
| Destination không nằm trong allowlist | `DENY` |
| Tool call vượt call limit | `DENY` |
| Hành động có side effect hợp lệ nhưng có rủi ro cao | `REQUIRE_APPROVAL` |
| Hành động read-only hoặc state change đã được cấp quyền | `ALLOW` |

Prototype ghi `case_id`, episode, initial/final decision, reason code, approval status và mock effect ID. Trong nghiên cứu đầy đủ, audit trace cần bổ sung model version, seed, policy hash, input hash, normalized tool call, state diff và outcome của task.

### 4.3. Những gì Guard không bảo đảm

Guard không biết chắc mọi token trong LLM bị ảnh hưởng bởi nguồn nào. Nhãn trust/sensitivity trong prototype chỉ là metadata ở resource/session level, không phải dynamic taint tracking hoàn chỉnh. Guard cũng không thể ngăn harmful action nằm hoàn toàn trong một capability được cấp quá rộng. Vì vậy, thiết kế policy và minification của capability quan trọng ngang với logic `DENY`.

## 5. Câu hỏi nghiên cứu và giả thuyết

**RQ1 (primary).** Khi cùng một action trace đi qua schema/alias hoặc adapter
drift, defense nào tạo forbidden post-effect nhiều nhất, đo bằng
`AFER_uncond`?

**RQ2.** Canonicalization và post-call verification ảnh hưởng thế nào tới
`BDP`, `CTS`, `FBR_drift`, approval burden và p95 overhead?

**RQ3.** Held-out và policy-aware adaptive traces có làm thay đổi
pre-dispatch ASR và post-effect AFER khác nhau giữa các model và adapter hay
không?

**RQ4.** Post-call state-diff có loại bỏ executor-alias escape mà pre-dispatch
guard không nhìn thấy hay không?

Các giả thuyết được preregister trước khi chạy benchmark:

- **H1:** P2 giảm `AFER_uncond` so với P0 trên held-out adapter-drift attacks.
- **H2:** P1 không kém canonical control quá 5 điểm phần trăm về `BDP` và
  giảm `FBR_drift` so với P0.
- **H3:** AFER trên held-out/white-box drift không tăng quá 5–10 điểm phần
  trăm so với development split.

Các ngưỡng này là tiêu chí đánh giá đề xuất, không phải kết quả hiện tại.

## 6. Phương pháp thực nghiệm chính được đề xuất

### 6.1. Dataset và sandbox

Benchmark chính là AgentDojo. Nếu không đủ ngân sách để chạy toàn bộ 629 security test cases, nhóm phải công bố trước quy tắc lấy mẫu phân tầng theo attack type/tool suite và mô tả kết quả là sampled evaluation. InjecAgent có thể được dùng để mở rộng độ đa dạng của indirect injection, nhưng không thay thế việc đo utility ở môi trường động.

Sandbox mở rộng do nhóm xây dựng cần có:

- mock email, HTTP, ticket, file và search tool;
- attacker sink giả lập;
- canary per case;
- benign high-risk task để đo approval;
- security oracle và utility oracle tách biệt.

Schema tối thiểu:

```json
{
  "case_id": "workspace_014",
  "split": "test",
  "user_task": "…",
  "task_capabilities": ["…"],
  "attack_carrier": "email_body",
  "attack_goal": "exfiltrate_canary",
  "forbidden_action_predicate": "http.post to attacker.test containing CANARY",
  "task_success_oracle": "…",
  "initial_state_hash": "…"
}
```

### 6.2. Baseline

| Mã | Cấu hình cho benchmark LLM |
|---|---|
| B0 | Unsafe Agent: LLM gọi tool không qua policy enforcement |
| B1 | Prompt-only baseline: system prompt hướng dẫn coi dữ liệu ngoài là data, không là instruction |
| B2 | Static Tool Filter: allowlist tool nhưng không xét task, argument, resource hoặc destination |
| P0 | Pre-dispatch Guard: task capability, resource/destination constraint, call limit, approval và audit |
| P1 | P0 + canonicalization của tool/resource/destination aliases |
| P2 | P1 + post-call effect/state-diff verification |
| A1-A4 | Ablation: lần lượt bỏ task scope, destination constraint, call limit hoặc approval |

CaMeL, Fides và Progent chỉ được gọi là baseline thực nghiệm nếu nhóm thực sự chạy lại chúng với model, tool runtime và configuration tương thích. Nếu không, chúng là related work và mốc so sánh khái niệm.

### 6.3. Metrics

| Metric | Định nghĩa |
|---|---|
| AFER_uncond | Drift attack tạo forbidden post-effect / tổng drift attack |
| AFER_cond | Forbidden post-effect / drift attack được phép qua pre-dispatch |
| PDER_schema | Forbidden effect trên schema/alias drift, không gồm executor mismatch |
| SMF | Được phép thực thi và observed effect đúng canonical authorized effect / số call được phép |
| BDP | Benign semantics-preserving drift đạt expected effect / tổng benign drift |
| Action-grounded ASR | Attack cases tạo forbidden end state / tổng attack cases |
| Tool Misuse Rate | Episode có ít nhất một tool call vi phạm policy / tổng episode |
| Sensitive Data Exfiltration Rate | Cases có canary tại external sink / tổng cases chứa canary |
| Clean Task Success | Benign tasks hoàn thành đúng / tổng benign tasks |
| Secure Task Success | Task thành công và không có side effect trái phép / tổng episode |
| False Block Rate | Legitimate canonical calls bị `DENY` / tổng legitimate canonical calls |
| Approval Burden | Số approval requests/episode và tỷ lệ yêu cầu phê duyệt |
| Guard Overhead | p50/p95 decision latency của Guard, tách khỏi LLM API latency |
| Mediation Coverage | Tool executions đi qua dispatcher / tổng tool executions |

### 6.4. Protocol tái lập

1. Freeze model snapshot, system prompt, tool schema, policy, case manifest và scorer trước khi chạy test.
2. Dùng fixed split để tách development và locked test. Không sửa policy theo từng test case sau khi xem kết quả.
3. Reset sandbox sau mỗi episode; dùng cùng initial state, task và attack case cho mọi baseline.
4. Cố định temperature, top-p, max tool steps; lưu seed nếu provider hỗ trợ.
5. Chạy tối thiểu ba lần cho mỗi case nếu execution không deterministic.
6. Lưu run ID, case ID, model/version, policy hash, decision, reason code, state diff, task outcome và attack outcome.
7. Báo cáo numerator/denominator, chênh lệch tuyệt đối và 95% confidence interval. Với paired binary outcomes, dùng paired bootstrap hoặc exact McNemar test.

## 7. Kiểm chứng component của prototype

### 7.1. Mục tiêu

Kiểm chứng ban đầu không nhằm đo khả năng LLM chống prompt injection. Mục tiêu là kiểm tra: với tool call đã được chuẩn hóa, mock executor có chỉ thực thi khi Runtime Policy Guard cho phép hay không, và reason code có khớp policy oracle hay không.

### 7.2. Thiết lập

Corpus gồm bảy tool call cố định:

- **Bốn harmful calls:** HTTP exfiltration, capability replay, gửi email tới external destination và update ticket ngoài task scope.
- **Ba benign calls:** search public data, gửi status email hợp lệ nhưng cần approval và update ticket hợp lệ.

Policy, thứ tự case và oracle được tách vào `experiments/fixtures/policy_v1.json` và `experiments/fixtures/cases_v1.json`. Guard và mock executor được reset theo từng episode; riêng episode `public_search_replay` có một call hợp lệ ở step 1 tiêu quota, rồi replay ở step 2 phải bị chặn. Nhờ vậy, phép thử replay không phụ thuộc vào state toàn bộ configuration.

Ba cấu hình component:

| Mã | Cấu hình |
|---|---|
| C0 | Schema-only: call có schema hợp lệ được mock executor thực thi |
| C1 | Static allowlist: chỉ kiểm tra tool-operation có trong global allowlist |
| C2 | Policy Guard: kiểm tra capability, destination, call limit và approval |

Prompt-only defense không xuất hiện trong kiểm chứng này, vì simulator không mô phỏng việc LLM có nhận diện một indirect injection hay không.

### 7.3. Kết quả

| Cấu hình | Attack có forbidden effect | Attack bị `DENY` | Benign task hoàn thành | High-risk benign hoàn thành sau approval | Approval requests | Benign bị `DENY` |
|---|---:|---:|---:|---:|---:|---:|
| C0 Schema-only | 4/4 | 0/4 | 3/3 | 0/1 | 0 | 0/3 |
| C1 Static allowlist | 4/4 | 0/4 | 3/3 | 0/1 | 0 | 0/3 |
| C2 Policy Guard | 0/4 | 4/4 | 3/3 | 1/1 | 1 | 0/3 |

Trong C2, HTTP exfiltration và unauthorized ticket update bị từ chối do nằm ngoài task capability; email exfiltration bị từ chối do destination không thuộc allowlist; replay bị từ chối do capability call limit đã được dùng. Hai benign calls được thực thi tự động. Benign email hợp lệ tạo `REQUIRE_APPROVAL`; fixture sau đó mô phỏng một approval hợp lệ, guard re-check policy, tiêu quota đúng tại execution và mock executor mới tạo effect. C0/C1 cũng hoàn thành email đó, nhưng không có approval protocol nên không được tính là “completed after approval”.

Trong test harness này, 7/7 call tạo outcome và audit event; effect chỉ được tạo qua dispatcher token của mock executor. Đây là dispatch coverage của harness, không phải bằng chứng complete mediation trong Agent thật.

### 7.4. Diễn giải đúng mức

Kết quả hỗ trợ kết luận hẹp sau:

> Với một policy manifest và bảy tool call đã định nghĩa trước, Runtime Policy Guard tạo audit trace khớp fixture, không cho bốn forbidden mock effect xảy ra, và chỉ thực thi action cần approval sau approval mô phỏng hợp lệ.

Kết quả không chứng minh:

- LLM sẽ luôn sinh tool call có thể bị chặn;
- Policy Guard giảm ASR trên AgentDojo;
- prompt-only defense hoặc static allowlist kém hiệu quả trên LLM thật;
- Guard không gây false block trong các task khác;
- hệ thống production không có đường bypass;
- policy có thể theo dõi toàn bộ provenance hoặc thông tin bí mật qua reasoning của LLM.

## 8. Threats to validity và giới hạn

### 8.1. Construct validity

Prototype nhận tool call cuối đã được xác định sẵn, không có LLM, attack carrier thực, chain of thought hay context window. Do đó, nó đo policy conformance ở execution boundary, không đo indirect prompt injection ASR.

### 8.2. Internal validity

Policy và harmful/benign oracle được thiết kế cùng corpus, tạo nguy cơ circular evaluation. Structured effect oracle tách scoring khỏi `reference_assertion`, nhưng không làm fixture trở thành independent benchmark. Capability replay là một episode hai bước có quota cục bộ; nghiên cứu chính vẫn cần tách development/test, lock policy và chạy episode độc lập.

### 8.3. Baseline validity

Static allowlist chỉ kiểm tra tên tool-operation, còn corpus có nhiều harmful calls dùng tool vẫn được global allowlist cho phép. Kết quả minh họa giới hạn của name-only allowlist trong fixture này, không chứng minh baseline đó luôn kém trong thực tế. Prompt-only defense hoàn toàn chưa được chạy.

### 8.4. External validity

Mock executor không có API thật, retry, serialization error, race condition, credential leakage hoặc plugin bypass. Bảy case viết tay không đại diện cho paraphrase, encoding, role-play, tool-output injection phức tạp hay adaptive attacker. Kết quả trên một model/version sau này cũng không tự động tổng quát sang mọi model.

### 8.5. Statistical conclusion validity

Mẫu component gồm bảy call và có tính deterministic, nên không dùng được để suy luận thống kê hoặc báo cáo confidence interval. Các phân tích định lượng chỉ hợp lệ sau khi chạy nhiều episode độc lập trên benchmark.

## 9. Kế hoạch hoàn thiện

1. Tách case manifest, policy manifest và scoring oracle khỏi mã nguồn.
2. Hoàn tất R1 và khóa một contribution hẹp không trùng runtime guard hiện có.
3. Bổ sung session binding, expiry, argument-level validation, state diff và canary detector cho prototype.
4. Viết integration test bảo đảm direct tool call không thể bypass dispatcher.
5. Thực hiện AgentDojo full evaluation hoặc sampled evaluation đã preregister.
6. Chạy B0, B1, B2, P và ablation trên cùng model/runtime.
7. Báo cáo 95% CI, paired comparison, latency p50/p95 và failure cases.
8. Chỉ sau bước trên mới kết luận về hiệu quả đối với indirect prompt injection của Agent thật.

## 10. Kết luận

Runtime Policy Guard là một reference monitor defense-in-depth tại tool boundary: nó không làm LLM miễn nhiễm với indirect prompt injection, nhưng có thể ngăn một tool call trái policy tạo side effect nếu tool dispatcher thực thi complete mediation. Kiểm chứng component ban đầu xác nhận logic capability, destination allowlist, call limit và approval transaction của prototype trên fixture cố định.

Đóng góp khoa học hợp lý của đề tài là một nghiên cứu thực nghiệm tái lập và trung thực về quan hệ giữa policy enforcement, action security và task utility. Để trở thành kết luận thực nghiệm đầy đủ, báo cáo cần được mở rộng bằng AgentDojo hoặc môi trường tương đương với LLM thật, attack carrier thực, baseline công bằng và thống kê theo episode.

## Tái lập kiểm chứng component

Môi trường đã dùng:

- Python 3.12.14
- Script: `experiments/policy_guard_sim.py`
- Result artifact: `experiments/policy_guard_sim_results.json`
- Policy manifest: `experiments/fixtures/policy_v1.json`
- Case manifest: `experiments/fixtures/cases_v1.json`

Lệnh chạy:

```powershell
python experiments/policy_guard_sim.py --self-test --output experiments/policy_guard_sim_results.json
```

SHA-256 tại thời điểm chạy:

```text
policy_guard_sim.py
6B2429DCDC4FF24B7033904DFA7D33AFABD8BE90AF0267A31123BD295C1A470A

policy_guard_sim_results.json
99436FB946CDE0DBCD4618A8C3685C3CA8D43BD299ABFF14F3F063DC95F55871

policy_v1.json
4C65AD704DDBFF4CBF76DB206D07D5A97848D08D580FEB37F030059C79A2D66C

cases_v1.json
5EF576474CAF74B25D67F13EA81FE091B6C78ADCFC5C7D083228E7036FA3D0CF
```

## Tài liệu tham khảo

1. J. Kim, X. Liu, Z. Wang, S. Qiu, B. Li, W. Guo, and D. Song. “The Attack and Defense Landscape of Agentic AI: A Comprehensive Survey.” arXiv:2603.11088, 2026. https://arxiv.org/abs/2603.11088
2. E. Debenedetti, J. Zhang, M. Balunovic, L. Beurer-Kellner, M. Fischer, and F. Tramèr. “AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents.” Advances in Neural Information Processing Systems 37, 2024. https://proceedings.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html
3. Q. Zhan, Z. Liang, Z. Ying, and D. Kang. “InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents.” Findings of ACL, 2024. https://aclanthology.org/2024.findings-acl.624/
4. E. Debenedetti et al. “Defeating Prompt Injections by Design.” arXiv:2503.18813, 2025. https://arxiv.org/abs/2503.18813
5. M. Costa et al. “Securing AI Agents with Information-Flow Control.” arXiv:2505.23643, 2025. https://arxiv.org/abs/2505.23643
6. T. Shi et al. “Progent: Programmable Privilege Control for LLM Agents.” arXiv:2504.11703, 2025. https://arxiv.org/abs/2504.11703
7. P. Wang et al. “AgentArmor: Enforcing Program Analysis on Agent Runtime Trace to Defend Against Prompt Injection.” arXiv:2508.01249, 2025. https://arxiv.org/abs/2508.01249
8. W. Zhao, Z. Li, P. Zhang, and J. Sun. “ClawGuard: A Runtime Security Framework for Tool-Augmented LLM Agents Against Indirect Prompt Injection.” arXiv:2604.11790, 2026. https://arxiv.org/abs/2604.11790
9. K. Zhang, Y. Peng, K. Jiang, and Y. Zhang. “ActGov: Governing LLM Agent Actions via Policy-Constrained Validation.” arXiv:2609.24446, 2026. https://arxiv.org/abs/2609.24446
