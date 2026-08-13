import numpy as np

from lung_xray_api.application.prediction_service import PredictionService
from lung_xray_api.infrastructure.ml.artifact_bundle import ArtifactBundle
from lung_xray_api.infrastructure.ml.image_preprocessor import ImagePreprocessor
from lung_xray_api.infrastructure.ml.image_validator import ImageValidator
from lung_xray_api.infrastructure.ml.predictor import Predictor
from tests.conftest import make_image_bytes


class FakeRuntime:
    def predict_batch(self, batch):
        return np.asarray([[0.1, 0.8, 0.1]], dtype=np.float32)


def test_prediction_service_returns_contract(artifact_dir):
    bundle = ArtifactBundle.load(artifact_dir)
    service = PredictionService(
        bundle=bundle,
        validator=ImageValidator(max_upload_bytes=1024 * 1024),
        preprocessor=ImagePreprocessor(bundle),
        predictor=Predictor(bundle, FakeRuntime()),
    )

    result = service.predict_bytes(make_image_bytes(), "sample.jpg", "image/jpeg")

    assert result.prediction == "pneumonia"
    assert result.model_version == "1.1.0"
    assert result.probabilities["pneumonia"] > 0.7
