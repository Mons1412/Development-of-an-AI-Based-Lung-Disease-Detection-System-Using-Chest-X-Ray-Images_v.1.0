"""Benchmark real model latency with a provided local image."""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path
from time import perf_counter

from lung_xray_api.application.prediction_service import PredictionService
from lung_xray_api.core.config import load_settings
from lung_xray_api.infrastructure.ml.artifact_bundle import ArtifactBundle
from lung_xray_api.infrastructure.ml.image_preprocessor import ImagePreprocessor
from lung_xray_api.infrastructure.ml.image_validator import ImageValidator
from lung_xray_api.infrastructure.ml.model_runtime import ModelRuntime
from lung_xray_api.infrastructure.ml.predictor import Predictor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark real model inference.")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=10)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.image.is_file():
        print("PENDING INPUT FIXTURE: --image phải trỏ đến ảnh X-quang hợp lệ", file=sys.stderr)
        return 2

    settings = load_settings()
    bundle = ArtifactBundle.load(settings.artifact_dir)
    runtime = ModelRuntime(bundle)
    load_stats = runtime.load(warm_up=True)
    service = PredictionService(
        bundle=bundle,
        validator=ImageValidator(settings.max_upload_bytes),
        preprocessor=ImagePreprocessor(bundle),
        predictor=Predictor(bundle, runtime),
    )
    content = args.image.read_bytes()
    latencies: list[int] = []
    for _ in range(args.runs):
        start = perf_counter()
        service.predict_bytes(content, args.image.name, None)
        latencies.append(int((perf_counter() - start) * 1000))

    print(f"runs={args.runs}")
    print(f"load_time_ms={load_stats.load_time_ms}")
    print(f"warmup_time_ms={load_stats.warmup_time_ms}")
    print(f"mean_ms={statistics.mean(latencies):.2f}")
    print(f"median_ms={statistics.median(latencies):.2f}")
    print(f"p95_ms={sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
