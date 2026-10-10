# Báo cáo học phần của Nhóm 11 bằng LaTeX

Bộ này thực hiện nhánh **Hoàn thành** trong ảnh tiêu chí. Ưu tiên: báo cáo môn học → bài báo nghiên cứu → mục tiêu Q2.

## Chỉnh sửa trên Overleaf

1. Tạo **New Project → Upload Project**, chọn ZIP nguồn bàn giao.
2. Đặt **Main document: main.tex**, **Compiler: XeLaTeX**.
3. Recompile để tạo báo cáo. Bibliography dùng BibTeX, Overleaf tự chạy các lượt cần thiết.
4. Chọn slides.tex làm Main document để tạo bản trình chiếu 10 slide.
5. Dùng **Share** để mời thành viên; cả nhóm sửa cùng project. Không cần khóa API hoặc chạy AgentDojo để biên dịch.

## Các file cần sửa

| File | Nội dung |
|---|---|
| main.tex | Tiêu đề, tác giả, học phần, tóm tắt, thứ tự các phần |
| sections/01_problem.tex | Vấn đề, mục tiêu, mô hình đe dọa |
| sections/02_background.tex | Kiến thức nền tảng |
| sections/03_related.tex | Nghiên cứu liên quan |
| sections/04_solution.tex | Giải pháp, quyền truy cập, F/M |
| sections/05_evaluation.tex | Triển khai, kết quả và kế hoạch đánh giá |
| sections/06_conclusion.tex | Hạn chế, kết luận |
| references.bib | Danh mục tài liệu tham khảo |
| slides.tex | Nội dung trình chiếu và ghi chú người nói |

Không chỉnh llncs.cls và splncs04.bst khi sửa nội dung. Có thể chia phần theo thành viên nhưng nhóm tự xác nhận phân công; bộ này không gán công việc hay thành tích cho cá nhân.

## Biên dịch trên máy

Cài TeX Live hoặc MiKTeX có XeLaTeX, BibTeX và các gói trong phần đầu main.tex.

    xelatex main.tex
    bibtex main
    xelatex main.tex
    xelatex main.tex
    xelatex slides.tex
    xelatex slides.tex

Hoặc dùng Tectonic (tự chạy bibliography/lượt tham chiếu; tải dependency khi chạy lần đầu):

    tectonic main.tex
    tectonic slides.tex

Font TeX Gyre Termes/Heros và Latin Modern Mono giúp nhóm biên dịch giống nhau trên Windows, Linux và Overleaf. File UTF-8. Các ký tự đặc biệt trong văn bản cần escape; thêm citation bằng lệnh cite và đề mục bằng section. Không chèn ngắt trang thủ công chỉ để sửa một màn hình hiển thị.

## Mẫu và độ tương đồng

Mẫu người dùng: Template-1-cột.docm, SHA-256: 257ec3d1c458f8b8c7438edb35ff3ace39d62bece9aad3009f272782902005bb. File Word gốc không sửa hoặc chạy macro.

LaTeX dùng lớp LNCS 2.26 (25/02/2025) từ CTAN, bố cục một cột, khối tiêu đề/tác giả/tóm tắt/từ khóa, đánh số đề mục và danh mục trích dẫn. Đây là chuyển đổi bố cục sang LaTeX, **không phải bản sao từng pixel của Word**: font TeX Gyre Termes thay Times New Roman; ngắt dòng và phân trang có thể khác. Nội dung minh họa, trường/ORCID/email và tuyên bố lợi ích mẫu không được chép thành thông tin của nhóm.

Nguồn lớp: https://mirrors.ctan.org/macros/latex/contrib/llncs.zip . Xem LLNCS-LICENSE.md cho CC BY 4.0 và ghi công Springer. Hai file lớp/style được giữ nguyên.

## Phạm vi bằng chứng

- Bảng bốn ô F/M là **source-conformance**, không phải benchmark LLM.
- Fake provider kiểm tra tích hợp; chưa chứng minh hiệu quả phòng thủ.
- 144 test là số đã ghi tại snapshot nghiên cứu e678ea2; chưa bao phủ mọi WIP sau đó.
- Không suy ra ASR, độ tin cậy thống kê, tính mới hoặc Q2 readiness từ các kiểm tra này.
- Tên và thông tin nhóm lấy từ báo cáo hiện có; nhóm nên kiểm tra trước khi nộp. Bổ sung trường/lớp/giảng viên/email khi có thông tin xác nhận.

## Tái lập kiểm tra kỹ thuật nếu cần

Trong repository nghiên cứu, chạy PowerShell với môi trường pinned đã cài sẵn:

    $env:PYTHONUTF8 = "0"
    $env:PYTHONIOENCODING = "utf-8"
    $python = "./tmp/agentdojo-source/.venv31213/Scripts/python.exe"
    & $python -B -m experiments.agentdojo_file_scope_preflight --output qa/course_source_check.json
    & $python -B -m unittest experiments.test_agentdojo_file_scope_defense -v

ZIP LaTeX chỉ chứa báo cáo/trình bày và không đóng gói runtime thí nghiệm. Lệnh trên không phải điều kiện để biên dịch hoặc chỉnh sửa báo cáo.
