from fastapi import FastAPI

from lung_xray_api.api.v1.health import router as health_router


app = FastAPI(
    title="LungXrayAI 2.0",
    version="2.0.0-dev",
)

app.include_router(health_router)