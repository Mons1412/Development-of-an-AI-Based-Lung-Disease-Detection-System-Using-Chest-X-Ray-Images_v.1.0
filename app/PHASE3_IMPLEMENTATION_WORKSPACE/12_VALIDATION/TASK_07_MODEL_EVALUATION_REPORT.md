# TASK 07 — Offline Model Evaluation Tooling

**Status:** Implemented and automated checks passed on 2026-07-27.

## Scope and safeguards

- Added offline-only evaluation tooling; no user-facing demo files, model architecture,
  model weights, assistant integration, database, or external API were changed.
- The tool evaluates only local files explicitly supplied by the operator. No evaluation
  images are committed: `/evaluation_dataset/` and `/var/evaluation/` are ignored by Git.
- The tool does not call a network service and does not retrain, write, or replace the
  production model.
- An accuracy value is published only when the operator explicitly passes
  `--ground-truth-confirmed`. Otherwise the computed comparison is retained as
  `folder_label_accuracy`, clearly labelled as unconfirmed folder-label evidence.

## Architecture implemented

`scripts/evaluate_dataset.py` uses the production composition root
`build_prediction_service(load_settings(), warm_up=True)`. Therefore each accepted image
passes the existing production `ImageValidator`, `ImagePreprocessor`, and `Predictor`
through `PredictionService.predict_bytes`, rather than duplicating preprocessing or
loading model artifacts directly.

The script uses only the Python standard library for discovery, CSV/JSON output,
confusion-matrix generation, metrics, and latency calculation. It streams no images to a
remote service. The runtime is closed in `finally` after prediction work finishes.

## Dataset and command contract

Expected input structure:

```text
evaluation_dataset/
├── normal/
├── pneumonia/
└── tuberculosis/
```

- Supported files: `.jpg`, `.jpeg`, `.png` (case-insensitive).
- Missing expected folders, empty expected folders, unexpected top-level folders,
  unsupported extensions, invalid images, and failed inferences are reported rather than
  silently treated as successes.
- `--limit-per-class` limits each class; `--max-samples` uses deterministic round-robin
  selection across classes and records the selection rule in the summary.
- `--dataset-id` and `--dataset-source` record provenance. The report warns when source
  metadata is absent.
- `--training-overlap-reviewed` records that possible training-set overlap was reviewed;
  without it, the tool warns that no held-out accuracy claim is valid.

Standard Windows run:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe scripts\evaluate_dataset.py `
  --dataset-root evaluation_dataset `
  --output-dir var\evaluation `
  --dataset-id "<DATASET_ID>" `
  --dataset-source "<LABEL_PROVENANCE>"
```

For a fixed 200-image evaluation set, use `--max-samples 200`; the tool never assumes
that 200 images exist and records the actual selected count. Add
`--ground-truth-confirmed` and `--training-overlap-reviewed` only after those statements
have been independently verified. The same operational instructions are in `README.md`.

## Output contract

The requested output directory contains only known report artifacts:

| File | Content |
| --- | --- |
| `predictions.csv` | Dataset-relative path, folder label, prediction, all three class probabilities, model probability, latency, model version, and skip status. |
| `skipped_files.csv` | Unsupported, invalid, or failed files with reason and detail. |
| `confusion_matrix.csv` | Ground-truth rows and `normal`, `pneumonia`, `tuberculosis` prediction columns. |
| `metrics.json` | Folder-label accuracy, conditional confirmed accuracy, per-class precision/recall/F1, macro and weighted precision/recall/F1, matrix, and mean/median/p95 latency. |
| `evaluation_summary.json` | Timestamp, dataset metadata, model version, environment, selection rule, counts, skip reasons, warnings, and the metrics. |

The tool rejects an output directory inside the dataset root and requires `--overwrite`
before it replaces any known evaluation artifact.

## Files changed

| Path | Change |
| --- | --- |
| `scripts/evaluate_dataset.py` | New offline evaluation CLI. |
| `tests/unit/test_evaluate_dataset.py` | Five mocked-inference unit tests; no TensorFlow/model artifact/image fixture is required. |
| `.gitignore` | Ignores local evaluation datasets and default generated output. |
| `README.md` | Documents normal run, safeguards, and fixed-200-image run. |
| `PHASE3_IMPLEMENTATION_WORKSPACE/12_VALIDATION/TASK_07_MODEL_EVALUATION_REPORT.md` | This validation report. |

## Verification results

| Command | Result |
| --- | --- |
| `.\.venv\Scripts\python.exe -m pytest tests\unit\test_evaluate_dataset.py -q` | PASS — 5 passed. |
| `.\.venv\Scripts\python.exe -m compileall scripts\evaluate_dataset.py tests\unit\test_evaluate_dataset.py` | PASS. |
| `.\.venv\Scripts\python.exe -m pyright scripts\evaluate_dataset.py tests\unit\test_evaluate_dataset.py` | PASS — 0 errors, 0 warnings. |
| `.\.venv\Scripts\python.exe -m ruff check scripts\evaluate_dataset.py tests\unit\test_evaluate_dataset.py` | PASS. |
| `.\.venv\Scripts\python.exe -m pytest -q` | PASS — 255 passed; one pre-existing third-party `StarletteDeprecationWarning`. |
| `.\.venv\Scripts\python.exe -m compileall src scripts tests` | PASS. |
| `.\.venv\Scripts\python.exe -m pyright src scripts tests` | PASS — 0 errors, 0 warnings. |
| `.\.venv\Scripts\python.exe -m ruff check src scripts tests` | PASS. |
| `git diff --check -- .gitignore README.md scripts/evaluate_dataset.py tests/unit/test_evaluate_dataset.py` | PASS. |

## Limitations and remaining evidence

- No real evaluation dataset or independently verified ground truth was supplied in this
  task. Consequently, the production model was **not** run against real evaluation images
  and no empirical accuracy, precision, recall, F1, latency, or confusion-matrix result is
  claimed here.
- `--ground-truth-confirmed` and `--training-overlap-reviewed` are operator attestations;
  the tool records them but cannot independently prove label quality or training-set
  disjointness.
- Per-image inference failures are isolated and reported so that one corrupt image does not
  abort the full run. Metrics use successfully inferred images only and the summary records
  skipped counts/reasons.

## Recommended next action

Prepare a separately governed, de-identified, ground-truth-verified, training-disjoint
dataset, run the documented command, and review `evaluation_summary.json` before making
any model-performance statement.
