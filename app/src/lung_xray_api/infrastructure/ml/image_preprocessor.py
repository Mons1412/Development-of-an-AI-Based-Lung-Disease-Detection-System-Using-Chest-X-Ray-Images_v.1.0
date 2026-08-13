"""Preprocess ảnh theo đúng inference contract của model.

Pipeline deterministic: decode, convert RGB, resize bilinear, cast float32 và
thêm batch dimension. Không normalize về [-1, 1] ở đây vì model đã chứa layer
`Rescaling(scale=1/127.5, offset=-1)`.
"""

from __future__ import annotations

from io import BytesIO

import numpy as np
from PIL import Image

from lung_xray_api.infrastructure.ml.artifact_bundle import ArtifactBundle
from lung_xray_api.infrastructure.ml.image_validator import ValidatedImage


class ImagePreprocessor:
    def __init__(self, bundle: ArtifactBundle) -> None:
        self.input_height, self.input_width = bundle.input_size

    def preprocess(self, image: ValidatedImage) -> np.ndarray:
        with Image.open(BytesIO(image.content)) as opened:
            rgb = opened.convert("RGB")
            resized = rgb.resize((self.input_width, self.input_height), Image.Resampling.BILINEAR)
            array = np.asarray(resized, dtype=np.float32)

        if array.shape != (self.input_height, self.input_width, 3):
            raise ValueError(f"Shape ảnh sau preprocess không hợp lệ: {array.shape}")

        return np.expand_dims(array, axis=0)
