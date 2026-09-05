from __future__ import annotations

import argparse
from pathlib import Path

from lung_xray_api.infrastructure.imaging.semantic_chest_xray_validator import (
    semantic_chest_xray_validator,
)


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "image",
        type=Path,
    )

    args = parser.parse_args()

    image_path = args.image

    if not image_path.is_file():
        raise SystemExit(
            f"Image not found: {image_path}"
        )

    image_bytes = (
        image_path.read_bytes()
    )

    result = (
        semantic_chest_xray_validator.validate(
            image_bytes
        )
    )

    print(
        "Image:",
        image_path
    )

    print(
        "Accepted:",
        result.accepted
    )

    print(
        "P(CHEST_XRAY):",
        round(
            result.probability,
            6,
        )
    )

    print(
        "Threshold:",
        result.threshold
    )

    print(
        "Method:",
        result.method
    )


if __name__ == "__main__":
    main()