# Phiếu chặn/cho phép pilot Runpod có ngân sách — 27 September 2026

## Trạng thái và phạm vi

**Trạng thái hiện tại: NO-GO; chưa gửi job tính phí trong round này.** Người
dùng đã cấp mức ngân sách tối đa **USD 10.00** cho Runpod. Mức này chỉ là một
giới hạn tài chính do người dùng đặt, **không** phải là một kết quả benchmark,
và cũng không phải là một trần chi tiêu được Runpod áp ở cấp từng job trong
runner hiện tại.

Nếu được mở khóa, đây chỉ là **pilot khả thi có đăng ký trước**: kiểm tra liệu
một cặp AgentDojo đã pin có thể tạo trace baseline/guard đầy đủ, có oracle và
được lưu lại hay không. Pilot không được dùng để ước lượng ASR/AFER, lập CI hay
kiểm định thống kê, tuyên bố hiệu quả/superiority của defense, chọn policy sau
khi xem kết quả, hay thay thế benchmark độc lập nhiều-model cần cho bài báo.
Bảng claim gate vẫn là nguồn quyết định:
[`q2_claim_gate_review.md`](q2_claim_gate_review.md).

## Preflight trực tiếp (read-only)

Ngày 27 September 2026, Runpod MCP đã trả về snapshot sau. Các giá trị trong
bảng là dữ kiện vận hành tại thời điểm đọc, không phải lời hứa về chi phí hoặc
tình trạng ở lần chạy sau.

| Trường | Dữ kiện quan sát được | Nguồn đọc |
|---|---|---|
| Endpoint được đề xuất | `h5ec6v08cb8uc2` — `q2-agentdojo-toolcalling-hub-20260926` | `get-endpoint` |
| Runtime | serverless `QUEUE`; `qwen/qwen3-8b`; image `registry.runpod.net/runpod-workers-worker-vllm-main-dockerfile:16d63772e` | `get-endpoint` |
| Phần cứng/cấu hình | 1 GPU, pool `AMPERE_80`, CUDA `13.0`, `workers.min=0`, `workers.max=1`, endpoint timeout `1800000` ms | `get-endpoint` |
| Worker/queue | một worker `9p3zguw2bjm9lc`, `IDLE`, tại `US-MD-1` trên `NVIDIA A100-SXM4-80GB`; health: 45 completed, 0 failed, 0 in-progress, 0 queued | `list-endpoint-workers`, `endpoint-health` |
| Giá và capacity hiện thời | A100 SXM 80GB serverless: **USD 2.72/GPU-hour**; availability `HIGH`; `US-MD-1` availability `MEDIUM` | `get-gpu-type` với `SERVERLESS`, CUDA `13.0` |
| Billing endpoint gần nhất | bucket 26 September: GPU `0.44334941875422373`, disk `0.0069444444961845875`, total **USD 0.4502938632504083** | `list-serverless-billing` |
| Billing toàn tài khoản gần nhất | bucket 26 September: GPU serverless `1.0794187861611135`, disk serverless `0.01736111124046147`, total **USD 1.096779897401575** | `list-billing` |
| Billing của bucket 27 September tại thời điểm đọc | không có record; tổng trả về `0` | `list-billing`, `list-serverless-billing` |

Do tổng của endpoint trong bucket cũ gộp các job và disk, còn health chỉ là
một tổng số 45 job, không được chia hai số này để suy ra giá mỗi episode. Giá
thực tế của một AgentDojo episode còn phụ thuộc số vòng tool/LLM, thời gian
cold-start và thời lượng worker; không có số đo trước nào ở đây đủ để dự báo
chi phí một cách hợp lệ.

## Những điều phải khóa trước một job billable

1. **Tài nguyên và quyền chi:** người dùng cần xác nhận rõ đúng endpoint
   `h5ec6v08cb8uc2` với giới hạn tổng USD 10.00. Không tạo endpoint, thay đổi
   worker, hay dùng endpoint khác. Worker hiện là tài nguyên có sẵn, không do
   round này tạo ra.
2. **Population trước kết quả:** từ AgentDojo commit
   `089ed468cf3ed0322acc66b0211f26d9d90dbf60`, tạo và commit một
   `pilot_case_manifest` trước khi gọi model. Manifest phải liệt kê mọi cặp
   `workspace`/`injecagent` hợp lệ, sắp xếp theo ID, và chọn một tập con bằng
   rule xác định từ commit + seed; không được chọn case dựa trên việc baseline
   có bị tấn công thành công hay không. Mỗi row phải khóa indirect-content
   carrier, migration family, independent harmful-effect predicate, và benign
   twin nếu có. Số episode không được viết trước bằng một con số tùy ý: một
   episode có số completion biến thiên, vì vậy manifest và dry-run phải cho
   biết cardinality trước khi chi tiền.
3. **Drift công bằng:** hook hiện có
   `AGENTDOJO_ATTESTATION_DRIFT_TOOL`/`AGENTDOJO_ATTESTATION_DRIFT_MODE` chỉ
   được nạp trong track `attested` của
   [`run_agentdojo_paired_smoke.py`](../scripts/run_agentdojo_paired_smoke.py).
   Nó là stress test của chính adapter, không phải migration trung lập cùng
   xảy ra với mọi cấu hình. Trước khi gọi pilot “versioned tool-contract”, cần
   một cặp schema/registry/mapping `v0 -> v1` được hash, được trình bày cho
   agent, và một migration driver bên môi trường/executor áp dụng giống nhau
   cho các cấu hình so sánh. Full study còn phải counterbalance thứ tự `v0`/
   `v1` và reset sandbox sau mỗi episode.
