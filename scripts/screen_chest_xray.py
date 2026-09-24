import sys
from pathlib import Path

from lung_xray_api.infrastructure.imaging.chest_xray_validator import (
    chest_xray_validator,
)


def main() -> None:

    if len(sys.argv) != 2:
        print(
            "Usage:"
            " python scripts/"
            "screen_chest_xray.py"
            " <image_path>"
        )
        return

    image_path = Path(
        sys.argv[1]
    )

    if not image_path.is_file():
        print(
            "File not found:",
            image_path,
        )
        return

    result = (
        chest_xray_validator.validate(
            image_path.read_bytes()
        )
    )

    print(
        "File:",
        image_path,
    )

    print(
        "Accepted:",
        result.accepted,
    )

    print(
        "Total score:",
        round(
            result.score,
            4,
        ),
    )

    print(
        "Grayscale:",
        round(
            result.grayscale_score,
            4,
        ),
    )

    print(
        "Contrast:",
        round(
            result.contrast_score,
            4,
        ),
    )

    print(
        "Texture:",
        round(
            result.texture_score,
            4,
        ),
    )

    print(
        "Aspect:",
        round(
            result.aspect_score,
            4,
        ),
    )

    print(
        "Method:",
        result.method,
    )


if __name__ == "__main__":
    main()