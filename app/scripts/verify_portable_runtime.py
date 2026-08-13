"""Verify that the packaged runtime can load and warm up the real model."""

from __future__ import annotations

from lung_xray_api.core.config import load_settings
from lung_xray_api.core.lifespan import build_prediction_service


def main() -> int:
    settings = load_settings()
    service, runtime = build_prediction_service(settings, warm_up=True)
    try:
        print(f"model_version={service.bundle.model_version}")
        print(f"class_names={','.join(service.bundle.class_names)}")
        print("model_load_and_warmup=PASS")
    finally:
        runtime.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
