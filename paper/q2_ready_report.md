# Semantic Mediation Fidelity Under Tool Adapter Drift

> **R1 reopening — 27 September 2026.** This report preserves the prior
> protocol and mechanism pilot for auditability, but semantic mediation under
> adapter/schema drift is no longer a locked Q2 contribution. Direct closest
> work includes VIGIL, CXI, CONTINUITY and Assidiqi et al. The active candidate
> is a paired security-regression evaluation under versioned tool contracts;
> its literature stop gate is in `paper/r1_reopening_20260927.md`. Do not use
> the historical contribution or result language below as a submission claim.

## Bản báo cáo khoa học theo cấu trúc 5 phần thực thi, 3 phần phản biện và 2 phản biện mô phỏng

**Ngày cập nhật:** 27 tháng 09 năm 2026
**Trạng thái bằng chứng:** R1 mở lại; component/trace-replay pilot được giữ để
kiểm toán, benchmark LLM độc lập chưa chạy.
**Loại đóng góp:** chưa khóa; chỉ có candidate evaluation được mô tả trong R1 record.

> **Lưu ý về tính trung thực thực nghiệm.** Kết quả định lượng đã có trong bản này gồm kiểm chứng component trên bảy tool call cố định và trace-replay pilot 198 episode. Chúng đều là kiểm thử enforcement boundary trên trace được gắn nhãn, không phải Attack Success Rate của một LLM và không được dùng để suy rộng sang AgentDojo, InjecAgent hay môi trường production. Các kết quả benchmark LLM được để ở dạng protocol/preregistered analysis plan cho đến khi có run manifest và raw traces tương ứng.

## Tóm tắt

LLM agent có thể đọc email, trang web, tài liệu hoặc tool output rồi biến nội dung không đáng tin cậy thành tool call có side effect. Các công trình gần đây đã đề xuất hoặc đánh giá runtime policy enforcement, capability control, information-flow control và task-effect contracts trên các tool surface cụ thể [5–11], [23–25], [28]. Khoảng trống mà báo cáo này chọn là khác: liệu quyết định `ALLOW` hoặc `REQUIRE_APPROVAL` còn đúng về mặt ngữ nghĩa sau khi tool call đi qua alias, schema version, serialization hoặc adapter có thể remap side effect hay không. Báo cáo đặt runtime guard làm baseline và đo semantic mediation fidelity bằng deterministic post-effect oracle.

Phạm vi được giới hạn ở text-based agents, side-effecting tools chạy trong sandbox, attacker kiểm soát nội dung không đáng tin cậy nhưng không sửa model, policy issuer, policy enforcement point hoặc executor. Primary endpoint được đổi thành Adapter-induced Forbidden Effect Rate (AFER) trên drift cases; PDER_schema, benign drift portability, CTS, FBR, approval burden và latency là endpoint phụ/guardrail. Thiết kế full run gồm trace replay và end-to-end LLM tracks, ít nhất ba model snapshots, held-out drift và attacker thích nghi. Artifact hiện tại mới thực nghiệm B0, B1, B2, B4, P0, P1, P2 và bốn biến thể stress; chưa có full LLM efficacy.

Đóng góp được đề xuất là: (i) tách pre-dispatch security khỏi post-effect semantic fidelity; (ii) protocol paired để replay cùng action qua schema/adapter drift; (iii) metric AFER, PDER_schema, SMF và benign drift portability với oracle độc lập; và (iv) artifact tái lập. Component fixture chặn 4/4 forbidden mock effects, giữ 3/3 benign completions và yêu cầu approval cho 1/1 high-risk benign action. Offline trace-replay pilot trên 198 episode cho thấy PDER_schema của P0 là 0/60 applied drift attacks nhưng AFER_adapter là 2/3; P1 khôi phục benign drift portability, còn P2 loại bỏ toàn bộ 3/3 adapter escapes trong mô hình state-diff tổng hợp (P0 để lọt 2/3). Đây là bằng chứng động lực và failure analysis, không phải efficacy của LLM.

**Từ khóa:** LLM agents; indirect prompt injection; tool misuse; semantic mediation fidelity; adapter drift; schema evolution; runtime policy enforcement; reproducible evaluation.

## Bản đồ cấu trúc 5 + 3 + 2

Yêu cầu “5 phần thực thi, 3 phần phản biện, 2 phần phản biện” được diễn giải minh bạch thành năm work packages thực thi (E1–E5), ba lớp phản biện nội bộ (R1–R3) và hai phản biện mô phỏng kèm rebuttal (P1–P2). Trong một bài gửi tạp chí, E1–E5 tương ứng với Methods/Results; R1–R3 tương ứng với Related Work và Threats to Validity; P1–P2 nên đặt ở appendix hoặc hồ sơ rebuttal.

| Mã | Phần | Đầu ra bắt buộc |
|---|---|---|
| E1 | Phạm vi, threat model và đóng góp | Tài sản, attacker, TCB, non-goals, claims |
| E2 | Policy và runtime architecture | Policy schema, PEP/PDP, fail-closed, audit |
| E3 | Benchmark và attack protocol | Dataset, attack families, split, oracle, hold-out |
| E4 | Experimental design và implementation | Baselines, ablations, models, statistics, artifact |
| E5 | Results và analysis | Pilot result, planned benchmark tables, failure analysis |
| R1 | Novelty/literature review | Closest prior work, overlap gate, contribution boundary |
| R2 | Methods/statistical review | Power, pairing, CI, mixed effects, multiple testing |
| R3 | Security/validity review | Complete mediation, oracle, external validity, ethics |
| P1 | Reviewer A: security/novelty | Objection–evidence–rebuttal |
| P2 | Reviewer B: methods/reproducibility | Objection–evidence–rebuttal |

# E1. Phạm vi, threat model và đóng góp

## E1.1. Câu hỏi trung tâm và câu hỏi nghiên cứu

Câu hỏi không phải là “LLM có miễn nhiễm với prompt injection không?” và cũng không phải “runtime guard có tồn tại hay không?”. Câu hỏi kiểm chứng được là:

> Khi một tool call do LLM đề xuất đi qua schema/adapter drift, quyết định policy có còn đúng với side effect quan sát được hay không?

Tách hai cơ chế này là cần thiết. Một guard có thể `DENY` đúng ở pre-dispatch nhưng adapter vẫn tạo effect khác sau `ALLOW`; ngược lại, guard fail-closed có thể đạt security bằng cách chặn mọi alias hợp lệ. Vì vậy bài báo cáo đồng thời pre-dispatch ASR, post-effect AFER và utility dưới drift.

| RQ | Câu hỏi đo được | Endpoint chính |
|---|---|---|
| RQ1 | Khi action đi qua adapter/schema drift, defense nào tạo forbidden post-effect nhiều nhất? | AFER_uncond; AFER_cond chẩn đoán |
| RQ2 | Canonicalization và post-call verification ảnh hưởng utility thế nào? | BDP, CTS, FBR_drift, AB, p95 |
| RQ3 | Held-out/white-box adaptive traces có làm thay đổi pre-dispatch ASR và AFER khác nhau không? | train–test gap, ASR, AFER |
| RQ4 | Post-call state-diff có loại bỏ executor-alias escape không? | AFER_adapter, SMF |
| RQ5 | Chi phí trung gian cho mỗi forbidden effect được ngăn là bao nhiêu? | latency, cost, approval-per-prevented-effect |

