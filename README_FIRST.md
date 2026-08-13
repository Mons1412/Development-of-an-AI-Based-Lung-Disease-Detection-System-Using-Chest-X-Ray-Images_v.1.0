# Lung X-ray AI Portable Windows x64 v1.2.0

Gói này chứa Python 3.12 portable, dependencies, source FastAPI hiện tại,
model 1.1.0 và production Knowledge Base. Không cần cài Python hoặc tạo `.venv`.

## Chạy ngay

1. Giải nén toàn bộ ZIP.
2. Chạy `START_API.cmd`.
3. Mở `http://127.0.0.1:8000/demo`.
4. Dừng bằng `Ctrl+C`.

Ứng dụng hoạt động offline ngay cả khi chưa cấu hình Gemini.

## Bật Gemini online an toàn

API key thật không nằm trong ZIP. Trên máy đích:

1. Chạy `SET_GEMINI_KEY.cmd`.
2. Dán key khi PowerShell hỏi; ký tự không hiển thị.
3. Chạy `TEST_GEMINI_CONNECTION.cmd`.
4. Khởi động lại bằng `START_API.cmd`.

Key chỉ được lưu ở `app/.env` trên máy đích. Không gửi lại ZIP sau khi file này
đã được tạo.

## Chạy đúng dạng Python module

`START_API.cmd` thực thi chính xác:

```text
runtime\python.exe -m lung_xray_api
```

Launcher tự đặt `PYTHONPATH`, model path, UTF-8, host và port. Nếu cổng 8000 bận:

```text
START_API.cmd 8080
```

## Tự kiểm tra

Chạy `VERIFY_PACKAGE.cmd`. Lần warm-up TensorFlow đầu tiên có thể mất vài phút.

## Dữ liệu và giới hạn

- Không kèm `.env`, API key, lịch sử SQLite, thumbnail, ảnh upload hoặc PDF tạm.
- Không kèm development Knowledge Base. Test clinical-review gate phụ thuộc development
  fixtures không nằm trong portable package; production assistant tests vẫn được giữ.
- Lịch sử mới được tạo cục bộ trong `app/var/data/`.
- Ảnh gốc không được lưu mặc định.
- Kết quả chỉ phục vụ mục đích học thuật, không thay thế chẩn đoán của bác sĩ.
- Gemini cần Internet; offline assistant và prediction vẫn hoạt động khi mất mạng.
