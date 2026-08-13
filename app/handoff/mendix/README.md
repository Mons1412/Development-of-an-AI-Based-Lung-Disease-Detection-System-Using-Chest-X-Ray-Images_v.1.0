# Mendix Handoff

> **Handoff status:** LOCKED / READY FOR PHASE 03  
> **Contract version:** 1.0.0  
> **FastAPI release:** 1.0.0  
> **Model version:** 1.1.0  
> **Target phase:** Phase 03 - Mendix

## Status

Handoff này đã được sinh sau khi Phase 02 pass P0 gate ngày `2026-06-30`. OpenAPI được sinh từ `app.openapi()`. Response examples được sinh từ app/API thật bằng TestClient và model runtime thật cho success case.

Generated files:

```text
openapi/lung-xray-api.openapi.json
examples/prediction-success.json
examples/invalid-image.json
examples/file-too-large.json
examples/model-not-ready.json
```

Evidence screenshot đang pending manual capture:

```text
evidence/swagger-predict-success.png
evidence/demo-predict-success.png
```

## Base URL local

```text
http://127.0.0.1:8000
```

## Main endpoints

- `GET /health/live`
- `GET /health/ready`
- `GET /api/v1/model-info`
- `POST /api/v1/predict`
- `POST /predict`
- `GET /demo`

## Prediction response

Contract chính dùng nested probabilities:

```json
{
  "status": "success",
  "prediction": "pneumonia",
  "model_probability": 0.9936072826385498,
  "probabilities": {
    "normal": 0.005327203776687384,
    "pneumonia": 0.9936072826385498,
    "tuberculosis": 0.0010655076475813985
  },
  "model_version": "1.1.0",
  "processing_time_ms": 688,
  "disclaimer": "Kết quả chỉ phục vụ mục đích học thuật và không thay thế chẩn đoán của bác sĩ."
}
```

Response hiện tại cũng có flat fields `normal_probability`, `pneumonia_probability` và `tuberculosis_probability` để Mendix mapping thuận tiện hơn.

Kết quả chỉ phục vụ mục đích học thuật và không thay thế chẩn đoán của bác sĩ.