# Error Map

| HTTP | Code | Mendix handling |
| ---: | --- | --- |
| 400 | `invalid_image` | Hiển thị lỗi file không hợp lệ và cho upload lại |
| 401 | `unauthorized` | Kiểm tra API key local nếu đang bật |
| 503 | `model_not_ready` | Hiển thị trạng thái API chưa sẵn sàng |

Không hiển thị stack trace cho người dùng cuối.
