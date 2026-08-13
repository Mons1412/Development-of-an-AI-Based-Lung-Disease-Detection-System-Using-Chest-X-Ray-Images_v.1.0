# Endpoint Matrix

| Environment | Base URL | API key | Status |
| --- | --- | --- | --- |
| Local FastAPI | `http://127.0.0.1:8000` | Off by default | READY FOR PHASE 03 |

Nếu bật API key, Mendix gửi header:

```text
X-API-Key: <local key>
```

Không hard-code secret trong Mendix hoặc JavaScript public.