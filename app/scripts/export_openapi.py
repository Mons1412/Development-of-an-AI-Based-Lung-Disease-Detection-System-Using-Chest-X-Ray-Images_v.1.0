"""Export OpenAPI JSON from the real FastAPI app object."""

from __future__ import annotations

import json
from pathlib import Path

from lung_xray_api.main import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    output = PROJECT_ROOT / "handoff" / "mendix" / "openapi" / "lung-xray-api.openapi.json"
    app = create_app(load_model=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
