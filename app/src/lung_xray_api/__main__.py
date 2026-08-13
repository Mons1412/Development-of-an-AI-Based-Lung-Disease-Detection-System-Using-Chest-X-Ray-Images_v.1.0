"""CLI entrypoint cho local FastAPI server."""

from lung_xray_api.core.config import load_settings


def main() -> None:
    import uvicorn

    settings = load_settings()
    uvicorn.run(
        "lung_xray_api.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        workers=1,
    )


if __name__ == "__main__":
    main()
