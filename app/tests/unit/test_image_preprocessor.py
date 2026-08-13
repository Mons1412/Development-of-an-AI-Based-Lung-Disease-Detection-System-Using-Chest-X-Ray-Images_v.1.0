import numpy as np

from lung_xray_api.infrastructure.ml.artifact_bundle import ArtifactBundle
from lung_xray_api.infrastructure.ml.image_preprocessor import ImagePreprocessor
from lung_xray_api.infrastructure.ml.image_validator import ImageValidator
from tests.conftest import make_image_bytes


def test_preprocessor_outputs_raw_float32_batch(artifact_dir):
    bundle = ArtifactBundle.load(artifact_dir)
    image = ImageValidator(max_upload_bytes=1024 * 1024).validate(
        make_image_bytes(),
        filename="sample.jpg",
        content_type="image/jpeg",
    )

    batch = ImagePreprocessor(bundle).preprocess(image)

    assert batch.shape == (1, 224, 224, 3)
    assert batch.dtype == np.float32
    assert batch.min() >= 0
    assert batch.max() <= 255
