from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]


def resolve_project_path(path: str | Path) -> Path:
    value = Path(path)

    if value.is_absolute():
        return value

    return PROJECT_ROOT / value