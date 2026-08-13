"""Verify that the deployed artifact still matches the approved Phase 1 model.

This command validates immutable artifact checksums plus the exact class order,
input contract, preprocessing location, and model hash used by the original
portable release. It does not estimate clinical accuracy or replace an
independent evaluation dataset.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from lung_xray_api.infrastructure.ml.artifact_bundle import ArtifactBundle

EXPECTED_MODEL_SHA256 = "aae036ba1ac8a1b82fe6bfbf4834078564a6be07557f9bf5e4d1c7d0a9fcac2c"
EXPECTED_MODEL_VERSION = "1.1.0"
EXPECTED_CLASSES = ("normal", "pneumonia", "tuberculosis")
EXPECTED_INPUT_SHAPE = (224, 224, 3)
EXPECTED_EMBEDDED_LAYER = "Rescaling(scale=1/127.5, offset=-1)"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify parity with the approved Phase 1 MobileNetV2 artifact."
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=Path("artifacts/lung_classifier/1.1.0"),
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    args = parse_args()
    bundle = ArtifactBundle.load(args.artifact_dir, verify_checksum=True)
    model_path = args.artifact_dir / "lung_classifier_v1.keras"
    failures: list[str] = []

    actual_hash = sha256_file(model_path)
    if actual_hash != EXPECTED_MODEL_SHA256:
        failures.append("model SHA-256 differs from the approved Phase 1 artifact")
    if bundle.model_version != EXPECTED_MODEL_VERSION:
        failures.append("model_version is not 1.1.0")
    if tuple(bundle.class_names) != EXPECTED_CLASSES:
        failures.append("class order differs from normal, pneumonia, tuberculosis")
    if tuple(bundle.metadata.get("input_shape", ())) != EXPECTED_INPUT_SHAPE:
        failures.append("input shape differs from 224x224x3")
    if bundle.preprocessing.get("preprocessing_location") != "embedded_in_model":
        failures.append("preprocessing is no longer embedded in the model")
    if bundle.preprocessing.get("embedded_layer") != EXPECTED_EMBEDDED_LAYER:
        failures.append("embedded Rescaling contract differs from Phase 1")
    if bundle.preprocessing.get("raw_pixel_range") != [0, 255]:
        failures.append("raw pixel range differs from [0, 255]")

    print(f"artifact_dir={bundle.artifact_dir}")
    print(f"model_sha256={actual_hash}")
    print(f"model_version={bundle.model_version}")
    print(f"class_order={','.join(bundle.class_names)}")
    print(f"input_shape={bundle.metadata.get('input_shape')}")
    print(f"preprocessing_location={bundle.preprocessing.get('preprocessing_location')}")
    print(f"embedded_layer={bundle.preprocessing.get('embedded_layer')}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print("phase1_parity=PASS")
    print("clinical_validation=NOT_ASSERTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
