# Limitations

## Scope

Phase 02 chỉ phục vụ model đã train ở Phase 01 qua REST API. Phase này không retrain, fine-tune, đổi kiến trúc, đổi weights hoặc thêm model khác.

## ML constraints

- Class order phải đọc từ artifact.
- Preprocessing đã nhúng trong model.
- FastAPI không được gọi `mobilenet_v2.preprocess_input()` lần thứ hai.
- Không tự thêm uncertainty threshold.
- Probability là model probability, không phải độ tin cậy lâm sàng.

## Runtime constraints

- TensorFlow model có thể tiêu tốn RAM đáng kể.
- Local demo nên dùng một worker để tránh nhân bản model trong RAM.
- Smoke model cần ảnh X-quang hợp lệ do người dùng cung cấp.

Kết quả chỉ phục vụ mục đích học thuật và không thay thế chẩn đoán của bác sĩ.
