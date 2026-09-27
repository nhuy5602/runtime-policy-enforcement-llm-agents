# Ma trận phản biện và kiểm định cho bản thảo

Tài liệu này diễn giải yêu cầu “5 phần thực thi, 3 phần phản biện, 2 phần phản biện”
thành mười gói công việc có thể kiểm tra. Cấu trúc bài báo chính vẫn nên theo
Abstract–Introduction–Related Work–Threat Model–Method–Results–Discussion–Limitations;
ma trận này dùng cho phần Discussion, phụ lục và quy trình kiểm soát chất lượng.

**Trạng thái bằng chứng hiện tại.** Có một paired AgentDojo integration smoke
với Qwen3-8B qua Runpod; hai target trace đều có `utility=true`,
`security=false`, không gọi `send_email`, và không có adapter drift. Vì vậy nó
chỉ chứng minh đường chạy benchmark/proxy tạo được trace; nó **không** là
live-model efficacy run, không cho effect size và không cho phép đánh giá
defense. Artifact chính vẫn chỉ chứng minh component conformance và
trace-level enforcement trên các case offline đã khóa.

## Năm phần thực thi

| Gói | Nội dung bắt buộc | Bằng chứng đầu ra |
|---|---|---|
| E1 | Literature/contribution gate; đối chiếu CaMeL, Fides, Progent, AgentArmor, ClawGuard, ActGov, AgentDojo và InjecAgent | Bảng closest-prior, claim có thể đo, quyết định không dùng “first/novel” nếu chưa chứng minh |
| E2 | Threat model và policy semantics | Attacker capabilities, trusted computing base, non-goals, schema policy, default-deny, reason code, security/utility oracle độc lập |
| E3 | Benchmark và protocol | Version/commit, model/provider, prompt, schema, locked split, mutation suite, seed, initial-state hash, forbidden-end-state predicate |
| E4 | Runtime guard và instrumentation | Complete mediation test, canonicalization, expiry/session binding, approval transaction, audit trace, state diff, fail-closed behavior |
| E5 | Thực nghiệm và phân tích | Component/trace pilot và một paired integration smoke đã chạy; B3/B5, attack-positive drift pairs và các ablation còn lại pending; security–utility–overhead, CIs/effect sizes, failure cases, artifact/reproduction package |

## Ba phản biện nội bộ

| Review | Câu hỏi khó | Bằng chứng cần yêu cầu | Điều kiện đạt |
|---|---|---|---|
| R1 — Novelty/positioning | Đề tài khác gì so với runtime guard, capability và IFC đã công bố? | Ma trận closest prior; mỗi đóng góp có endpoint và failure criterion | Không còn claim trùng lặp; nếu chưa có contribution riêng thì gọi là replication/reference implementation |
| R2 — Methods/statistics | Baseline, oracle, mẫu, phép kiểm định và seed có công bằng, đủ mạnh và định trước không? | Locked test; numerator/denominator; power hoặc precision analysis; paired bootstrap/McNemar; mixed-effects khi có nhiều model/task | Không đổi policy sau khi xem test; báo 95% CI, effect size và correction multiple testing |
| R3 — Security/validity | Có đường bypass, circular oracle, overblocking, rò rỉ dữ liệu hay overclaim không? | Threat-to-validity table; direct-call bypass test; sandbox/canary; failure taxonomy; ethics/data card | Không gọi fixture là benchmark LLM; claims chỉ nằm trong threat model và evidence đã đo |

Mỗi phản biện phải ghi theo chuỗi **threat → evidence → mitigation → residual limitation**,
không chỉ nêu nhận xét định tính.

## Hai phản biện mô phỏng và rebuttal

### Reviewer A — Security và novelty

**Objection.** “Policy gate tại tool boundary và task-scoped authorization đã có trong
related work; benchmark tĩnh hoặc attack do tác giả tự viết chưa đủ để chứng minh đóng góp.”

**Revision/rebuttal.**

1. Đưa bảng so sánh capability, IFC, trace analysis, action validation, policy drift và
   domain/attack coverage với closest prior.
2. Nếu contribution chỉ là đánh giá, đổi ngôn ngữ thành *independent, reproducible
   evaluation/replication*; không tuyên bố cơ chế mới.
3. Chạy adaptive white-box và black-box attacker, mutation held-out, cross-domain và
   cross-model; giữ một test split không dùng để sửa policy.
4. Phân biệt rõ action-grounded ASR với việc LLM có bị ảnh hưởng về văn bản; policy gate
   chỉ ngăn side effect sau khi tool call được đề xuất.
5. Báo cả bypass/failure, capability quá rộng và trường hợp policy từ chối nhầm.

### Reviewer B — Phương pháp, thống kê và tái lập

**Objection.** “Một model, một API snapshot, LLM-as-judge và latency của wrapper không
đủ; kết quả không tái lập được và chưa đo burden của human approval.”

**Revision/rebuttal.**

1. Dùng deterministic side-effect oracle; nếu cần đánh giá ngôn ngữ, chỉ dùng human
   audit mù trên một mẫu và không dùng làm ground truth chính.
2. Có ít nhất một open-weight model và nhiều model/config; khóa model/version, prompt,
   tool schema, temperature, max steps, seed và manifest.
3. Dùng paired episodes, bootstrap hoặc McNemar cho binary outcome; mixed-effects
   logistic model theo model/task/attack family khi có nhiều tầng; báo CI và effect size.
4. Đo end-to-end p50/p95 gồm serialization/IPC/network, token/$, throughput, retries,
   approval requests và fail-open/fail-closed.
5. Công bố code, fixture, policy, scorer, raw redacted logs, container/lockfile và một
   lệnh chạy sạch từ đầu. Hiện repository mới có self-test dependency-free và hashes;
   container/lockfile cùng full live run vẫn là gate chưa đạt.

## Scorecard “Q2-ready” nội bộ

Chấm 100 điểm, chỉ dùng làm cổng chất lượng nội bộ (không phải dự đoán quartile):

| Hạng mục | Điểm |
|---|---:|
| Novelty/positioning có bằng chứng | 20 |
| Threat model, policy semantics, ethics | 15 |
| Method và reproducibility | 20 |
| Statistics và experimental coverage | 20 |
| Results/failure analysis/limitations | 15 |
| Clarity và artifact quality | 10 |
| **Tổng** | **100** |

Không pass nếu thiếu bất kỳ cổng bắt buộc nào: deterministic oracle, baseline mạnh và
công bằng, locked test, 95% CI/effect size, hoặc artifact có thể tái chạy. Điểm tổng
khuyến nghị tối thiểu là 80/100 trước khi gửi phản biện ngoài.
