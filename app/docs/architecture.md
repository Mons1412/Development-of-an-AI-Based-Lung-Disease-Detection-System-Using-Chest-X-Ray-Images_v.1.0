# Architecture

## Mục tiêu

Phase 02 dùng kiến trúc phân lớp để giữ model artifact bất biến và tách HTTP khỏi inference logic.

## Dependency direction

```text
main
→ api
→ application
→ infrastructure.ml
→ artifacts
```

`core` chứa cấu hình, logging, security và lifespan dùng chung.

## Layer responsibilities

| Layer | Trách nhiệm |
| --- | --- |
| `api` | HTTP routes, dependency injection từ `request.app.state`, status code |
| `application` | Điều phối validate → preprocess → predict, tính latency |
| `infrastructure.ml` | Artifact contract, checksum, image pipeline, TensorFlow runtime |
| `schemas` | Public request/response models |
| `core` | Config, security, lifecycle và exception |

## Invariants

- Endpoint không đọc artifact JSON trực tiếp.
- `PredictionService` không phụ thuộc FastAPI.
- Model chỉ load một lần trong lifespan.
- Không retrain, fine-tune hoặc đổi weights trong Phase 02.
- Không double normalize ảnh.

## Generated và evidence

OpenAPI, examples, benchmark report và screenshots không phải source. Chúng chỉ được sinh sau khi code tương ứng chạy thật.
