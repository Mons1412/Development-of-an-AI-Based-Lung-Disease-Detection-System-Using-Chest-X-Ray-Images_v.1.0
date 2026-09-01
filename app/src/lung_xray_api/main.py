from fastapi import FastAPI

from lung_xray_api.api.v1.auth import router as auth_router
from lung_xray_api.api.v1.health import router as health_router
from lung_xray_api.api.v1.users import router as users_router


app = FastAPI(
    title="LungXrayAI 2.0",
    version="2.0.0-dev",
)


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(users_router)