## E1.2. Mô hình episode

Mỗi episode được biểu diễn bởi:

$$
\mathcal{E}=(G, P, U, T, S_0, M),
$$

trong đó:

- $G$ là mục tiêu người dùng và các điều kiện hoàn thành;
- $P$ là policy manifest đã ký/đóng băng trước test;
- $U$ là dữ liệu không đáng tin cậy do attacker kiểm soát một phần;
- $T$ là registry tool và JSON schema;
- $S_0$ là snapshot trạng thái ban đầu của sandbox;
- $M$ là model, prompt, decoding và giới hạn số bước.

Agent phát sinh chuỗi đề xuất:

$$
a_i=(task, tool, op, args, resource, destination, provenance, i).
$$

Executor chỉ được phép biến $a_i$ thành state transition nếu PEP trả quyết định hợp lệ. Forbidden end state được đánh giá trên state diff, sink canary hoặc event log có cấu trúc; không dùng văn bản do LLM tự chấm làm ground truth chính.

## E1.3. Attacker và tài sản

Attacker được phép:

- chèn instruction vào email, web page, document, OCR text, RAG chunk hoặc tool output;
- dùng override/fake-role, instruction splitting, paraphrase, encoding, Unicode confusable, multilingual và multi-turn accumulation;
- thay recipient, resource, query hoặc argument để biến một tool call hợp lệ về schema thành action ngoài quyền;
- quan sát kết quả episode và thích nghi trong ngân sách truy vấn đã định trước;
- biết policy manifest trong white-box track, nhưng không biết token bí mật của executor.

Attacker không được phép sửa model weights, system prompt tin cậy, policy issuer, PEP/PDP, sandbox host, credential store hoặc approval của người dùng. Direct user jailbreak, model backdoor, OS/container escape, denial of service và tool implementation đã bị cài mã độc nằm ngoài phạm vi.

Tài sản bảo vệ gồm:

1. **Confidentiality:** canary/PII không đi tới attacker sink hoặc recipient ngoài allowlist.
2. **Integrity:** không tạo/sửa/xóa file, ticket, email hoặc record ngoài scope.
3. **Least privilege:** không dùng lại capability sau quota, session hoặc expiry.
4. **Operational safety:** action irreversible/high-impact phải có approval; policy service lỗi phải fail-closed.

Mức độ side effect được phân tầng trước test:

| Mức | Ý nghĩa | Ví dụ |
|---|---|---|
| S0 | Không có side effect | Chỉ trả lời văn bản |
| S1 | Đọc ngoài scope | Search resource không được cấp |
| S2 | Thay đổi trạng thái | Update/delete ticket hoặc file |
| S3 | Egress/privilege escalation | Gửi canary ra external sink, thay credential |

## E1.4. Đóng góp và ranh giới novelty

Các primitive capability, information-flow control, least privilege, runtime contracts và action validation đã được nghiên cứu trong CaMeL, Fides, Progent, AgentArmor, ClawGuard, ActGov, AgentSpec, PACT, RAC, TraceGrant và công trình MCP runtime policy năm 2026 [5–11], [23–25], [28]. Các công trình về policy-invisible violations và agent–human interaction [26, 27] mở rộng threat/validity context nhưng không được dùng làm bằng chứng cho một primitive enforcement mới. Trong đó nhiều công trình gần là preprint/arXiv tại thời điểm khóa protocol; các claim về design space được neo thêm vào benchmark/công trình peer-reviewed [1–4], [14], [18–22]. Vì vậy báo cáo này không claim “first runtime policy guard” hoặc “first post-call contract”. Contribution được khóa ở dạng extension/replication:

**C1 — Semantic mediation protocol.** Tách pre-dispatch decision khỏi observed post-effect, với cùng trace được replay qua canonical, harmless drift và semantic-remapping adapter.

**C2 — Drift metric suite.** Định nghĩa AFER_uncond/cond, PDER_schema, SMF và benign drift portability; denominator không được trộn schema alias với executor mismatch.

**C3 — Adapter/state-diff stress test.** Đánh giá canonicalization và post-call verification như ablation/extension của runtime guard, với state-diff/canary oracle độc lập.

**C4 — Reproducibility artifact (planned).** Full run sẽ công bố manifest, hash, seed, model snapshot, prompt, policy version, drift map, trace redaction và lệnh tái tạo bảng chính. Ở trạng thái hiện tại, artifact mới bao phủ policy/case/runner hashes, dry-run/auth probe và lệnh self-test; chưa có model snapshot, container/lockfile hay bảng efficacy LLM. Nếu không hoàn thành benchmark LLM và C1–C3, bài phải được định vị là protocol/pilot report, không phải efficacy paper.

# E2. Policy và runtime architecture

## E2.1. Kiến trúc

```text
Trusted user goal + policy manifest
                 |
          LLM Agent / planner
                 |
       PEP: normalize + validate
                 |
       PDP: evaluate policy/risk
        |       |        |
      ALLOW   ASK       DENY
        |       |
     executor  approval + re-check
        |
  deterministic sandbox + state diff
        |
  append-only audit trace (redacted)
```

PEP (Policy Enforcement Point) là đường duy nhất từ đề xuất tool call tới executor. PDP (Policy Decision Point) không dùng LLM để quyết định quyền cuối cùng. Detector ngữ nghĩa, nếu có, chỉ là tín hiệu risk bổ trợ; parse lỗi, policy conflict hoặc provenance không xác định phải dẫn tới `DENY`/`ASK_USER` theo fail-closed profile.

## E2.2. Policy manifest

Policy tối thiểu có các trường:

```json
{
  "policy_version": "v1",
  "task_id": "send_status",
  "tool": "mail",
  "operation": "send",
  "resource": "status_update",
  "allowed_destinations": ["company.edu"],
  "argument_constraints": {"max_bytes": 4096},
  "sensitivity": {"allow_egress": false},
  "max_calls": 1,
  "session_id": "episode-bound",
  "expires_at": "2026-09-26T23:59:59Z",
  "approval": "required_for_external_write",
  "default_on_unknown": "DENY"
}
```

Manifest được canonicalize, hash và version-control. Quyền không do LLM tự cấp. Mỗi capability gắn với task/session, resource, destination, quota và expiry. `ALLOW` chỉ có hiệu lực tại commit/execution; preflight không được tiêu quota.

## E2.3. Semantics quyết định

| Điều kiện | Quyết định |
|---|---|
| Tool/operation/resource không nằm trong capability | `DENY` |
| Destination hoặc recipient ngoài allowlist | `DENY` |
| Argument không khớp canonical schema/constraint | `DENY` |
| Sensitive data đi tới sink không được cấp | `DENY` |
| Call vượt quota, session hoặc expiry | `DENY` |
| Write/transfer irreversible nằm trong scope nhưng risk cao | `REQUIRE_APPROVAL` |
| Read-only hoặc state change hợp lệ, ít rủi ro | `ALLOW` |
| Policy conflict, timeout hoặc provenance unknown | `DENY` trong primary profile; báo sensitivity analysis với `ASK_USER` nếu được preregistered |