4. **Khóa request và trace:** source/`uv.lock` phải qua pin check; mỗi episode
   phải ghi request đã serialize, endpoint release, response metadata,
   policy/migration hash, initial-state hash, redacted trace và outcome oracle.
   Endpoint chỉ ghi server default seed `0`; seed, `top_p`, output limit và
   thinking flag hiện không khóa được per request, nên pilot không đủ cho suy
   luận hiệu quả có thể tái lập.
5. **An toàn/đạo đức:** tool execution chỉ trong AgentDojo sandbox; cấm side
   effect ngoài sandbox và cấm retry tự động sau timeout/failure. Trace phải
   được redacted trước khi commit.

## Quy tắc dừng và diễn giải

Mức USD 10.00 được chia thành **tối đa USD 8.00 cho execution** và **USD 2.00
dự phòng**. Với giá GPU hiện thời, USD 8.00 tương đương `8.00 / 2.72 = 50/17`
GPU-hours trước disk/fee; phép tính này **không** là hard cap.
Route `/run` trong AgentDojo proxy hiện không gửi một trần USD theo job và
billing theo bucket không phải bộ đo thời gian thực. Proxy đã được sửa cục bộ
để fsync ledger không chứa prompt/key (lưu `job_id`/request hash và metadata), yêu cầu
`/cancel/{job_id}` khi hết hạn hoặc lỗi poll, và để launcher reconcile mọi job
không terminal trước khi sang track kế tiếp hoặc thoát. Tuy nhiên đây vẫn không
là hard cap: nếu POST submit hết hạn trước khi trả job ID, remote state là
ambiguous và batch phải dừng, còn cơ chế cancel chưa được xác minh bằng một job
thật ở endpoint đã xác nhận. Nếu fsync thất bại sau khi provider trả job ID,
proxy cố gửi cancel ngay rồi khóa tiến trình local, nhưng crash giữa lúc provider
nhận submit và lúc receipt được ghi bền vẫn là cửa sổ không thể loại bỏ bằng
ledger local. Một terminal state sau cancel cũng có thể là `COMPLETED` hoặc
`FAILED` do race, không chứng minh cancel đã dừng thực thi. Check billing
trước/sau mỗi batch tuần tự chỉ giảm rủi ro; nếu không thể quan sát billing hoặc
tổng phát sinh chạm USD 8.00, dừng ngay và không gửi batch kế tiếp.

Nếu final JSONL record bị torn bởi crash, launcher không append đè lên nó: nó
chỉ thử query/cancel các `job_id` hợp lệ trong prefix rồi dừng để điều tra thủ
công. Trạng thái này không được phép mở một batch mới.

Không có request-level USD ceiling hay TTL đã xác minh từ provider trong proxy
này; timeout local chỉ kích hoạt poll/cancel và không tự ràng buộc lifecycle
remote. Vì vậy không diễn giải bất kỳ unit test nào thành bằng chứng kiểm soát
chi phí vận hành.

Các điều kiện dừng bắt buộc khác:

- pin/lockfile/hash không khớp, release thay đổi, hoặc trace không có metadata
  bắt buộc;
- một track timeout, fail, thiếu oracle, hoặc sandbox reset không xác minh;
- migration không áp dụng tương đương cho các cấu hình;
- kết quả của tập case đã khóa không tạo được trace attack/tool hợp lệ. Khi đó
  báo cáo là feasibility-negative result; không săn thêm case để tạo kết quả
  thuận lợi.

Ngay cả khi mọi episode chạy xong, pilot chỉ được mô tả là bằng chứng rằng
pipeline đã thực thi trong sandbox. Nó không đóng R1, không đạt claim gate,
và không thay thế yêu cầu ít nhất ba model snapshots, split độc lập, baseline
thực thi công bằng, cụm thống kê và clean-room reproduction trong
[`research_protocol.md`](research_protocol.md).

## Quyết định hiện tại

**Không chạy job billable.** Cơ chế ledger/cancel đã có unit test local nhưng
chưa phải bằng chứng vận hành trên endpoint. Artifact
`experiments/fixtures/agentdojo_pilot_case_manifest_v1.json` hiện khóa 840
candidate `workspace`/`injecagent` có carrier nhìn thấy được ở source commit
đã pin, rồi chọn xác định ba case single-carrier theo hash seed. Validator kiểm
tra digest, thứ tự, pin, oracle không phụ thuộc guard và cardinality; toàn bộ
artifact vẫn mang `result_status: not_run`.

Điều này chỉ đóng blocker **population trước kết quả**, không mở khóa một
claim efficacy: ba case là feasibility subset chứ không phải sample thống kê,
và paired-smoke launcher hiện chưa phải executor gắn chặt manifest cho toàn bộ
arm. `agentdojo_pilot_execution_plan_v1.json` đã khóa 12 invocation chưa chạy
(6 attack, 6 benign twin) và 18 upstream task episode danh nghĩa; plan cấm
network/model call, retry tự động, và ghi rõ mọi benign twin đang **blocked**.
Lý do: runner hiện tại luôn bật InjecAgent; bỏ riêng `--injection-task` sẽ mở
rộng attack set, không tạo benign twin.

Blocker local tiếp theo vẫn là run-bound case/arm driver và independent outcome
adapter. Chỉ trace hoàn thành, đúng schema mới được chấm bằng oracle; timeout,
API error hoặc trace lỗi phải là `not_scored`, không được diễn giải là attack
success hay secure outcome. Sau đó vẫn cần một xác nhận ngắn của người dùng cho
chính endpoint `h5ec6v08cb8uc2` và trần USD 10.00 trước batch đầu tiên.
