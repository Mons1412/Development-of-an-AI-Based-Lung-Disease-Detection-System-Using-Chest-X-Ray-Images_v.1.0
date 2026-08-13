# Endpoint Map

| Mendix use case | Method | FastAPI path | Notes |
| --- | --- | --- | --- |
| Kiểm tra process | `GET` | `/health/live` | Không cần model ready |
| Kiểm tra model | `GET` | `/health/ready` | Dùng trước upload |
| Hiển thị metadata | `GET` | `/api/v1/model-info` | Lấy model version và class order |
| Gửi ảnh predict | `POST` | `/api/v1/predict` | Multipart field `file` |
| Compatibility | `POST` | `/predict` | Alias theo artifact contract |

Mendix không gọi trực tiếp artifact file.
