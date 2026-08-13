# Frontend State Contract

Một application store duy nhất quản lý:

- selected `File` và session-only Object URL;
- phase: idle, selected, loading, success, error;
- patient code/name/source/anonymous/confirmed/parsed date;
- current persisted prediction;
- current `analysisId`.

Không dùng `window.lungXrayAssistantContext`. Controller giao tiếp qua store và CustomEvent:

- `lungxray:analysis-completed`
- `lungxray:analysis-reset`
- `lungxray:history-changed`

Chọn/xóa ảnh, lỗi prediction hoặc reset phải xóa current result và assistant context. Mở history không tự thay current assistant context.
