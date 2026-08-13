"""API v1 router composition."""

from fastapi import APIRouter

from lung_xray_api.api.v1 import analyses, assistant, demo, health, model_info, predict, report

router = APIRouter()
router.include_router(health.router)
router.include_router(model_info.router)
router.include_router(predict.router)
router.include_router(analyses.router)
router.include_router(assistant.router)
router.include_router(report.router)
router.include_router(demo.router)
