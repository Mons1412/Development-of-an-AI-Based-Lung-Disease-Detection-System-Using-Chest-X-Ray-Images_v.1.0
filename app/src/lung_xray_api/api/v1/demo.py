"""Route hiển thị giao diện kiểm thử FastAPI Phase 02.

Module này chỉ render HTML. Toàn bộ logic phân loại vẫn đi qua
`POST /api/v1/predict`, vì vậy UI không chứa hoặc tải lại model.
"""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from lung_xray_api.web.assets import (
    FRONTEND_ASSET_VERSION,
    FRONTEND_STATIC_BASE,
    frontend_asset_url,
)

router = APIRouter(tags=["demo"], include_in_schema=False)

_WEB_DIR = Path(__file__).resolve().parents[2] / "web"
_templates = Jinja2Templates(directory=str(_WEB_DIR / "templates"))


@router.get("/demo", response_class=HTMLResponse)
def render_demo(request: Request) -> HTMLResponse:
    """Render trang demo kỹ thuật cho API inference."""
    return _templates.TemplateResponse(
        request=request,
        name="demo.html",
        context={
            "request": request,
            "frontend_asset_url": frontend_asset_url,
            "frontend_asset_version": FRONTEND_ASSET_VERSION,
            "frontend_static_base": FRONTEND_STATIC_BASE,
        },
    )
