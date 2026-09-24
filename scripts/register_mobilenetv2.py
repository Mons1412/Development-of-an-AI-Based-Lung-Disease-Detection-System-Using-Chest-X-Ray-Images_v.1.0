from pathlib import Path

from lung_xray_api.infrastructure.persistence.database import SessionLocal
from lung_xray_api.infrastructure.persistence.repositories.ai_model_repository import (
    AIModelRepository,
)


MODEL_KEY = "mobilenetv2"
MODEL_VERSION = "1.1.0"

ARTIFACT_PATH = (
    "app/artifacts/models/"
    "mobilenetv2/1.1.0"
)

REQUIRED_FILES = [
    "lung_classifier_v1.keras",
    "class_indices.json",
    "preprocessing_config.json",
    "model_metadata.json",
    "inference_contract.json",
    "metrics.json",
    "model_runtime_requirements.txt",
    "checksums.json",
]


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]

    artifact_directory = (
        project_root / ARTIFACT_PATH
    )

    missing_files = [
        filename
        for filename in REQUIRED_FILES
        if not (
            artifact_directory / filename
        ).is_file()
    ]

    if missing_files:
        print(
            "Cannot register model. "
            "Missing artifact files:"
        )

        for filename in missing_files:
            print(f"- {filename}")

        return

    repository = AIModelRepository()
    db = SessionLocal()

    try:
        existing = repository.get_by_key_version(
            db,
            model_key=MODEL_KEY,
            version=MODEL_VERSION,
        )

        if existing is not None:
            print(
                "Model already registered: "
                f"id={existing.id}, "
                f"key={existing.model_key}, "
                f"version={existing.version}"
            )
            return

        model = repository.create(
            db,
            model_key=MODEL_KEY,
            display_name="MobileNetV2",
            architecture="MobileNetV2",
            version=MODEL_VERSION,
            artifact_path=ARTIFACT_PATH,
            class_names=[
                "normal",
                "pneumonia",
                "tuberculosis",
            ],
            is_active=True,
            is_default=True,
        )

        print(
            "Model registered: "
            f"id={model.id}, "
            f"key={model.model_key}, "
            f"version={model.version}, "
            f"default={model.is_default}"
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()