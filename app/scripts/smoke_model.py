"""Run real model smoke inference for one local image."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lung_xray_api.application.prediction_service import PredictionService
from lung_xray_api.core.config import load_settings
from lung_xray_api.infrastructure.ml.artifact_bundle import ArtifactBundle
from lung_xray_api.infrastructure.ml.image_preprocessor import ImagePreprocessor
from lung_xray_api.infrastructure.ml.image_validator import ImageValidator
from lung_xray_api.infrastructure.ml.model_runtime import ModelRuntime
from lung_xray_api.infrastructure.ml.predictor import Predictor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test real model with a local image.")
    parser.add_argument("--image", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.image.is_file():
        print("PENDING INPUT FIXTURE: --image phải trỏ đến ảnh X-quang hợp lệ", file=sys.stderr)
        return 2

    settings = load_settings()
    bundle = ArtifactBundle.load(settings.artifact_dir)
    runtime = ModelRuntime(bundle)
    runtime.load(warm_up=True)
    service = PredictionService(
        bundle=bundle,
        validator=ImageValidator(settings.max_upload_bytes),
        preprocessor=ImagePreprocessor(bundle),
        predictor=Predictor(bundle, runtime),
    )
    result = service.predict_bytes(args.image.read_bytes(), args.image.name, None)
    print(result.to_response())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
