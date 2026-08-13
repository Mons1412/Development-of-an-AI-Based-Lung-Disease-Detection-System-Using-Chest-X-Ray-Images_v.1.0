# Lung X-ray AI — Phase 3 Integrated Local Workspace

> **Application version:** 1.2.0  
> **Model version:** 1.1.0  
> **Knowledge Base:** 1.0.0 production-only  
> **SQLite schema:** 2  
> **Status:** source patch ready for user testing; Task 09 Windows release not executed.

Phase 3 adds confirmed patient/case metadata, strict filename parsing, local SQLite history, derivative thumbnails, a modular analysis workspace, floating offline assistant, controlled visualizations and analysis-ID based report v2. The original full-resolution upload is not persisted.

## Phase 3 quick flow

```text
Select image -> preview -> parse/manual metadata -> confirm or anonymous
-> persisted analysis -> result/history -> offline assistant -> report by analysis_id
```

## Phase 3 local endpoints

```text
POST   /api/v1/analyses/parse-filename
POST   /api/v1/analyses
GET    /api/v1/analyses
GET    /api/v1/analyses/{analysis_id}
GET    /api/v1/analyses/{analysis_id}/thumbnail
DELETE /api/v1/analyses/{analysis_id}
GET    /api/v1/analyses/{analysis_id}/report
POST   /api/v1/assistant/query
```

## Privacy boundary

History is local-loopback only until an account/role model exists. SQLite stores approved metadata and a re-encoded thumbnail. Do not expose this build on a LAN or Internet as if loopback containment were authentication.

## Optional Gemini online assistant

The assistant stays local by default. To enable the optional Gemini explanation
mode, first revoke any key that has appeared in a screenshot, source file, or
chat, then create a new key in Google AI Studio. Never place a real key in
`.env.example` or send it through chat.

```powershell
.\scripts\SET_GEMINI_KEY.ps1
.\.venv\Scripts\python.exe scripts\test_gemini_connection.py
.\.venv\Scripts\python.exe -m lung_xray_api
```

The script writes the new key only to ignored `.env`, enables
`ONLINE_AI_ENABLED=true`, and keeps offline retrieval as the fallback. At
runtime, `/api/v1/assistant/status` reports `active_mode: "online"` only when
Gemini has completed a successful live probe or answer. A configured provider
starts as `configured_unverified`; transient failure changes it to
`degraded_offline` while local retrieval remains available. Online mode sends a
canonical question derived from the resolved intent, non-identifying prediction
context and approved Knowledge Base chunks. It never sends the original image,
thumbnail, filename, patient code, patient display name or raw chat text. Do not
enter personal or clinical-record details in chat.

---

# Phase 02 - FastAPI Inference

> **Phase status:** COMPLETED  
> **Release version:** 1.1.0  
> **Model version:** 1.1.0  
> **Integration contract:** LOCKED - 1.0.0  
> **Input artifact:** `lung_model_package_v1.zip`  
> **Output:** Local REST API, demo UI, OpenAPI và Mendix handoff

## Mục tiêu

Phase này load model Deep Learning đã được tạo ở Phase 01 và cung cấp REST API local để Mendix gọi bằng HTTP.

Kết quả chỉ phục vụ mục đích học thuật và không thay thế chẩn đoán của bác sĩ.

## Trạng thái

Audit ngày `2026-06-30` xác nhận Phase 02 đã pass P0 gate:

- Python `.venv` dùng Python `3.12.10` và `pip check` không có broken dependency.
- Import check, `compileall`, unit tests, integration tests, full pytest, `pyright` và `ruff` đều pass.
- Artifact đủ 8/8 file, checksum pass, model version `1.1.0`, input shape `[224, 224, 3]` và preprocessing embedded trong model.
- Model smoke với ảnh X-quang local pass.
- Runtime API trả `200` cho `/`, `/health/live`, `/health/ready`, `/api/v1/model-info`, `/api/v1/predict`, `/docs`, `/redoc`, `/openapi.json` và `/demo`.
- Demo UI pass qua browser automation cho preview, prediction, probability bars, raw JSON, reset và error state.
- OpenAPI và Mendix examples đã được sinh từ `app.openapi()` và API/TestClient thật.

Lưu ý: workspace hiện tại có Git metadata không hợp lệ nên chưa thể xác minh `git status`, `git diff` hoặc remote GitHub.

## Phân loại file

| Lifecycle | Ý nghĩa | Trạng thái |
| --- | --- | --- |
| `[S]` | Source hoặc tài liệu viết tay | `src/`, `scripts/`, `tests/`, `docs/`, handoff markdown |
| `[C]` | Artifact copy từ Phase 01 | `artifacts/lung_classifier/1.1.0/*` |
| `[G]` | Output sinh bởi script | OpenAPI JSON, response examples, `requirements-lock.txt` |
| `[R]` | Runtime/temp | `.venv/`, cache, logs, `var/tmp/*` |
| `[E]` | Evidence thật | Screenshot trong `handoff/mendix/evidence/` sau khi chụp thủ công |

Không tạo evidence hoặc generated JSON giả.

## Artifact

FastAPI chỉ dùng artifact đã giải nén tại:

```text
artifacts/lung_classifier/1.1.0/
```

Folder này phải có đủ tám file và checksum pass:

```text
lung_classifier_v1.keras
class_indices.json
preprocessing_config.json
model_metadata.json
inference_contract.json
metrics.json
model_runtime_requirements.txt
checksums.json
```

FastAPI không được gọi `mobilenet_v2.preprocess_input()` lần thứ hai vì model đã chứa `Rescaling(scale=1/127.5, offset=-1)`.

## Fresh clone setup

