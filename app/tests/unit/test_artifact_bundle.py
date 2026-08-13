from lung_xray_api.infrastructure.ml.artifact_bundle import ArtifactBundle


def test_artifact_bundle_loads_contract(artifact_dir):
    bundle = ArtifactBundle.load(artifact_dir)

    assert bundle.model_version == "1.1.0"
    assert bundle.class_names == ["normal", "pneumonia", "tuberculosis"]
    assert bundle.input_size == (224, 224)
    assert bundle.preprocessing["preprocessing_location"] == "embedded_in_model"
