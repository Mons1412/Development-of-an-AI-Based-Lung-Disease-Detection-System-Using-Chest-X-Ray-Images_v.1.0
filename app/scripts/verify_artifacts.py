"""Verify immutable model artifacts for Phase 02."""

from __future__ import annotations

import argparse
from pathlib import Path

from lung_xray_api.core.config import load_settings
from lung_xray_api.infrastructure.ml.artifact_bundle import REQUIRED_FILES, ArtifactBundle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify lung classifier artifact bundle.")
    parser.add_argument("--artifact-dir", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = load_settings()
    artifact_dir = args.artifact_dir or settings.artifact_dir
    bundle = ArtifactBundle.load(artifact_dir, verify_checksum=True)
    print(f"artifact_dir={bundle.artifact_dir}")
    print(f"artifact_files={len(REQUIRED_FILES)}/{len(REQUIRED_FILES)}")
    print(f"model_version={bundle.model_version}")
    print(f"input_shape={bundle.metadata['input_shape']}")
    for index, class_name in enumerate(bundle.class_names):
        print(f"class_{index}={class_name}")
    print(f"preprocessing_location={bundle.preprocessing['preprocessing_location']}")
    print(f"embedded_layer={bundle.preprocessing['embedded_layer']}")
    print("checksum=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
