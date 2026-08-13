# Phase 02 Completion Gate Report

> **Document status:** FINAL  
> **Phase:** 02 - FastAPI Inference  
> **Release version:** 1.0.0  
> **Model version:** 1.1.0  
> **Integration contract:** 1.0.0  
> **Audit date:** 2026-06-30

## Scope

Báo cáo này ghi lại kết quả chạy quality gate P0 cho Phase 02. Các gate runtime, test, API, demo UI, OpenAPI và Mendix handoff đã PASS bằng môi trường thật.

Kết quả chỉ phục vụ mục đích học thuật và không thay thế chẩn đoán của bác sĩ.

## Environment

| Item | Evidence | Result |
| --- | --- | --- |
| Python version | `.venv\Scripts\python.exe --version` | `Python 3.12.10` |
| Interpreter | `.venv\Scripts\python.exe -c "import sys; print(sys.executable)"` | Nằm trong `02_fastapi_inference\.venv\Scripts\python.exe` |
| Dependency check | `.venv\Scripts\python.exe -m pip check` | `No broken requirements found.` |
| Import check | Import FastAPI, Pydantic, TensorFlow, Keras, NumPy, Pillow và `lung_xray_api` | `IMPORT_CHECK_PASS` |

## P0 Gate Matrix

| Gate | Command/Evidence | Result |
| --- | --- | --- |
| P0-01 Python environment | `python --version`, `sys.executable`, `pip check` | PASS |
| P0-02 Import | Runtime dependency import check | PASS |
| P0-03 Compile source | `.venv\Scripts\python.exe -m compileall src scripts tests` | PASS |
| P0-04 Artifact integrity | `.venv\Scripts\python.exe scripts\verify_artifacts.py` | PASS: `artifact_files=8/8`, `checksum=PASS`, model `1.1.0`, class order đúng |
| P0-05 Unit tests | `.venv\Scripts\python.exe -m pytest tests\unit -q` | PASS: `12 passed` |
| P0-05 Integration tests | `.venv\Scripts\python.exe -m pytest tests\integration -q` | PASS: `9 passed`, 1 dependency warning |
| P0-05 Full pytest | `.venv\Scripts\python.exe -m pytest -q` | PASS: `21 passed`, 1 dependency warning |
| P0-06 Model load và warm-up | `scripts\smoke_model.py --image <local-valid-xray>` | PASS: prediction `pneumonia`, model `1.1.0`, probabilities hợp lệ |
| P0-07 API runtime | `.venv\Scripts\python.exe -m lung_xray_api` và HTTP probes | PASS: tất cả endpoint bắt buộc trả `200` |
| P0-08 Prediction contract | HTTP `POST /api/v1/predict` với ảnh X-quang local | PASS: đủ fields bắt buộc và probabilities hợp lệ |
| P0-09 Error handling | HTTP probes cho zero-byte, fake JPG, MIME sai, GIF, oversized; TestClient model-not-ready | PASS: không trả stack trace |
| P0-10 Demo UI | Browser automation tại `/demo` | PASS: preview, prediction, probability bars, raw JSON, reset và error state |
| P0-11 OpenAPI handoff | `scripts\export_openapi.py`, parse JSON, so với `app.openapi()` | PASS: `OPENAPI_MATCHES_APP True` |
| P0-12 Mendix examples | `scripts\export_mendix_handoff.py --image <local-valid-xray>` | PASS: bốn JSON examples parse được và sinh từ app/API thật |
| P0-13 Mapping documents | Endpoint, field, error và environment mapping | PASS |
| P0-14 Static checks | `pyright src scripts tests`, `ruff check src scripts tests` | PASS: `0 errors`, `All checks passed!` |
| P0-15 Security baseline | `.env` absent, API key default off, no OpenAI/Gemini dependency, no secret pattern hit | PASS |

## Endpoint Verification

| Endpoint | HTTP status |
| --- | ---: |
| `/` | 200 |
| `/health/live` | 200 |
| `/health/ready` | 200 |
| `/api/v1/model-info` | 200 |
| `/api/v1/predict` | 200 |
| `/docs` | 200 |
| `/redoc` | 200 |
| `/openapi.json` | 200 |
| `/demo` | 200 |
| `/static/demo.css` | 200 |
| `/static/demo.js` | 200 |
| `/static/assets/favicon.svg` | 200 |
| `/static/assets/lungs-hero.svg` | 200 |
| `/static/assets/lungs-result.svg` | 200 |

## Prediction Evidence

Real-image smoke dùng ảnh X-quang local hợp lệ và trả:

```text
prediction=pneumonia
model_probability=0.9936072826385498
probabilities.normal=0.005327203776687384
probabilities.pneumonia=0.9936072826385498
probabilities.tuberculosis=0.0010655076475813985
model_version=1.1.0
```

Probabilities hữu hạn, nằm trong `[0,1]`, tổng gần `1` và prediction thuộc ba class đã khóa.

## Error Handling Evidence

| Case | HTTP | Code |
| --- | ---: | --- |
| Zero-byte file | 400 | `invalid_image` |
| Text payload giả `.jpg` | 400 | `invalid_image` |
| MIME không hợp lệ | 400 | `invalid_image` |
| Unsupported format | 400 | `invalid_image` |
| File quá lớn | 400 | `invalid_image` |
| Model service chưa ready | 503 | FastAPI `detail` |

## Generated Output

| File | Status |
| --- | --- |
| `handoff/mendix/openapi/lung-xray-api.openapi.json` | GENERATED / LOCKED |
| `handoff/mendix/examples/prediction-success.json` | GENERATED FROM REAL MODEL RESPONSE |
| `handoff/mendix/examples/invalid-image.json` | GENERATED FROM ROUTE VALIDATION |
| `handoff/mendix/examples/file-too-large.json` | GENERATED FROM ROUTE VALIDATION |
| `handoff/mendix/examples/model-not-ready.json` | GENERATED FROM APP STATE |
| `requirements-lock.txt` | GENERATED FROM `.venv` WITHOUT LOCAL PATH |

## Non-P0 Notes

| Item | Result | Note |
| --- | --- | --- |
| Benchmark report | PENDING | Không ghi latency giả |
| Swagger screenshot | PENDING | Không tạo screenshot giả |
| Demo screenshot | PENDING | Không tạo screenshot giả |
| Git metadata | FAIL | `.git` không hợp lệ nên `git status`, `git diff`, remote chưa xác minh được |
| Runtime temp cleanup | PENDING | Safety hook chặn recursive cleanup cho `var/tmp/edge-profile` |
| Phase 03 implementation | PENDING | Mendix source chưa triển khai |

## Final Decision

`PHASE 02 COMPLETED`

Integration contract được khóa ở version `1.0.0`. Phase 03 chuyển sang `READY TO START`. Final system vẫn `NOT RELEASED` cho đến khi Phase 03 có implementation và end-to-end evidence.