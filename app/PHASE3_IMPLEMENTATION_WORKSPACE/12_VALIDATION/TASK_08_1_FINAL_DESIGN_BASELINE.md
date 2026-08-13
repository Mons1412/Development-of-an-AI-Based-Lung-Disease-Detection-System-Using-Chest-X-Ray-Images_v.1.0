# Task 8.1 Final Design Baseline

Status: **implemented baseline for user testing**  
Application: `1.2.0` · Model: `1.1.0` · Knowledge Base: `1.0.0` · SQLite schema: `2`

## Quyết định nguồn sự thật

- FastAPI + Jinja2 + vanilla JavaScript ES modules; không thêm frontend framework.
- Trợ lý chỉ dùng rules/retrieval và production Knowledge Base local; không Gemini/API ngoài.
- SQLite là persistence duy nhất cho lịch sử. Ảnh gốc không được lưu; chỉ thumbnail đã re-encode.
- Ca có định danh bắt buộc `patient_display_name`; `patient_code` không bắt buộc.
- Ca ẩn danh không lưu code/tên và phải được xác nhận rõ ràng.
- Parser chỉ full-match `<PATIENT_CODE>__<PATIENT_NAME>__<YYYYMMDD>.<jpg|jpeg|png>`.
- Prediction, history, visualization và report dùng cùng một probability contract với tolerance `1e-4` rồi normalize.
- Report mới được dựng từ `analysis_id`; frontend không gửi lại xác suất để tạo report.
- Biểu đồ đường chỉ dùng cho chuỗi lịch sử đã lọc, không biểu diễn một prediction đơn lẻ.

## Kiến trúc cuối

`route -> application service -> repository/storage` cho backend.  
`app store -> controller -> API/renderer` cho frontend.

## Contract bảo mật

History/report chỉ khả dụng khi server được cấu hình loopback và client thực tế là loopback. Response nhạy cảm dùng `Cache-Control: no-store`. Không coi loopback là authentication cho triển khai mạng.

## Tài liệu bị thay thế

Các khác biệt cũ về BLOB thumbnail, cursor pagination, endpoint parser hoặc filename convention trong báo cáo Task 8.1 trước đây được coi là lịch sử thiết kế, không còn là contract active. Contract active nằm trong các tài liệu `*_FINAL.md` của thư mục này.
