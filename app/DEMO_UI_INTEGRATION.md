# Tích hợp giao diện demo vào FastAPI

Bộ file này là phần giao diện kỹ thuật của Phase 02. Giao diện gọi trực tiếp:

```text
GET  /health/ready
GET  /api/v1/model-info
POST /api/v1/predict
```

## 1. Cây thư mục

```text
src/lung_xray_api/
├── api/v1/demo.py
└── web/
    ├── templates/
    │   └── demo.html
    └── static/
        ├── demo.css
        ├── demo.js
        └── assets/
            ├── favicon.svg
            ├── lungs-hero.svg
            └── lungs-result.svg
```

## 2. Mount static assets trong `main.py`

Bổ sung một lần tại composition root:

```python
from pathlib import Path

from fastapi.staticfiles import StaticFiles

WEB_DIR = Path(__file__).resolve().parent / "web"

app.mount(
    "/static",
    StaticFiles(directory=str(WEB_DIR / "static")),
    name="static",
)
```

Không mount static nhiều lần và không đặt trong request handler.

## 3. Include demo router

Trong `api/v1/router.py`:

```python
from fastapi import APIRouter

from lung_xray_api.api.v1 import demo, health, model_info, predict

router = APIRouter()
router.include_router(health.router)
router.include_router(model_info.router)
router.include_router(predict.router)
router.include_router(demo.router)
```

Nếu router chính của dự án có tên khác, chỉ cần include `demo.router` đúng một lần.

## 4. Contract response được UI hỗ trợ

UI hỗ trợ cả nested probabilities:

```json
{
  "status": "success",
  "prediction": "pneumonia",
  "model_probability": 0.9936,
  "probabilities": {
    "normal": 0.0053,
    "pneumonia": 0.9936,
    "tuberculosis": 0.0011
  },
  "model_version": "1.1.0",
  "processing_time_ms": 772,
  "disclaimer": "..."
}
```

và ba field phẳng:

```json
{
  "normal_probability": 0.0053,
  "pneumonia_probability": 0.9936,
  "tuberculosis_probability": 0.0011
}
```


## Mendix multipart compatibility

Mendix `System.FileDocument` integration path:

```text
System.FileDocument
-> multipart/form-data
-> field name: file
-> MIME may be application/octet-stream
-> backend normalizes MIME
-> magic-byte validation
-> Pillow verify and full decode
-> preprocessing
-> inference
-> response JSON
-> Mendix Import Mapping
```

`application/octet-stream` is accepted only as a neutral transport MIME from Mendix. It does not bypass content validation. The backend still rejects fake `.jpg` files, invalid binary data, unsupported extensions, unsupported specific MIME values, MIME/content mismatch, oversized files, empty files, truncated files, and unsafe pixel counts.

For Mendix, keep the multipart field name exactly `file`. Do not manually force a misleading `Content-Type` for the file part; let Mendix send the file part naturally unless it can safely provide `image/jpeg` or `image/png`.

## 5. Lưu ý API key

Không hard-code API key trong `demo.js`, vì JavaScript được gửi công khai tới trình duyệt.

Local demo nên dùng:

```env
API_KEY_ENABLED=false
```

Khi cần bảo vệ API, nên dùng giải pháp server-side hoặc chỉ dùng API key ở Mendix runtime.

## 6. Kiểm thử

```powershell
python -m pytest tests\integration\test_demo_ui.py -q
python -m lung_xray_api
```

Mở:

```text
http://127.0.0.1:8000/demo
```

## 7. Asset

Ba file SVG là asset nội bộ, không phụ thuộc CDN và không phải logo thương hiệu:

- `lungs-hero.svg`: minh họa nền header;
- `lungs-result.svg`: minh họa trong trạng thái chờ và kết quả;
- `favicon.svg`: icon tab trình duyệt.

Ảnh X-quang preview luôn lấy từ file người dùng chọn. UI không chứa ảnh bệnh nhân mẫu.
