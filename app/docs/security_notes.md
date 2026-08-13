# Security Notes

## Trust boundary

Upload file là trust boundary chính. API không tin filename hoặc MIME từ client và phải decode bằng Pillow trước khi preprocess.

## File upload

- Chặn file rỗng.
- Chặn file vượt `MAX_UPLOAD_MB`.
- Chỉ nhận JPG, JPEG, PNG.
- Kiểm tra nội dung file bằng magic/detect format.
- Không lưu ảnh upload mặc định.
- Không log raw bytes.

## API key

Mặc định:

```text
API_KEY_ENABLED=false
```

Nếu bật API key, so sánh bằng `secrets.compare_digest`. API key chỉ kiểm soát truy cập local, không liên quan chất lượng AI.

## Logging

Không log:

- ảnh;
- raw bytes;
- API key;
- đường dẫn cá nhân;
- thông tin bệnh nhân.

## Artifact integrity

Nếu checksum artifact sai, service không được chuyển sang ready state.