Approval là transaction hai pha: preflight trả `REQUIRE_APPROVAL` nhưng không tạo effect; sau approval, guard re-check toàn bộ policy, quota và state; chỉ khi còn hợp lệ mới commit và tiêu quota.

## E2.4. Bất biến an toàn

Các invariant được kiểm tra bằng test tự động:

1. `DENY ⇒ no side effect`.
2. `ALLOW ⇒ normalized call satisfies policy`.
3. `REQUIRE_APPROVAL ⇒ no quota consumption before approval`.
4. `approved action ⇒ re-check policy before execution`.
5. `call_count ≤ max_calls` trong một session.
6. `direct executor call without dispatcher token ⇒ fail`.
7. `audit event` có cùng `case_id`, decision, reason và effect identifier với outcome.

Prototype hiện tại kiểm tra các invariant trên ở mức mock executor. Complete mediation của một agent runtime thật vẫn là một assumption phải được test integration riêng.

# E3. Benchmark và attack protocol

## E3.1. Nguồn dữ liệu

Đánh giá chính dùng ba lớp:

1. **AgentDojo**: dynamic environment cho prompt injection, có task hợp lệ và security test; phải pin commit, model adapter, workspace snapshot và scorer [1].
2. **InjecAgent**: benchmark tool-integrated indirect injection với user tools, attacker tools, direct harm và exfiltration; dùng để kiểm tra đa dạng attack carrier [2].
3. **Hold-out suite do tác giả xây dựng**: 200–300 episode sandbox, năm domain (email/calendar, file/knowledge, ticketing, e-commerce, finance/travel), benign/adversarial twin cùng user goal nhưng khác nội dung không đáng tin cậy. Tool name, schema alias và attack template của test không xuất hiện trong train/dev.

τ-bench hoặc ToolSandbox có thể dùng cho utility/stateful control nếu adapter giữ nguyên oracle và không trộn kết quả giữa benchmark [12, 13]. Nếu chỉ chạy AgentDojo, bài phải gọi đúng là *single-benchmark evaluation*.

Phạm vi threat và attack carrier được đối chiếu thêm với công trình về indirect
prompt injection và sandbox [3, 4], BIPIA và ToolSword [18, 19], AGENTVIGIL [14],
Task Shield [20], MELON [21] và ASB [22]. Các baseline thông tin-flow,
privilege và runtime validation ở [5–11] được dùng để định vị contribution, không
được xem là đã tái lập trong artifact hiện tại. Risk terminology được neo vào
NIST AI 600-1 và OWASP LLM Top 10 [16, 17].

## E3.2. Attack families

Mỗi case được gắn đúng một primary family và có thể có secondary tags:

- F1: instruction override/fake system role;
- F2: secret exfiltration và recipient substitution;
- F3: unauthorized write/delete/update;
- F4: tool-chain escalation và capability replay;
- F5: obfuscation, encoding, Unicode confusable, multilingual;
- F6: cross-step accumulation và stateful TOCTOU;
- F7: policy-aware adaptive attack (black-box/white-box).

White-box attacker được xem policy semantics nhưng không được gọi executor trực tiếp. Black-box attacker chỉ quan sát outcome/reason code đã công khai. Ngân sách query, số turn và thời gian tìm payload được khóa trước.

## E3.3. Case manifest và split

Mỗi case có:

```json
{
  "case_id": "email_014",
  "split": "test",
  "domain": "email",
  "user_goal": "...",
  "tool_schema_hash": "...",
  "initial_state_hash": "...",
  "untrusted_carrier": "email_body",
  "attack_family": "F2",
  "canary_id": "CANARY_email_014",
  "allowed_end_state": "...",
  "forbidden_end_state": "...",
  "task_success_oracle": "...",
  "security_oracle": "programmatic predicate"
}
```

Split đề xuất là 70/10/20 theo **task + domain + attack template + schema version**, không phải random theo episode. Test được khóa trước khi nhìn kết quả. Mỗi episode reset về `initial_state_hash`; seed, temperature, top-p, max steps và tool timeout được ghi.

## E3.4. Policy-drift mutation

Với mỗi policy–task pair, sinh các biến thể mà semantics đáng lẽ không đổi:

- alias tool (`send_mail` ↔ `mail.send`);
- đổi thứ tự hoặc tên JSON field;
- string/number serialization;
- destination canonicalization;
- schema version tăng nhưng effect signature giữ nguyên;
- thêm field vô hại và field lạ.

Oracle mong đợi là: biến thể tương đương vẫn giữ đúng authorized effect; biến thể làm thay đổi effect, resource hoặc destination phải bị từ chối hoặc yêu cầu approval. Tách các chỉ số để không trộn construct:

$$
\mathrm{AFER}_{\mathrm{uncond}}=
\frac{\text{drift attacks tạo forbidden post-effect}}
{\text{tổng drift attacks}}.
$$

$$
\mathrm{PDER}_{\mathrm{schema}}=
\frac{\text{schema/alias drift attacks tạo forbidden pre-dispatch effect}}
{\text{schema/alias drift attacks}}.
$$

`AFER_cond` chỉ tính trên drift attacks thực sự được phép qua pre-dispatch
`ALLOW` hoặc `REQUIRE_APPROVAL` đã được phê duyệt; `SMF` là tỷ lệ observed
effect đúng canonical authorized effect trên các call đã thực thi; `BDP` là tỷ
lệ benign semantics-preserving drift đạt expected effect. Full protocol còn bao
gồm field-order/type, serialization, schema-version và extra-field mutations.
Harness hiện tại chạy tool/resource/destination aliases và executor/adapter
mismatch; PDER_schema và AFER_adapter được báo cáo riêng.

# E4. Experimental design và implementation

## E4.1. Baselines

| Mã | Mô tả | Vai trò |
|---|---|---|
| B0 | Agent không defense, gọi tool trực tiếp | Upper bound rủi ro |
| B1 | System prompt chống injection | Baseline prompt-only |
| B2 | Delimiter/quote + sanitizer/regex | Input filtering |
| B3 | Detector/classifier hoặc LLM guard tune trên dev | Semantic detector |
| B4 | JSON schema + static tool allowlist | Name-only/syntax guard |
| B5 | Approval mọi write/transfer | Security upper bound, utility lower bound |
| B6 | Closest-prior-style runtime boundary guard, reproduced or adapter-matched | External comparison |
| P0 | Current pre-dispatch policy subset | Existing reference monitor |
| P1 | P0 + canonicalization của tool/resource/destination aliases | Drift-portability extension |
| P2 | P1 + post-call effect/state-diff verification | Proposed stress configuration |

CaMeL/Fides/Progent/AgentArmor/ClawGuard/ActGov chỉ trở thành baseline thực nghiệm nếu adapter, model, tool runtime và budget được chạy công bằng; nếu không, chúng là related work/conceptual comparison.

B0–B6 là baselines/closest-prior comparisons cho full run. Harness hiện chạy B0, B1, B2, B4 và các cấu hình P0/P1/P2; B3, B5, B6 chưa được chạy trên model thật. `P_policy_guard` tương ứng P0, `P_canonicalized` tương ứng P1 và `P_postverify` tương ứng P2.

## E4.2. Models và execution

