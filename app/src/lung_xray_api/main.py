from pathlib import Path

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from lung_xray_api.api.v1.admin import (
    router as admin_router,
)
from lung_xray_api.api.v1.analyses import (
    router as analyses_router,
)
from lung_xray_api.api.v1.auth import (
    router as auth_router,
)
from lung_xray_api.api.v1.health import (
    router as health_router,
)
from lung_xray_api.api.v1.models import (
    router as models_router,
)
from lung_xray_api.api.v1.medical_histories import (
    router as medical_histories_router,
)
from lung_xray_api.api.v1.patient_profiles import (
    router as patient_profiles_router,
)
from lung_xray_api.api.v1.users import (
    router as users_router,
)


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[3]
)

FRONTEND_DIR = (
    PROJECT_ROOT
    / "frontend"
)


if not FRONTEND_DIR.exists():
    raise RuntimeError(
        "Frontend directory was not found: "
        f"{FRONTEND_DIR}"
    )


app = FastAPI(
    title="LungXrayAI 2.0",
    version="1.5.0-dev",
)


app.include_router(
    health_router
)

app.include_router(
    auth_router
)

app.include_router(
    users_router
)

app.include_router(
    admin_router
)

app.include_router(
    models_router
)

app.include_router(
    analyses_router
)

app.include_router(
    patient_profiles_router
)

app.include_router(
    medical_histories_router
)

app.mount(
    "/frontend",
    StaticFiles(
        directory=str(
            FRONTEND_DIR
        )
    ),
    name="frontend",
)


@app.get(
    "/",
    include_in_schema=False,
)
def frontend_home():
    return FileResponse(
        FRONTEND_DIR
        / "index.html"
    )


def _patch_multipart_binary_field(
    openapi_schema: dict,
    *,
    path: str,
    field_name: str,
    multiple: bool,
    description: str,
) -> None:
    try:
        request_schema = (
            openapi_schema
            ["paths"]
            [path]
            ["post"]
            ["requestBody"]
            ["content"]
            ["multipart/form-data"]
            ["schema"]
        )

        ref_value = (
            request_schema
            .get("$ref")
        )

        if not ref_value:
            return

        schema_name = (
            ref_value
            .split("/")[-1]
        )

        body_schema = (
            openapi_schema
            ["components"]
            ["schemas"]
            .get(schema_name)
        )

        if not body_schema:
            return

        properties = (
            body_schema
            .get(
                "properties",
                {}
            )
        )

        if (
            field_name
            not in properties
        ):
            return

        if multiple:
            properties[field_name] = {
                "type": "array",
                "items": {
                    "type": "string",
                    "format": "binary",
                },
                "title": "Files",
                "description": (
                    description
                ),
            }

        else:
            properties[field_name] = {
                "type": "string",
                "format": "binary",
                "title": "File",
                "description": (
                    description
                ),
            }

    except KeyError:
        return


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    _patch_multipart_binary_field(
        openapi_schema,
        path="/api/v1/analyses",
        field_name="file",
        multiple=False,
        description=(
            "Chest X-ray image file."
        ),
    )

    _patch_multipart_binary_field(
        openapi_schema,
        path=(
            "/api/v1/analyses/batch"
        ),
        field_name="files",
        multiple=True,
        description=(
            "Select multiple image files "
            "for batch analysis."
        ),
    )

    app.openapi_schema = (
        openapi_schema
    )

    return app.openapi_schema


app.openapi = custom_openapi