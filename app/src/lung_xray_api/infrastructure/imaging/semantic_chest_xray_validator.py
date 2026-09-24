from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import json
from pathlib import Path
from threading import Lock

import numpy as np
from PIL import Image
import tensorflow as tf

from lung_xray_api.core.paths import (
    resolve_project_path,
)


@dataclass(frozen=True)
class ChestXrayValidationResult:
    accepted: bool
    probability: float
    threshold: float
    method: str


class SemanticChestXrayValidator:
    def __init__(self) -> None:
        self._artifact_path = (
            resolve_project_path(
                "app/artifacts/validators/"
                "chest_xray/1.0.0"
            )
        )

        self._model_path = (
            self._artifact_path
            / "chest_xray_validator.keras"
        )

        self._threshold_path = (
            self._artifact_path
            / "threshold_config.json"
        )

        self._model: tf.keras.Model | None = None
        self._threshold: float | None = None

        self._load_lock = Lock()

    def _ensure_loaded(self) -> None:
        if (
            self._model is not None
            and self._threshold is not None
        ):
            return

        with self._load_lock:
            if (
                self._model is not None
                and self._threshold is not None
            ):
                return

            if not self._model_path.is_file():
                raise RuntimeError(
                    "Chest X-ray validator model "
                    f"not found: {self._model_path}"
                )

            if not self._threshold_path.is_file():
                raise RuntimeError(
                    "Chest X-ray validator threshold "
                    f"not found: {self._threshold_path}"
                )

            threshold_config = json.loads(
                self._threshold_path.read_text(
                    encoding="utf-8"
                )
            )

            threshold = float(
                threshold_config["threshold"]
            )

            if not 0.0 < threshold < 1.0:
                raise RuntimeError(
                    "Invalid chest X-ray "
                    f"threshold: {threshold}"
                )

            model = tf.keras.models.load_model(
                self._model_path,
                compile=False,
                safe_mode=True,
            )

            if model.input_shape != (
                None,
                224,
                224,
                3,
            ):
                raise RuntimeError(
                    "Unexpected chest X-ray "
                    f"validator input shape: "
                    f"{model.input_shape}"
                )

            if model.output_shape != (
                None,
                1,
            ):
                raise RuntimeError(
                    "Unexpected chest X-ray "
                    f"validator output shape: "
                    f"{model.output_shape}"
                )

            self._model = model
            self._threshold = threshold

    @staticmethod
    def _preprocess(
        image_bytes: bytes,
    ) -> np.ndarray:
        with Image.open(
            BytesIO(image_bytes)
        ) as image:
            image = image.convert("RGB")

            image = image.resize(
                (224, 224),
                Image.Resampling.BILINEAR,
            )

            array = np.asarray(
                image,
                dtype=np.float32,
            )

        if array.shape != (
            224,
            224,
            3,
        ):
            raise ValueError(
                "Unexpected image shape "
                f"after preprocessing: "
                f"{array.shape}"
            )

        return np.expand_dims(
            array,
            axis=0,
        )

    def validate(
        self,
        image_bytes: bytes,
    ) -> ChestXrayValidationResult:
        self._ensure_loaded()

        if (
            self._model is None
            or self._threshold is None
        ):
            raise RuntimeError(
                "Chest X-ray validator "
                "failed to initialize."
            )

        batch = self._preprocess(
            image_bytes
        )

        output = self._model(
            batch,
            training=False,
        )

        probability = float(
            np.asarray(
                output
            ).reshape(-1)[0]
        )

        if not np.isfinite(
            probability
        ):
            raise RuntimeError(
                "Chest X-ray validator "
                "returned non-finite probability."
            )

        if not (
            0.0
            <= probability
            <= 1.0
        ):
            raise RuntimeError(
                "Chest X-ray validator "
                "returned probability outside "
                f"[0, 1]: {probability}"
            )

        accepted = (
            probability
            >= self._threshold
        )

        return ChestXrayValidationResult(
            accepted=accepted,
            probability=probability,
            threshold=self._threshold,
            method="semantic_model_v1",
        )


semantic_chest_xray_validator = (
    SemanticChestXrayValidator()
)