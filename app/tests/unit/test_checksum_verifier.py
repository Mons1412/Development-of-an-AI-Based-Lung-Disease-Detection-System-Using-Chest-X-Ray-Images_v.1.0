from lung_xray_api.infrastructure.ml.checksum_verifier import verify_checksums


def test_verify_checksums_passes_for_model_package(artifact_dir):
    results = verify_checksums(artifact_dir)

    assert {item.file_name for item in results} >= {
        "lung_classifier_v1.keras",
        "class_indices.json",
        "preprocessing_config.json",
        "model_metadata.json",
        "inference_contract.json",
        "metrics.json",
        "model_runtime_requirements.txt",
    }
    assert all(item.ok for item in results)
