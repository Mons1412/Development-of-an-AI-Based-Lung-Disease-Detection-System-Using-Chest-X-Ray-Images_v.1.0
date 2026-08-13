# Local Runbook

## Setup

```powershell
cd 02_fastapi_inference
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Yêu cầu Python `>=3.12,<3.13`.

## Verify artifact

```powershell
python scripts\verify_artifacts.py
```

## Run API

```powershell
python -m lung_xray_api
```

Default local URL:

```text
http://127.0.0.1:8000
```

## Tests

```powershell
python -m compileall src scripts tests
pytest tests\unit -q
pytest tests\integration -q
pytest -q
```

## Smoke model

Smoke model cần ảnh X-quang local hợp lệ:

```powershell
python scripts\smoke_model.py --image <VALID_LOCAL_XRAY_PATH>
```

Không dùng ảnh placeholder để tuyên bố smoke model pass.
