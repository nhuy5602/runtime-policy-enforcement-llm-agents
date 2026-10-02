# Cập nhật tài liệu gốc — 02 tháng 10 năm 2026

## Mục đích và giới hạn

Artifact này ghi lại một tổng hợp ngắn gồm ba công trình gốc cho hướng đang xét: **Security Regression Testing of Indirect Prompt-Injection Defenses under Versioned Agent Tool Contracts**. Đây là đối tượng nghiên cứu đã thu hẹp từ ý tưởng ban đầu về một runtime policy guard tổng quát.

Đây **không** phải systematic review và không hỗ trợ claim “first”, “novel” hoặc “unexplored”. Nó chỉ trả lời yêu cầu tìm 2–3 tài liệu gần, kiểm tra chồng lấp rõ ràng, rồi điều chỉnh phạm vi project trước khi chạy bất kỳ đánh giá LLM nào.

Các truy vấn hạt giống được dùng để truy vết nguồn gốc gồm:

- `"indirect prompt injection" tool-using LLM agent benchmark`;
- `"prompt injection" capability-based LLM agents`;
- `"runtime privilege control" LLM agents AgentDojo`;
- `"tool contract" schema drift indirect prompt injection`.

Sau bước truy vết, chỉ trang công bố chính thức/primary source được dùng cho ba bài dưới đây. Ngày truy cập: 02 tháng 10 năm 2026.

## Ba công trình liên quan

| Công trình | Phương pháp và bằng chứng tác giả báo cáo | Quan hệ với project | Hệ quả định vị |
|---|---|---|---|
| **AgentDojo** — Debenedetti et al., NeurIPS 2024 | Môi trường động, stateful cho agent gọi tool trên dữ liệu không tin cậy; 97 realistic tasks và 629 security test cases; đo cả utility lẫn security. | Là benchmark/corpus phù hợp để buộc agent thật chạy với carrier gián tiếp và quan sát side effect. | Không được claim benchmark IPI mới, “first AgentDojo defense”, hoặc suy luận efficacy từ simulator nội bộ. |
| **CaMeL** — Debenedetti et al., arXiv v2 (2025, preprint) | Tách control flow khỏi data flow, dùng privileged/quarantined LLM, capability và interpreter kiểm tra policy ở tool call. Tác giả báo cáo 77% task AgentDojo với provable security, so với 84% ở hệ không phòng vệ. | Chồng lấp trực tiếp với capability, least privilege, data/control separation và runtime enforcement. | Không được trình bày capability hay runtime guard là primitive mới. Một extension có thể kiểm tra liệu một defense dạng này có bị security regression khi tool contract chuyển `v0 -> v1` hay không. |
| **Progent** — Shi et al., arXiv v3 (2026, preprint) | Policy symbolic trên tool name/arguments, enforcement xác định ở tool boundary và SMT check cho policy update. Tác giả báo cáo trên AgentDojo ASR giảm 39,9% xuống 1,0% trong cấu hình của họ, đồng thời báo utility. | Chồng lấp trực tiếp với policy theo tool/argument, privilege control, approval và proxy/wrapper ở runtime. | Không được claim policy DSL, dynamic privilege control, approval hay “bảo vệ agent khỏi IPI” là mới. Nghiên cứu chỉ có thể đo fidelity giữa verdict trước dispatch và effect sau dispatch dưới migration đã khóa. |

### 1. AgentDojo

AgentDojo đặt bài toán ở đúng mức hệ thống: tool output không tin cậy có thể đi vào context, agent tự sinh action và làm thay đổi một môi trường stateful. Vì vậy nó khắc phục điểm yếu của đánh giá chỉ chấm văn bản hoặc chỉ đưa vào một tool call độc hại đã tạo sẵn. Với project này, AgentDojo là **môi trường đánh giá**, không phải đóng góp để tái phát minh. Một kết quả chỉ được gọi là AgentDojo efficacy khi action do LLM tạo, carrier IPI thật sự đi qua runtime, và utility/security đều được chấm.

### 2. CaMeL

CaMeL đã phủ phần lớn ý tưởng kiến trúc ban đầu: tách dữ liệu không tin cậy khỏi control flow và thực thi capability/policy tại thời điểm gọi tool. Điều này làm hướng “xây một guard capability mới” không còn là một novelty hợp lý. Khác biệt có thể kiểm chứng của project không phải là phủ nhận CaMeL, mà là một câu hỏi đánh giá hẹp hơn: sau khi interface tool thay đổi có kiểm soát, liệu quyết định authorization ban đầu vẫn tương ứng với effect thực tế hay không. Phần mô tả/evaluation được đọc ở đây không báo cáo endpoint paired `v0 -> v1` này; đó là một quan sát có giới hạn của nguồn đã sàng lọc, không phải tuyên bố rằng không có công trình nào từng làm điều đó.