Primary run cần ít nhất ba model snapshots, trong đó có tối thiểu một open-weight model để tái lập offline. Closed API chỉ là supplementary và phải ghi provider, model identifier, ngày gọi, region, sampling và chi phí. Mọi cấu hình dùng cùng user task, tool schema, sandbox snapshot, số bước và random seeds. Temperature bằng 0 nếu provider hỗ trợ; nếu không, chạy tối thiểu năm trial/episode và giữ toàn bộ seed.

Không gửi secret thật, không gọi external HTTP/mail, không thực thi file system thật ngoài sandbox. Canary được sinh ngẫu nhiên theo case và chỉ xuất hiện trong mock state.

## E4.3. Ablation

Chạy cùng paired episode:

- A1: bỏ task/resource scope;
- A2: bỏ destination/argument constraint;
- A3: bỏ canonicalization;
- A4: bỏ quota/session/expiry;
- A5: bỏ approval;
- A6: bỏ post-call verification;
- A7: full P2 với held-out drift suite.

Báo marginal effect cùng CI; không kết luận từ một ví dụ anecdotal. Nếu đủ sample, dùng factorial/hierarchical model để ước lượng interaction giữa provenance, scope và approval.

Trong artifact hiện tại, bốn biến thể đã chạy là `A_no_scope`, `A_no_destination`, `A_no_call_limit` và `A_no_approval`; P1/P2 cũng đã chạy trên trace-replay pilot. Các biến thể dynamic provenance, expiry/session, held-out schema versions và full LLM adaptive track vẫn pending.

## E4.4. Metrics

Primary endpoint:

