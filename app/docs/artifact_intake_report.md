# Artifact Intake Report

## Source

Artifact được giải nén từ:

```text
01_ml_training_colab/model_release/lung_classifier/1.1.0/lung_model_package_v1.zip
```

Vị trí Phase 02:

```text
02_fastapi_inference/artifacts/lung_classifier/1.1.0/
```

## Required files

| File | Lifecycle |
| --- | --- |
| `lung_classifier_v1.keras` | `[C]` |
| `class_indices.json` | `[C]` |
| `preprocessing_config.json` | `[C]` |
| `model_metadata.json` | `[C]` |
| `inference_contract.json` | `[C]` |
| `metrics.json` | `[C]` |
| `model_runtime_requirements.txt` | `[C]` |
| `checksums.json` | `[C]` |

## Locked contract

- Model version: `1.1.0`
- Class order: `0 → normal`, `1 → pneumonia`, `2 → tuberculosis`
- Input: `224 × 224 × 3`, RGB, `float32`, raw pixel range `[0,255]`
- Preprocessing: embedded in model
- Model SHA-256: `aae036ba1ac8a1b82fe6bfbf4834078564a6be07557f9bf5e4d1c7d0a9fcac2c`

Không sửa, format, rename hoặc regenerate các artifact này.