### 3. Progent

Progent củng cố thêm rằng least privilege, policy cập nhật động và enforcement trước tool call đã là những hướng có kết quả benchmark mạnh. Nó cũng nêu rõ một giới hạn triển khai quan trọng: proxy mode không bảo vệ tool built-in nếu tool đó bypass interface MCP bên ngoài. Vì vậy project phải đo **mediation coverage** và effect hậu thực thi, không chỉ tin vào verdict `ALLOW`/`DENY`. Điểm mở có thể đo là security regression của cùng defense khi mapping tool/argument ở contract `v0` được migration sang `v1`, thay vì đề xuất thêm một policy language hay proxy nữa.

## Tổng hợp: ý tưởng có bị trùng lặp không?

**Có, nếu đề tài vẫn được mô tả là một cơ chế runtime policy enforcement, least-privilege/capability system, hoặc prompt-injection defense tổng quát.** CaMeL và Progent đã bao phủ trực tiếp những claims đó; AgentDojo đã cung cấp benchmark động cho security–utility evaluation.

Định vị còn có thể bảo vệ, nhưng chỉ như một **câu hỏi đo lường/replication extension có điều kiện**:

> Với cùng IPI carrier, cùng task, cùng initial state và cùng defense, việc migration tool contract `v0 -> v1` có tạo security regression giữa verdict authorization trước dispatch và harmful/authorized effect sau dispatch hay không?

Điểm khác biệt này chỉ hợp lệ nếu toàn bộ điều kiện sau có mặt trong thí nghiệm:

1. IPI đi qua email/web/tool output lúc agent chạy, không phải action nguy hiểm tạo tay.
2. So sánh paired `v0 -> v1`; manifest công bố chính xác alias/schema/sink/scope nào thay đổi.
3. Action được LLM sinh ra; fixed trace, simulator hay source ground truth chỉ là kiểm tra dụng cụ.
4. Harmful effect được chấm từ state/effect hậu thực thi bằng oracle độc lập với verdict của guard.
5. Có genuine no-injection benign control, reset có chứng cứ, model/prompt/source/trace hash được lưu và failure/timeout là `not_scored`.
6. Báo security, clean utility, escalation/approval burden và latency; phân tích thống kê phải ở mức paired episode, không gộp component test vào LLM result.

Nếu thiếu (1)–(4), kết quả chỉ được gọi là component conformance hoặc diagnostic stress test. Nếu đủ (1)–(4) nhưng thiếu đối chứng/thống kê, nó chỉ là case study/pilot — không phải bằng chứng Q2-ready hay một claim hiệu quả tổng quát.

## Áp dụng vào project

Từ tổng hợp này, project được khóa lại theo ba quyết định:

1. **Không xây claim cơ chế mới.** Runtime guard hiện có trong repository là reference monitor/component baseline; không được gọi là đóng góp chính.
2. **Đơn vị đánh giá là paired security regression.** Mỗi hàng kết quả phải buộc cùng case/agent/initial state/defense vào `v0` và `v1`, cùng evidence cho carrier, source, reset, trace và snapshot trước/sau.
3. **Endpoint là effect, không phải verdict.** `ALLOW`/`DENY`, policy hash hay trace text không đủ; harmful-effect oracle độc lập và benign end-state utility phải được giữ tách biệt.

Do đó protocol dùng `AFER_uncond`, `AFER_cond`, `PDER_schema`, `SMF`, `BDP` và mediation coverage như **planned endpoints**, không phải kết quả hiện có. Các source-only calibration, simulator và tiny pilot của repository vẫn không phải LLM efficacy evidence. Cổng R1 trong [`r1_reopening_20260927.md`](r1_reopening_20260927.md) vẫn mở: cần replay độc lập truy vấn trên các chỉ mục học thuật trước khi đóng claim-novelty.

## Tài liệu tham khảo gốc

1. E. Debenedetti, J. Zhang, M. Balunović, L. Beurer-Kellner, M. Fischer, and F. Tramèr. “AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents.” *NeurIPS 2024, Datasets and Benchmarks Track*. [Trang công bố chính thức](https://proceedings.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html).
2. E. Debenedetti et al. “Defeating Prompt Injections by Design.” *arXiv:2503.18813v2*, 2025 (preprint). [Bài báo](https://arxiv.org/abs/2503.18813) · [bản HTML v2](https://arxiv.org/html/2503.18813v2) · [artifact mã nguồn](https://github.com/google-research/camel-prompt-injection).
3. T. Shi et al. “Progent: Securing AI Agents with Privilege Control.” *arXiv:2504.11703v3*, 2026 (preprint). [Bài báo](https://arxiv.org/abs/2504.11703) · [bản HTML v3](https://arxiv.org/html/2504.11703v3).