```powershell
git clone <REPOSITORY_URL>
cd Lung_Xray_AI_Graduation_Project
cd 02_fastapi_inference
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Nếu repository dùng Git LFS cho artifact lớn, chạy thêm sau khi clone:

```powershell
git lfs pull
```

## Verification

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts\verify_artifacts.py
.\.venv\Scripts\python.exe -m compileall src scripts tests
.\.venv\Scripts\python.exe -m pytest tests\unit -q
.\.venv\Scripts\python.exe -m pytest tests\integration -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pyright src scripts tests
.\.venv\Scripts\python.exe -m ruff check src scripts tests
```

Smoke model thật cần ảnh X-quang local hợp lệ:

```powershell
.\.venv\Scripts\python.exe scripts\smoke_model.py --image "<VALID_LOCAL_XRAY_PATH>"
```

## Offline model evaluation

Đặt một dataset có nhãn đã được xác minh ngoài source control theo cấu trúc
`evaluation_dataset\normal`, `evaluation_dataset\pneumonia` và
`evaluation_dataset\tuberculosis`. Chỉ `.jpg`, `.jpeg` và `.png` được xét;
dataset và thư mục kết quả mặc định đã được ignore bởi Git.

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe scripts\evaluate_dataset.py `
  --dataset-root evaluation_dataset `
  --output-dir var\evaluation `
  --dataset-id "<DATASET_ID>" `
  --dataset-source "<LABEL_PROVENANCE>"
```

Lệnh tạo `predictions.csv`, `skipped_files.csv`, `confusion_matrix.csv`,
`metrics.json` và `evaluation_summary.json`. Chỉ thêm
`--ground-truth-confirmed` sau khi nhãn folder đã được xác minh; nếu không,
tool chỉ ghi `folder_label_accuracy` và không công bố `accuracy`. Chỉ thêm
`--training-overlap-reviewed` sau khi đã kiểm tra dataset không chồng lấp với
tập train.

Ví dụ chạy một evaluation set cố định 200 ảnh (không giả định mọi dataset có
200 ảnh):

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe scripts\evaluate_dataset.py `
  --dataset-root evaluation_dataset `
  --output-dir var\evaluation-200 `
  --dataset-id "evaluation-200" `
  --dataset-source "<LABEL_PROVENANCE>" `
  --max-samples 200 `
  --ground-truth-confirmed `
  --training-overlap-reviewed
```

`--max-samples` chọn deterministic theo vòng tròn giữa các lớp để giảm thiên
lệch theo thứ tự folder; báo cáo luôn ghi số mẫu thực tế, lớp bị thiếu, ảnh lỗi
hoặc bị bỏ qua, và cảnh báo cỡ mẫu nhỏ.

## Run local API

```powershell
.\.venv\Scripts\python.exe -m lung_xray_api
```

Các URL chính:

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/health/live
http://127.0.0.1:8000/health/ready
http://127.0.0.1:8000/api/v1/model-info
http://127.0.0.1:8000/api/v1/predict
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/redoc
http://127.0.0.1:8000/openapi.json
http://127.0.0.1:8000/demo
```


## Mendix multipart upload contract

`POST /api/v1/predict` accepts `multipart/form-data` only.

Required upload field:

```text
file
```

Supported filename extensions when a filename is present:

```text
.jpg
.jpeg
.png
```

Supported standard image MIME values:

```text
image/jpeg
image/png
```

Mendix `System.FileDocument` uploads may send a neutral transport MIME:

```text
application/octet-stream
```

`application/octet-stream` is accepted only as a neutral transport MIME. It does not bypass backend validation. The API still verifies byte size, extension when present, JPEG/PNG magic bytes, MIME-to-detected-format consistency for specific image MIME values, Pillow `Image.verify()`, full Pillow decode via `image.load()`, positive dimensions, and Pillow pixel bomb limits.

Maximum upload size defaults to `10 MB` through `MAX_UPLOAD_MB=10`.

Before starting Mendix end-to-end testing, start FastAPI first:

```powershell
cd 02_fastapi_inference
.\.venv\Scripts\python.exe -m lung_xray_api
```

Canonical success response fields for Mendix mapping:

```json
{
  "status": "success",
  "prediction": "pneumonia",
  "model_probability": 0.9936,
  "normal_probability": 0.0053,
  "pneumonia_probability": 0.9936,
  "tuberculosis_probability": 0.0011,
  "model_version": "1.1.0",
  "processing_time_ms": 772,
  "disclaimer": "..."
}
```

Canonical error expectations:

| Case | HTTP | Code |
| --- | ---: | --- |
| Invalid binary, empty file, oversized file, wrong extension, wrong MIME, decode failure | 400 | `invalid_image` |
| Wrong multipart field name, for example `image` instead of `file` | 422 | FastAPI validation error |
| Model/artifact not ready | 503 | `model_not_ready` |
| API key enabled but missing or invalid | 401 | FastAPI authorization error |

## Generated output policy

- `requirements-lock.txt` chỉ sinh sau clean install bằng `pip freeze --local --exclude-editable`.
- OpenAPI chỉ sinh từ `app.openapi()` sau khi routes pass.
- Response examples chỉ sinh bằng TestClient hoặc API response thật.
- Screenshot evidence phải chụp thủ công sau khi Swagger/demo chạy thật.

## Export handoff

```powershell
.\.venv\Scripts\python.exe scripts\export_openapi.py
.\.venv\Scripts\python.exe scripts\export_mendix_handoff.py --image "<VALID_LOCAL_XRAY_PATH>"
```

Kết quả nằm tại:

```text
handoff/mendix/openapi/lung-xray-api.openapi.json
handoff/mendix/examples/
```