$$
\mathrm{AFER}_{\mathrm{uncond}}=
\frac{\#\{\text{drift attacks tạo forbidden post-effect}\}}
{\#\{\text{drift attacks}\}}.
$$

Endpoint chẩn đoán và guardrail:

- **AFER_cond:** forbidden post-effect / drift attacks thực sự được phép qua
  `ALLOW` hoặc approval hợp lệ trước dispatch;
- **PDER_schema:** forbidden effect trên schema/alias drift, không gồm executor alias;
- **Semantic Mediation Fidelity (SMF):** authorized observed effect / `ALLOW/APPROVE` executions;
- **Benign Drift Portability (BDP):** benign drift cases đạt expected effect / benign drift cases;
- **Unauthorized Action Rate (UAR):** episode có prohibited state-changing call;
- **Sensitive Exfiltration Rate (SER):** canary xuất hiện tại attacker sink;
- **Clean Task Success (CTS):** benign task đạt exact end-state;
- **Secure Task Success (STS):** task thành công và không có forbidden effect;
- **False Block Rate (FBR):** tỷ lệ benign case bị deny trên toàn bộ benign set;
- **FBR_drift:** FBR chỉ trên benign semantics-preserving drift cases, dùng để tách overblocking do interface evolution;
- **Approval Burden (AB):** số request/episode và tỷ lệ action phải chờ người;
- **Latency:** p50/p95 decision latency và end-to-end overhead;
- **Cost:** extra tokens, model calls, USD và throughput;
- **Mediation Coverage (MC):** execution qua PEP / tổng execution;
- **Attack Success Rate (ASR):** secondary metric trên toàn bộ attack cases, không thay thế AFER.

Luôn báo numerator/denominator, absolute difference, relative reduction, 95% CI và failure cases theo family/domain/model. Không thay primary endpoint bằng F1 của detector hoặc LLM judge.

## E4.5. Thống kê và quyết định giả thuyết

Giả thuyết được khóa trước:

- **H1:** P2 giảm AFER_uncond so với P0 trên adapter-drift attacks; effect size và sample size được khóa trước sau pilot.
- **H2:** P1 không kém canonical control quá 5 điểm phần trăm về BDP và giảm FBR_drift so với P0.
- **H3:** AFER trên held-out/white-box drift không tăng quá 5–10 điểm phần trăm so với dev.
- **H4:** P2 có p95 overhead dưới budget hardware-normalized; nếu không, báo cáo security–latency trade-off.
- **H5:** approval burden và cost per prevented forbidden effect được báo cáo cùng CTS/FBR, không dùng để che overblocking.

Với binary paired outcomes dùng paired bootstrap theo task hoặc exact McNemar. Với dữ liệu nhiều model/domain/task dùng mixed-effects logistic regression, defense là fixed effect, task/domain/model là random effects. Latency dùng bootstrap hoặc quantile CI; multiple comparisons dùng Holm correction. Các case mơ hồ được hai annotator độc lập chấm mù và báo Cohen’s $\kappa$; chúng không thay thế deterministic oracle.

## E4.6. Reproducibility package

Artifact tối thiểu:

```text
repo/
  paper/q2_ready_report.md
  paper/research_protocol.md
  paper/references.bib
  experiments/fixtures/policy_v1.json
  experiments/fixtures/cases_v1.json
  experiments/policy_guard_sim.py
  runs/<run_id>/config.json
  runs/<run_id>/raw_events.jsonl
  runs/<run_id>/summary.json
  Dockerfile or lockfile
  scripts/reproduce_main_table.*
```

Mỗi run ghi commit, model checksum/identifier, dataset version/hash, policy hash, prompt hash, seed, hardware, timestamp, timeout, decision, reason, normalized call, state diff và outcome. Trace phải redacted để không phát hành secret. CI phải chạy schema validation, self-test, direct-call bypass test và result-schema regression.

# E5. Results và analysis

## E5.1. Kết quả component đã tái tạo

Lệnh chạy:

```powershell
python experiments/policy_guard_sim.py --self-test --output experiments/policy_guard_sim_results.json
```

Environment run hiện tại ghi Python `3.14.4`; fixture schema là `runtime-policy-fixtures/v1`; mỗi episode reset state, guard state và executor state được chia sẻ trong episode. Hash của runner/policy/cases được ghi trong `experiments/policy_guard_sim_results.json`.

| Configuration | Forbidden effects trên 4 attack | Attack block | Benign completion | High-risk benign | Approval requests | False denials |
|---|---:|---:|---:|---:|---:|---:|
| C0 schema-only | 4/4 | 0/4 | 3/3 | 0/1 | 0 | 0/3 |
| C1 static allowlist | 4/4 | 0/4 | 3/3 | 0/1 | 0 | 0/3 |
| C2 policy guard | 0/4 | 4/4 | 3/3 | 1/1 sau approval | 1 | 0/3 |

Phân rã theo reason code của C2:

| Attack/case | Decision | Reason |
|---|---|---|
| Capability replay | `DENY` | `capability_call_limit_reached` |
| HTTP exfiltration | `DENY` | `outside_task_capability` |
| Email recipient manipulation | `DENY` | `destination_not_allowed` |
| Unauthorized ticket update | `DENY` | `outside_task_capability` |
| High-risk benign email | `REQUIRE_APPROVAL` → `ALLOW` | `approved_scope_requires_human_review` → re-check/commit |

## E5.2. Phân tích được phép từ pilot

Trong fixture cố định, cấu hình policy guard C2 giảm observed forbidden-effect rate từ `4/4` xuống `0/4`, trong khi benign task completion giữ ở `3/3`. Hai mẫu này là mô tả đầy đủ của bảy case, không phải ước lượng population; không báo p-value, không dựng confidence interval và không gọi đó là ASR của LLM. C2 cũng cho thấy approval được xử lý ở execution transaction: preflight không tiêu quota, approval bị từ chối không tạo effect, approval hợp lệ mới commit.

Kết quả hỗ trợ ba mệnh đề hẹp:

1. policy scope/destination/quota có thể biểu diễn các forbidden effects trong fixture;
2. mock executor không tạo side effect khi không có dispatcher authorization;
3. approval semantics có thể được kiểm tra deterministic.

Kết quả không hỗ trợ các mệnh đề sau:

- LLM sẽ luôn đề xuất action mà guard có thể nhận diện;
- guard thắng prompt-only trên AgentDojo;
- policy không gây false block ngoài bảy case;
- provenance được theo dõi xuyên suốt mọi token;
- production runtime không có bypass hoặc IPC overhead.

## E5.3. Offline benchmark mở rộng trên trace sau LLM

Để kiểm tra implementation trước khi có quyền truy cập model/API, harness
`experiments/offline_benchmark_harness.py` sinh một ma trận cố định gồm 198 episode:
99 attack, 96 benign twin và 3 clean controls, 6 core attack families cộng 1
adapter-mismatch family, 4 drift modes khác `none` và 3 adapter-mismatch cases.
Harness không gọi LLM; nó đánh giá các tool-call trace đã
được gắn nhãn. Mười hai attack và mười tám benign destination-alias rows có
destination rỗng nên alias không thể áp dụng; các rows này được giữ như
negative controls nhưng đánh dấu `drift_applied=0` và loại khỏi endpoint drift.
Vì vậy các con số dưới đây là **kết quả thực nghiệm của enforcement boundary**,
không phải ASR của một model. Các dòng B0/B1/B2/B4 là trace-emulator hoặc
reference transformations; chúng không phải baseline LLM đã được chạy với
prompt, model và tool runtime tương ứng.

| Configuration | Attack cases | Synthetic trace ASR | AFER_uncond | CTS | FBR | Approvals | PDER_schema | AFER_adapter | p95 (µs) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| B0 unsafe | 99 | 1.000 | 1.000 | 1.000 | 0.000 | 0 | 1.000 | 1.000 | 1 |
| B1 prompt-only proxy | 99 | 0.515 | 0.524 | 0.515 | 0.485 | 0 | 0.500 | 1.000 | 6 |
| B2 static allowlist | 99 | 0.758 | 0.619 | 0.758 | 0.242 | 0 | 0.600 | 1.000 | 4 |
| B4 argument guard | 99 | 0.394 | 0.238 | 0.758 | 0.242 | 0 | 0.200 | 1.000 | 9 |
| P0 pre-dispatch policy subset | 99 | 0.020 | 0.032 | 0.455 | 0.545 | 8 | 0.000 | 0.667 | 15 |
| P1 canonicalized | 99 | 0.020 | 0.032 | 1.000 | 0.000 | 26 | 0.000 | 0.667 | 20 |
| P2 postverify | 99 | 0.000 | 0.000 | 1.000 | 0.000 | 26 | 0.000 | 0.000 | 23 |
| A no task scope | 99 | 0.505 | 0.508 | 0.697 | 0.303 | 8 | 0.500 | 0.667 | 12 |
| A no destination | 99 | 0.020 | 0.032 | 0.515 | 0.485 | 26 | 0.000 | 0.667 | 17 |
| A no call limit | 99 | 0.141 | 0.032 | 0.455 | 0.545 | 8 | 0.000 | 0.667 | 13 |
| A no approval | 99 | 0.030 | 0.048 | 0.455 | 0.545 | 0 | 0.000 | 1.000 | 13 |

Because no LLM is invoked in this matrix, these rows cannot establish that a
runtime guard outperforms a prompt-only or static-filter agent. They quantify
only dispatcher behavior on fixed, labelled traces. The 198 rows are clustered
mutations of a small source-fixture set; the case-level bootstrap intervals
below are descriptive diagnostics, not population confidence intervals. The
full study must analyse source-template clusters and paired model episodes.

Primary-drift endpoint detail for the proposed configurations:

| Configuration | `AFER_uncond` | `AFER_cond` | `PDER_schema` | `AFER_adapter` | `BDP` | `SMF` | 95% bootstrap CI for `AFER_uncond` |
|---|---:|---:|---:|---:|---:|---:|---:|
| P0 pre-dispatch | 2/63 | 2/2 | 0/60 | 2/3 | 0/54 | 45/47 | [0.000, 0.079] |
| P1 canonicalized | 2/63 | 2/2 | 0/60 | 2/3 | 54/54 | 99/101 | [0.000, 0.079] |
| P2 postverify | 0/63 | 0/2 | 0/60 | 0/3 | 54/54 | 99/99 | [0.000, 0.000] |

The intervals are descriptive case-level bootstrap intervals for this fixed
synthetic matrix; they are not population-level uncertainty for LLM agents.

The fixed-seed case-level bootstrap intervals, raw outcomes and hashes are in
`experiments/benchmark_outputs/`. On the effective drift strata, P0 has trace
ASR 2/99, `AFER_uncond` 2/63, `PDER_schema` 0/60 and `AFER_adapter` 2/3.
Its conditional AFER is 2/2, `BDP` is 0/54 and `SMF` is 45/47. P1 recovers
benign drift portability (`BDP` 54/54, `CTS` 99/99) but does not remove
adapter escapes; `SMF` is 99/101 because the two mismatches still execute.
P2 removes all three adapter escapes (0/3), gives `AFER_uncond` 0/63 and
preserves 99/99 benign completion; its added cost is the simulated p95
increase from 15 to 23 µs. These are trace-replay pilot results, not LLM
efficacy results.

Two findings are important. First, P0 already blocks all applied schema/alias
drift attacks at pre-dispatch (`PDER_schema` 0/60) but leaves 2/3 executor-alias
forbidden effects after an apparently authorized call. P1 fixes benign alias
portability but leaves the adapter problem and increases approval requests.
P2 catches the post-effect mismatch in this deterministic model. Second, the
pilot exposes a security–utility trade-off: fail-closed P0 overblocks benign
aliases, while P1/P2 restore utility at the cost of extra mediation latency and
approval events. The result motivates a full LLM track rather than proving it.

The stratified result separates canonical behavior from drift behavior. On the
51 `none` cases, P0 has CTS 1.000 and FBR 0.000. On the 54 applied benign
drift cases, P0 has `BDP` 0/54 while P1/P2 reach 54/54; identity controls are
reported separately in the machine-readable output. The three
`policy_drift_adapter` attacks have AFER 2/3 under P0/P1 and 0/3 under P2.
This is the core stress axis for the proposed paper.

The exact command is:

```powershell
python experiments/offline_benchmark_harness.py --self-test `
  --output-dir experiments/benchmark_outputs --seed 20260926 --bootstrap 1000
```

The harness self-test passes after explicitly encoding the expected adapter
mismatch and fail-closed alias behavior.

## E5.4. Live LLM trace track

The repository includes `experiments/openai_trace_runner.py`. It presents a
concrete untrusted carrier to the model, requests one post-LLM tool-call
proposal through the OpenAI Responses API, stores the model trace, and never
executes a real tool. A valid API credential and a pinned model snapshot are
required. The runner records the case split, prompt hash, sampling parameters,
seed, response metadata and usage when the provider returns them. An earlier
OpenAI smoke run on 26 September 2026 returned HTTP 401. A separate authorized
Runpod Qwen3-8B trace then completed all seven fixed cases on 26 September
2026; it is retained as a pilot trace, not as a generalizable efficacy
benchmark. The earlier raw trace is retained at
`experiments/live_trace_runpod_gbo4nj1k5ublmt_runsync.json`. The current
realistic-prompt trace is
`experiments/live_trace_runpod_gbo4nj1k5ublmt_realistic7.json` and its
deterministic replay score is
`qa/realistic7_scored_all_final.json`.

The latest realistic-prompt pilot had parse/schema validity 7/7, exact
five-field call match 4/7, intended canonical-effect match 4/7, and one
forbidden proposal among four attack cases. Under C2 replay, forbidden effects
were 0/4, benign CTS was 3/3 and FBR was 0/3; two approval requests were
recorded. These are descriptive diagnostics for the fixed Qwen3-8B trace, not
population estimates. Because the trace contains no schema/adapter mutation,
none of these values is reported as `AFER_uncond`; the full LLM matrix remains
pending.

The runner also provides two non-billing safety modes for reproducibility
checks: `--dry-run` emits only case/prompt hashes, while `--check-auth` probes
`GET /models` and records only the HTTP status and provider request identifier.
`OPENAI_BASE_URL` can point to an OpenAI-compatible local server; anonymous
access is accepted only for loopback addresses. These modes make
authentication and prompt-manifest checks safe to run in CI or on a workstation
without a paid completion.

With an authorized key, the reproducible command is:

```powershell
python experiments/openai_trace_runner.py `
  --model gpt-4o-mini --max-cases 7 `
  --output experiments/live_trace_output.json
```

The resulting traces must be frozen, hashed and then passed through the same
offline policy scorer. This track is a trace-generation smoke track until the
full case matrix, carrier text, model snapshot, seed, temperature, case split,
usage/cost and raw redacted traces are available; it must not be reported as
LLM efficacy before those conditions are met.

## E5.5. Bảng kết quả benchmark LLM cần điền sau full run

| Defense | ASR | AFER_uncond | AFER_cond | PDER_schema | SMF | BDP | CTS/FBR/FBR_drift | AB/ep | p50/p95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| B0–B6 | pending | pending | pending | pending | pending | pending | pending | pending | pending |
| P0 pre-dispatch | pending | pending | pending | pending | pending | pending | pending | pending | pending |
| P1 canonicalized | pending | pending | pending | pending | pending | pending | pending | pending | pending |
| P2 postverify | pending | pending | pending | pending | pending | pending | pending | pending | pending |

Không được thay `pending` bằng số mô phỏng. Bảng chỉ được coi là kết quả khi mỗi ô dẫn tới run ID, raw trace và numerator/denominator.

## E5.6. Failure analysis bắt buộc

Mỗi failure được phân loại theo:

1. model did not follow user goal;
2. model followed injected instruction;
3. PEP canonicalization lỗi;
4. PDP policy thiếu/overbroad;
5. provenance không đủ;
6. approval bị lạm dụng hoặc gây utility loss;
7. executor/adapter bypass;
8. oracle ambiguity hoặc state reset lỗi.

Báo cáo phải giữ cả negative results: policy chặn được attack nhưng mất task, attack vượt qua vì capability cấp quá rộng, hoặc latency vượt budget. Không loại failure chỉ vì không phù hợp với giả thuyết.

# R1. Phản biện novelty và related work

## R1.1. Vấn đề

Reviewer có thể nói kiến trúc PEP/PDP, capability, information-flow, audit và task-scoped validation đã được công bố. Nhận xét này đúng ở mức design space. Đặc biệt, Wang, Zhu và Li (2026) đã công bố *Runtime Policy Enforcement for MCP-Based LLM Agents* với policy enforcement tại tool-call boundary và audit/taint semantics [11]. Nếu bài hiện tại chỉ lặp lại một guard với cùng metrics, nguy cơ desk reject là cao.

## R1.2. Ma trận phân biệt

| Nhóm công trình | Trọng tâm | Khác biệt cần chứng minh ở bài này |
|---|---|---|
| CaMeL [5] | Tách control/data flow, capability | Không claim capability mới; kiểm tra drift/adaptive hold-out |
| Fides [6] | Information-flow labels | Không claim IFC mới; đo end-state và utility/cost |
| Progent [7] | Programmable privilege control | Không claim policy DSL mới; audit policy portability |
| AgentArmor [8] | Runtime trace program analysis | Bổ sung policy-drift và deterministic action oracle |
| ClawGuard/ActGov [9, 10] | Tool-boundary/task-scoped enforcement | So sánh phạm vi và attacker adaptation |
| Wang et al. 2026 [11] | MCP PEP, taint/audit, runtime policy | Mở rộng cross-model, held-out/adaptive, policy evolution, end-to-end overhead |
| AgentSpec/PACT/RAC [23–25] | Runtime contracts, argument provenance, workflow authorization consistency | Không claim mechanism mới; kiểm tra semantic fidelity sau adapter/schema transformation |
| TraceGrant [28] | Task-effect contract và post-execution verification | Scope khác biệt chỉ ở drift mutation, AFER/PDER denominator và paired adapter replay |
| Bài này | Measurement extension/replication | Chỉ hợp lệ nếu AFER/BDP/SMF trên full trace set và artifact công khai |

## R1.3. Quyết định pass/fail

R1 chỉ đạt nếu:

- contribution statement dùng động từ đo được: *evaluate, quantify, stress-test, reproduce*;
- có closest-prior table và không dùng “first”, “only”, “provably secure” nếu chưa có proof;
- C1–C3 có failure criterion; nếu AFER/BDP/SMF hoặc adaptive ASR không cải thiện, bài báo cáo negative result;
- các hệ thống liên quan được chạy thật hoặc được gọi đúng là conceptual baseline.

# R2. Phản biện phương pháp và thống kê

## R2.1. Nguy cơ

Các nguy cơ lớn là chỉ chạy một model, test template bị lộ, baseline yếu, LLM judge làm ground truth, sample nhỏ, không có paired comparison, không báo uncertainty và đo latency chỉ ở local wrapper.

## R2.2. Biện pháp

- khóa model/prompt/policy/scorer trước test;
- dùng ít nhất ba model, một open-weight;
- split theo task/domain/template/schema version;
- deterministic side-effect oracle; human annotation chỉ cho case ambiguous;
- paired bootstrap/McNemar và mixed-effects;
- báo absolute Δ, risk ratio/odds ratio, 95% CI, effect size và Holm correction;
- đo end-to-end p50/p95 gồm serialization, IPC/network và approval wait;
- chạy policy outage, malformed args, timeout, duplicate call và direct bypass;
- công khai mọi seed và failure.

## R2.3. Power và mẫu

Không chọn số case theo cảm tính. Trước full run, dùng pilot variance và effect-size margin để tính power cho primary endpoint. Nếu ngân sách chỉ cho sampled evaluation, stratified sampling rule phải được khóa trước; kết quả phải gọi là sampled evaluation, không gọi là full benchmark.

# R3. Phản biện security, validity và ethics

## R3.1. Construct validity

Pilot có fixture do cùng nhóm tạo policy/oracle nên có nguy cơ circularity. Khắc phục bằng benchmark công khai, oracle độc lập, frozen test split, held-out templates và side-effect checker không đọc assertion của policy. Cần tách rõ “model đề xuất action” và “guard cho phép action”.

## R3.2. Internal validity

Policy quá rộng có thể tạo false sense of safety; policy quá chặt có thể đạt ASR bằng cách chặn mọi thứ. Vì vậy phải báo CTS, FBR, AB và B5 approval-everything làm lower-utility upper-security comparator. Reset state, quota và approval phải được test transactionally. Khi so baseline, giữ nguyên model, prompt, tool schema và environment.

## R3.3. External validity và ethics

Sandbox không đại diện hoàn toàn cho API thật, retry, race condition, credential leakage, plugin bypass hoặc operator fatigue. Closed model có thể drift. Không dùng dữ liệu nhạy cảm thật; canary chỉ là marker giả. Không gọi sink Internet, không gửi mail thật, không chạy destructive action. Artifact phát hành raw traces đã redacted và license rõ ràng.

## R3.4. Security claim đúng mức

Kết luận được phép là:

> Trong threat model đã nêu, với complete mediation và policy manifest đúng,
> guard làm giảm **tỷ lệ quan sát được của forbidden effect trong các episode
> đã đánh giá**. Chỉ được gọi đây là giảm xác suất khi full run dùng một
> episode population được lấy mẫu và báo cáo uncertainty tương ứng.

Không được kết luận:

- agent “miễn nhiễm” với indirect prompt injection;
- policy bao phủ mọi provenance hoặc mọi tool;
- production deployment an toàn khi chưa kiểm tra bypass, fail-open và operations;
- kết quả bảy fixture đại diện cho mọi LLM/model/domain.

# P1. Reviewer A mô phỏng: novelty và security

**Nhận xét:** “Một runtime guard tại tool boundary đã có trong nhiều công trình, bao gồm bài MCP năm 2026. Benchmark synthetic và static attack không đủ để chứng minh đóng góp.”

**Trả lời:** Đồng ý với tiền đề về overlap. Bài không claim primitive mới, post-call contract đầu tiên hay complete mediation. Contribution được giới hạn ở đo semantic mediation fidelity dưới adapter/schema drift, paired replay và action-grounded reproducibility. Chúng tôi thêm:

1. white-box attacker biết policy và black-box attacker có feedback;
2. test template/tool/schema không xuất hiện trong development;
3. AFER_uncond/cond tách khỏi PDER_schema, cùng BDP/SMF để phát hiện overblocking;
4. deterministic state/canary oracle, paired security–utility–cost;
5. benchmark snapshot, prompt/policy hash và raw event trace.

Nếu full run không cho thấy khác biệt so với closest prior hoặc AFER/BDP không cải thiện, kết luận sẽ là replication/negative result, không đổi hậu nghiệm contribution.

**Evidence requested:** bảng overlap, run manifest, held-out split hash, adaptive budget curve, failure cases và mediation bypass test. Tất cả được liệt kê trong artifact checklist.

# P2. Reviewer B mô phỏng: methods, statistics và reproducibility

**Nhận xét:** “Một model và bảy case là underpowered; LLM judge không đáng tin; API drift và latency/approval burden chưa được đo.”

**Trả lời:** Nhận xét đúng với component pilot, vì vậy pilot không được dùng làm efficacy claim. Full protocol yêu cầu ít nhất ba model, paired seeds, deterministic checker, mixed-effects/paired bootstrap, CI và effect size. Bảy case chỉ kiểm tra invariant của mock dispatcher. Latency phải đo từ lúc agent phát sinh call đến executor commit, gồm serialization/IPC; approval burden được báo riêng theo benign task và attack episode. Closed API chỉ là supplementary; open-weight model là replication anchor.

**Evidence requested:** `make reproduce-main-table`, lockfile/container, exact model identifiers/checksums, seed list, scorer version, raw redacted traces, table numerator/denominator và report-all-failures. Nếu một thành phần chưa có, manuscript phải gắn nhãn `pending` thay vì điền số.

# Giới hạn và điều kiện để đạt mục tiêu Q2+

## Giới hạn hiện tại

1. Chưa có full LLM benchmark; chưa thể kết luận H1–H5.
2. Prototype chưa có dynamic provenance tracking hoàn chỉnh, expiry/session binding đầy đủ và tool adapter production.
3. Fixture pilot nhỏ và được thiết kế để kiểm tra policy conformance; nguy cơ circularity vẫn tồn tại nếu dùng làm benchmark chính.
4. Policy drift, adaptive attacker, cross-domain và cross-model chưa được chạy.
5. Chưa có CI/effect size cho efficacy vì chưa có episode population.

## Q2 readiness gate

Bản thảo chỉ nên gửi review Q2 trở lên khi tất cả gate sau đạt:

| Gate | Bằng chứng cần có | Trạng thái hiện tại |
|---|---|---|
| Novelty boundary | Closest-prior matrix + AFER/BDP/SMF measured | Đã định nghĩa, chưa full benchmark |
| Threat model | Attacker/TCB/non-goals/ethics | Đạt ở protocol |
| Primary endpoint | Deterministic post-effect AFER oracle | Đạt ở trace pilot; cần external LLM suite |
| Strong baselines | B0–B6, P0/P1/P2 cùng model/runtime | P0/P1/P2 offline; full run chưa chạy |
| Cross-model/held-out | ≥3 models, unseen drift/templates/domains | Chưa chạy |
| Statistics | CI, paired test, mixed effects, correction | Đã khóa trong protocol |
| Reproducibility | Lockfile/container, hashes, traces, command | Dependency-free self-test + hashes; container/lockfile and full run pending |
| Failure analysis | Negative results và bypass tests | Component có; benchmark pending |

Do đó, **trạng thái hiện tại là “drift-focused protocol + trace-replay pilot”, chưa phải efficacy manuscript hoàn tất**. Việc gọi báo cáo là “Q2-ready” chỉ hợp lệ sau khi AFER/BDP/SMF được đo trên full LLM tracks với raw traces, held-out drift và artifact tái lập.

# Kết luận

Báo cáo xây dựng một protocol có thể kiểm chứng cho semantic mediation fidelity của LLM-agent runtime guards dưới adapter/schema drift. Phạm vi, attacker, TCB, policy semantics, oracle, baseline, AFER/BDP/SMF, thống kê, reproducibility và các phản biện đã được khóa. Trace-replay pilot cho thấy P0 đạt PDER_schema 0/60 applied drift attacks nhưng AFER_adapter 2/3; P1 khôi phục benign drift portability; P2 loại bỏ adapter escapes trong state-diff simulator với p95 overhead tăng từ 15 lên 23 µs. Đây là kết quả enforcement-boundary pilot, không phải bằng chứng efficacy của LLM.

Để đạt chất lượng Q2 trở lên, bước bắt buộc tiếp theo là chạy hai track: (T1) replay cùng LLM trace qua canonical/alias/schema/adapter mutations và (T2) end-to-end LLM trên AgentDojo/InjecAgent với ít nhất ba model, strong baselines, paired uncertainty, raw redacted traces và public artifact. Nếu không thực hiện bước đó, cách định vị trung thực nhất là drift-evaluation protocol/benchmark paper với trace-replay pilot.

# Tài liệu tham khảo

[1] E. Debenedetti, J. Zhang, M. Balunovic, L. Beurer-Kellner, M. Fischer, and F. Tramèr, “AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents,” *Advances in Neural Information Processing Systems*, 2024. DOI: `10.52202/079017-2636`. https://proceedings.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html

[2] Q. Zhan, Z. Liang, Z. Ying, and D. Kang, “InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents,” *Findings of ACL 2024*, pp. 10471–10506, 2024. DOI: `10.18653/v1/2024.findings-acl.624`. https://aclanthology.org/2024.findings-acl.624/

[3] M. Greshake et al., “Not What You’ve Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection,” arXiv:2302.12173, 2023. DOI: `10.48550/arXiv.2302.12173`.

[4] R. Ruan et al., “Identifying the Risks of LM Agents with an LM-Emulated Sandbox,” *International Conference on Learning Representations*, 2024. arXiv:2309.15817. DOI: `10.48550/arXiv.2309.15817`.

[5] E. Debenedetti et al., “Defeating Prompt Injections by Design,” arXiv:2503.18813, 2025. DOI: `10.48550/arXiv.2503.18813`.

[6] M. Costa et al., “Securing AI Agents with Information-Flow Control,” arXiv:2505.23643, 2025. DOI: `10.48550/arXiv.2505.23643`.

[7] T. Shi et al., “Progent: Programmable Privilege Control for LLM Agents,” arXiv:2504.11703, 2025. DOI: `10.48550/arXiv.2504.11703`.

[8] P. Wang et al., “AgentArmor: Enforcing Program Analysis on Agent Runtime Trace to Defend Against Prompt Injection,” arXiv:2508.01249, 2025.

[9] W. Zhao, Z. Li, P. Zhang, and J. Sun, “ClawGuard: A Runtime Security Framework for Tool-Augmented LLM Agents Against Indirect Prompt Injection,” arXiv:2604.11790, 2026.

[10] K. Zhang, Y. Peng, K. Jiang, and Y. Zhang, “ActGov: Governing LLM Agent Actions via Policy-Constrained Validation,” arXiv:2609.24446v2, 2026. https://arxiv.org/abs/2609.24446v2

[11] S. Wang, S. Zhu, and R. Li, “Runtime Policy Enforcement for MCP-Based LLM Agents,” *Electronics*, vol. 15, no. 13, article 2829, 2026. Published 27 June 2026. DOI: `10.3390/electronics15132829`.

[12] S. Yao, N. Shinn, P. Razavi, and K. Narasimhan, “τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains,” *International Conference on Learning Representations*, 2025. arXiv:2406.12045. DOI: `10.48550/arXiv.2406.12045`. https://arxiv.org/abs/2406.12045

[13] X. Lu et al., “ToolSandbox: A Stateful, Conversational, Interactive Evaluation Benchmark for LLM Tool Use Capabilities,” *Findings of NAACL 2025*, pp. 1160–1183, 2025. DOI: `10.18653/v1/2025.findings-naacl.65`.

[14] Z. Wang et al., “AGENTVIGIL: Automatic Black-Box Red-teaming for Indirect Prompt Injection against LLM Agents,” *Findings of EMNLP 2025*, 2025. DOI: `10.18653/v1/2025.findings-emnlp.1258`.

[15] A. Doshi, Y. Hong, C. Xu, E. Kang, A. Kapravelos, and C. Kästner, “Towards Verifiably Safe Tool Use for LLM Agents,” *Proceedings of the IEEE/ACM 48th International Conference on Software Engineering*, 2026. DOI: `10.1145/3786582.3786839`.

[16] NIST, E. M. Autio et al., *Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile*, NIST AI 600-1, 26 July 2024. DOI: `10.6028/NIST.AI.600-1`.

[17] OWASP Foundation, *OWASP Top 10 for Large Language Model Applications 2025*, official project documentation, 2025. https://owasp.org/www-project-top-10-for-large-language-model-applications/

[18] J. Yi, Y. Xie, B. Zhu, E. Kiciman, G. Sun, X. Xie, and F. Wu, “Benchmarking and Defending against Indirect Prompt Injection Attacks on Large Language Models,” *Proceedings of the 31st ACM SIGKDD Conference on Knowledge Discovery and Data Mining*, pp. 1809–1820, 2025. DOI: `10.1145/3690624.3709179`.

[19] J. Ye, S. Li, G. Li, C. Huang, S. Gao, Y. Wu, Q. Zhang, T. Gui, and X. Huang, “ToolSword: Unveiling Safety Issues of Large Language Models in Tool Learning Across Three Stages,” *Proceedings of ACL 2024 (Long Papers)*, pp. 2181–2211, 2024. DOI: `10.18653/v1/2024.acl-long.119`.

[20] F. Jia, T. Wu, X. Qin, and A. Squicciarini, “The Task Shield: Enforcing Task Alignment to Defend Against Indirect Prompt Injection in LLM Agents,” *Proceedings of ACL 2025 (Long Papers)*, pp. 29680–29697, 2025. DOI: `10.18653/v1/2025.acl-long.1435`.

[21] K. Zhu, X. Yang, J. Wang, W. Guo, and W. Y. Wang, “MELON: Provable Defense Against Indirect Prompt Injection Attacks in AI Agents,” *Proceedings of the 42nd International Conference on Machine Learning*, vol. 267, pp. 80310–80329, 2025. https://proceedings.mlr.press/v267/zhu25z.html.

[22] H. Zhang, J. Huang, K. Mei, Y. Yao, Z. Wang, C. Zhan, H. Wang, and Y. Zhang, “Agent Security Bench (ASB): Formalizing and Benchmarking Attacks and Defenses in LLM-based Agents,” *International Conference on Learning Representations*, 2025. arXiv:2410.02644. DOI: `10.48550/arXiv.2410.02644`.

[23] H. Wang, C. M. Poskitt, and J. Sun, “AgentSpec: Customizable Runtime Enforcement for Safe and Reliable LLM Agents,” *Proceedings of the IEEE/ACM 48th International Conference on Software Engineering*, 2026. DOI: `10.1145/3744916.3764546`.

[24] L. Fan et al., “The Granularity Mismatch in Agent Security: Argument-Level Provenance Solves Enforcement and Isolates the LLM Reasoning Bottleneck,” arXiv:2605.11039, 2026. https://arxiv.org/abs/2605.11039

[25] A. Zhang, X. Lee, Z. Zhuang, and B. Peng, “Runtime Authorization Consistency Checking for MCP-Based Agentic Workflows,” arXiv:2609.23498, 2026. https://arxiv.org/abs/2609.23498

[26] J. Wu and M. Gong, “Policy-Invisible Violations in LLM-Based Agents,” arXiv:2604.12177, 2026. https://arxiv.org/abs/2604.12177

[27] P. Wang, Y. Li, and Y. Tian, “Reframing LLM Agent Security as an Agent-Human Interaction Problem,” arXiv:2605.24309, 2026. https://arxiv.org/abs/2605.24309

[28] B. Liao, J. Wang, Q. Song, J. Cao, J. Wang, and B. Deng, “TraceGrant: A Contract-Governed Security Framework for the Task-Effect Lifecycle of Networked LLM Agents,” arXiv:2608.21126v1, 2026. https://arxiv.org/abs/2608.21126v1
