"""Smoke test API routes with TestClient."""

from __future__ import annotations

from fastapi.testclient import TestClient

from lung_xray_api.main import create_app


def main() -> int:
    app = create_app(load_model=False)
    with TestClient(app) as client:
        live = client.get("/health/live")
        ready = client.get("/health/ready")
    print(f"/health/live={live.status_code}")
    print(f"/health/ready={ready.status_code}")
    return 0 if live.status_code == 200 and ready.status_code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
