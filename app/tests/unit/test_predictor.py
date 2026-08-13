import numpy as np
import pytest

from lung_xray_api.core.exceptions import ModelRuntimeError
from lung_xray_api.infrastructure.ml.artifact_bundle import ArtifactBundle
from lung_xray_api.infrastructure.ml.predictor import Predictor


class FakeRuntime:
    def __init__(self, output):
        self.output = np.asarray(output, dtype=np.float32)

    def predict_batch(self, batch):
        return self.output


def test_predictor_maps_argmax_to_class(artifact_dir):
    bundle = ArtifactBundle.load(artifact_dir)
    predictor = Predictor(bundle, FakeRuntime([[0.1, 0.8, 0.1]]))

    result = predictor.predict(np.zeros((1, 224, 224, 3), dtype=np.float32))

    assert result.prediction == "pneumonia"
    assert result.model_probability == pytest.approx(0.8)


def test_predictor_rejects_invalid_shape(artifact_dir):
    bundle = ArtifactBundle.load(artifact_dir)
    predictor = Predictor(bundle, FakeRuntime([[0.5, 0.5]]))

    with pytest.raises(ModelRuntimeError):
        predictor.predict(np.zeros((1, 224, 224, 3), dtype=np.float32))


def test_predictor_preserves_raw_argmax_before_normalization(artifact_dir, monkeypatch):
    bundle = ArtifactBundle.load(artifact_dir)
    predictor = Predictor(bundle, FakeRuntime([[0.4, 0.35, 0.25]]))

    monkeypatch.setattr(
        "lung_xray_api.infrastructure.ml.predictor.normalize_probabilities",
        lambda _raw: {"normal": 0.2, "pneumonia": 0.3, "tuberculosis": 0.5},
    )

    result = predictor.predict(np.zeros((1, 224, 224, 3), dtype=np.float32))

    assert result.prediction == "normal"
    assert result.model_probability == pytest.approx(0.2)
