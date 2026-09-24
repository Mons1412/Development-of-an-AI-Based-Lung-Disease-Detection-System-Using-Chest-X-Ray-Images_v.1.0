from dataclasses import dataclass
from io import BytesIO

import numpy as np
from PIL import Image, ImageOps


@dataclass(frozen=True)
class ChestXrayScreeningResult:
    accepted: bool

    score: float

    grayscale_score: float
    contrast_score: float
    texture_score: float
    aspect_score: float

    method: str = "heuristic_v1"


class ChestXrayValidator:

    @staticmethod
    def _clamp01(
        value: float,
    ) -> float:
        return max(
            0.0,
            min(
                1.0,
                float(value),
            ),
        )

    def validate(
        self,
        image_bytes: bytes,
    ) -> ChestXrayScreeningResult:

        if not image_bytes:
            raise ValueError(
                "Image data is empty."
            )

        with Image.open(
            BytesIO(image_bytes)
        ) as image:

            image = ImageOps.exif_transpose(
                image
            )

            width, height = image.size

            rgb_image = image.convert(
                "RGB"
            )

            rgb_image.thumbnail(
                (512, 512),
                Image.Resampling.BILINEAR,
            )

            rgb = np.asarray(
                rgb_image,
                dtype=np.float32,
            )

        #
        # 1. Grayscale similarity
        #
        channel_max = rgb.max(
            axis=2
        )

        channel_min = rgb.min(
            axis=2
        )

        mean_channel_spread = float(
            np.mean(
                channel_max
                - channel_min
            )
        )

        grayscale_score = (
            self._clamp01(
                1.0
                - (
                    mean_channel_spread
                    / 35.0
                )
            )
        )

        #
        # 2. Convert RGB -> grayscale
        #
        gray = (
            0.299 * rgb[:, :, 0]
            + 0.587 * rgb[:, :, 1]
            + 0.114 * rgb[:, :, 2]
        )

        #
        # 3. Dynamic range / contrast
        #
        percentile_1 = float(
            np.percentile(
                gray,
                1,
            )
        )

        percentile_99 = float(
            np.percentile(
                gray,
                99,
            )
        )

        dynamic_range = (
            percentile_99
            - percentile_1
        )

        contrast_score = (
            self._clamp01(
                (
                    dynamic_range
                    - 30.0
                )
                / 90.0
            )
        )

        #
        # 4. Texture
        #
        standard_deviation = float(
            np.std(gray)
        )

        texture_score = (
            self._clamp01(
                (
                    standard_deviation
                    - 15.0
                )
                / 45.0
            )
        )

        #
        # 5. Aspect ratio
        #
        aspect_ratio = (
            width / height
        )

        if (
            0.60
            <= aspect_ratio
            <= 1.35
        ):
            aspect_score = 1.0

        elif (
            0.50
            <= aspect_ratio
            <= 1.60
        ):
            aspect_score = 0.5

        else:
            aspect_score = 0.0

        #
        # Final heuristic score
        #
        score = (
            0.50 * grayscale_score
            + 0.25 * contrast_score
            + 0.15 * texture_score
            + 0.10 * aspect_score
        )

        accepted = (
            score >= 0.62
            and grayscale_score >= 0.72
            and contrast_score >= 0.15
        )

        return ChestXrayScreeningResult(
            accepted=accepted,
            score=float(score),
            grayscale_score=float(
                grayscale_score
            ),
            contrast_score=float(
                contrast_score
            ),
            texture_score=float(
                texture_score
            ),
            aspect_score=float(
                aspect_score
            ),
        )


chest_xray_validator = (
    ChestXrayValidator()
)