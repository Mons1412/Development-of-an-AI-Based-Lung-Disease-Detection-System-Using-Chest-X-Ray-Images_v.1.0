# API Contract

> **Document status:** LOCKED  
> **Contract version:** 1.0.0  
> **Phase:** 02 - FastAPI Inference  
> **Audit date:** 2026-06-30  
> **Lock status:** LOCKED

Contract này phản ánh API runtime đã chạy thật và OpenAPI đã được sinh từ `app.openapi()` ngày `2026-06-30`.

Kết quả chỉ phục vụ mục đích học thuật và không thay thế chẩn đoán của bác sĩ.

## Health

| Method | Path | Response |
| --- | --- | --- |
| `GET` | `/health/live` | Process liveness |
| `GET` | `/health/ready` | Model readiness |

## Model info

```text
GET /api/v1/model-info
```

Response gồm model name, version, architecture, classes, input shape, preprocessing, metrics và disclaimer.

## Prediction

```text
POST /api/v1/predict
POST /predict
```

`/predict` là compatibility alias theo `inference_contract.json`; logic dùng chung service với `/api/v1/predict`.

Request:

```text
Content-Type: multipart/form-data
Field name: file
Allowed formats: JPG, JPEG, PNG
Max file size: 10 MB
```

Response success bắt buộc:

```text
status
prediction
model_probability
probabilities
model_version
processing_time_ms
disclaimer
```

`probabilities` là object lồng nhau:

```json
{
  "normal": 0.005327203776687384,
  "pneumonia": 0.9936072826385498,
  "tuberculosis": 0.0010655076475813985
}
```

Response hiện tại cũng trả các flat fields để thuận tiện cho Mendix mapping:

```text
normal_probability
pneumonia_probability
tuberculosis_probability
```

Class order bị khóa:

```text
0 -> normal
1 -> pneumonia
2 -> tuberculosis
```

## Error taxonomy

| Code | HTTP | Khi nào |
| --- | ---: | --- |
| `invalid_image` | 400 | File rỗng, quá lớn, MIME/extension sai hoặc decode fail |
| `model_not_ready` | 503 | Artifact/model runtime chưa sẵn sàng |
| `unauthorized` | 401 | API key bật nhưng request thiếu hoặc sai key |

Error response không trả stack trace, path cá nhân hoặc thông tin nội bộ nhạy cảm.