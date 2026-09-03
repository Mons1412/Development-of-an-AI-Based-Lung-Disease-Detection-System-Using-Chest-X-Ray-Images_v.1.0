from dataclasses import dataclass

import numpy as np
import tensorflow as tf

from lung_xray_api.core.paths import resolve_project_path


MODEL_FILENAME = "lung_classifier_v1.keras"

EXPECTED_HEIGHT = 224
EXPECTED_WIDTH = 224
EXPECTED_CHANNELS = 3


@dataclass(frozen=True)
class RuntimePrediction:
    predicted_class: str
    confidence: float
    probabilities: dict[str, float]


class ModelRuntime:

    def __init__(
        self,
        *,
        artifact_path: str,
        class_names: list[str],
    ) -> None:

        self.artifact_directory = (
            resolve_project_path(
                artifact_path
            )
        )

        self.model_path = (
            self.artifact_directory
            / MODEL_FILENAME
        )

        self.class_names = tuple(
            class_names
        )

        self.model = self._load_model()

        self._validate_model_contract()

        self._warm_up()

    def _load_model(self):

        if not self.model_path.is_file():
            raise FileNotFoundError(
                "Model file not found: "
                f"{self.model_path}"
            )

        return tf.keras.models.load_model(
            self.model_path,
            compile=False,
            safe_mode=True,
        )

    def _validate_model_contract(
        self,
    ) -> None:

        expected_input = (
            EXPECTED_HEIGHT,
            EXPECTED_WIDTH,
            EXPECTED_CHANNELS,
        )

        actual_input = tuple(
            self.model.input_shape[1:]
        )

        if actual_input != expected_input:
            raise RuntimeError(
                "Model input shape mismatch. "
                f"Expected {expected_input}, "
                f"received {actual_input}."
            )

        output_size = int(
            self.model.output_shape[-1]
        )

        if output_size != len(
            self.class_names
        ):
            raise RuntimeError(
                "Model output/class mismatch. "
                f"Output={output_size}, "
                f"classes={len(self.class_names)}."
            )

    def _warm_up(
        self,
    ) -> None:

        batch = np.zeros(
            (
                1,
                EXPECTED_HEIGHT,
                EXPECTED_WIDTH,
                EXPECTED_CHANNELS,
            ),
            dtype=np.float32,
        )

        self.model(
            batch,
            training=False,
        )

    def predict(
        self,
        batch: np.ndarray,
    ) -> RuntimePrediction:

        expected_shape = (
            1,
            EXPECTED_HEIGHT,
            EXPECTED_WIDTH,
            EXPECTED_CHANNELS,
        )

        if batch.shape != expected_shape:
            raise ValueError(
                "Invalid input batch shape. "
                f"Expected {expected_shape}, "
                f"received {batch.shape}."
            )

        outputs = self.model(
            batch,
            training=False,
        )

        probabilities = np.asarray(
            outputs,
            dtype=np.float32,
        )

        if probabilities.shape != (
            1,
            len(self.class_names),
        ):
            raise RuntimeError(
                "Unexpected model output shape: "
                f"{probabilities.shape}"
            )

        values = probabilities[0]

        if not np.all(
            np.isfinite(values)
        ):
            raise RuntimeError(
                "Model returned non-finite values."
            )

        probability_sum = float(
            values.sum()
        )

        if not np.isclose(
            probability_sum,
            1.0,
            atol=1e-3,
        ):
            raise RuntimeError(
                "Model output does not look like "
                "softmax probabilities. "
                f"Sum={probability_sum}"
            )

        predicted_index = int(
            np.argmax(values)
        )

        predicted_class = (
            self.class_names[
                predicted_index
            ]
        )

        confidence = float(
            values[predicted_index]
        )

        probability_map = {
            class_name: float(probability)
            for class_name, probability
            in zip(
                self.class_names,
                values,
            )
        }

        return RuntimePrediction(
            predicted_class=predicted_class,
            confidence=confidence,
            probabilities=probability_map,
        )