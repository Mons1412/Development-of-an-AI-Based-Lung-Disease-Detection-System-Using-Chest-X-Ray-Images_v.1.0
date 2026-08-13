# Mendix Field Map

## Prediction response

| JSON field | Mendix type gợi ý | Ghi chú |
| --- | --- | --- |
| `status` | String | `success` hoặc `error` |
| `prediction` | String | `normal`, `pneumonia`, `tuberculosis` |
| `model_probability` | Decimal | Probability của class argmax |
| `probabilities.normal` | Decimal | Probability lớp normal |
| `probabilities.pneumonia` | Decimal | Probability lớp pneumonia |
| `probabilities.tuberculosis` | Decimal | Probability lớp tuberculosis |
| `model_version` | String | `1.1.0` |
| `processing_time_ms` | Integer | Latency phía FastAPI |
| `disclaimer` | String | Hiển thị trên result page |

Không diễn giải probability là độ tin cậy lâm sàng.
