# Final API Contract

## Legacy compatibility

- `POST /api/v1/predict`
- `POST /predict`

Hai endpoint trên không yêu cầu metadata và không tự lưu lịch sử.

## Persisted analysis

- `POST /api/v1/analyses/parse-filename`
- `POST /api/v1/analyses`
- `GET /api/v1/analyses`
- `GET /api/v1/analyses/{analysis_id}`
- `GET /api/v1/analyses/{analysis_id}/thumbnail`
- `DELETE /api/v1/analyses/{analysis_id}`
- `GET /api/v1/analyses/{analysis_id}/report`

`POST /api/v1/analyses` dùng multipart gồm `file`, `patient_display_name`, optional `patient_code`, `patient_name_source`, `patient_info_confirmed`, `is_anonymous_sample`.

## Assistant

- `POST /api/v1/assistant/query`

Request chứa message, application stage và optional current prediction context. Không gửi ảnh hoặc patient identity vào assistant.

## Privacy and cache

Analyses, thumbnail và persisted report dùng `no-store`. API history từ chối client không phải loopback khi chưa có auth/role model.
