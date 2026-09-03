from io import BytesIO

import numpy as np
from PIL import Image, ImageOps


TARGET_WIDTH = 224
TARGET_HEIGHT = 224


class ImagePreprocessor:

    def preprocess(
        self,
        image_bytes: bytes,
    ) -> np.ndarray:

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

            image = image.convert("RGB")

            image = image.resize(
                (
                    TARGET_WIDTH,
                    TARGET_HEIGHT,
                ),
                Image.Resampling.BILINEAR,
            )

            array = np.asarray(
                image,
                dtype=np.float32,
            )

        expected_shape = (
            TARGET_HEIGHT,
            TARGET_WIDTH,
            3,
        )

        if array.shape != expected_shape:
            raise ValueError(
                "Unexpected image shape: "
                f"{array.shape}"
            )

        batch = np.expand_dims(
            array,
            axis=0,
        )

        return batch


image_preprocessor = ImagePreprocessor()