# TASK 02 — Local/Offline Assistant Backend Report

**Date:** 2026-07-26  
**Scope:** Local retrieval assistant backend only. The demo UI, MobileNetV2 model/prediction flow, PDF, branding, database, Gemini, Google AI Studio, OpenAI, and all external network services were not implemented or integrated.

## Architecture implemented

```text
POST /api/v1/assistant/query
  -> Pydantic request validation
  -> SafetyGuard (before retrieval)
  -> StateValidator
  -> IntentRouter
  -> local TF-IDF/cosine retrieval over production KB
  -> deterministic ResponseRenderer
```

- `AssistantService` is created once in the FastAPI lifespan and stored as `app.state.assistant_service`.
- `KnowledgeBase.load()` accepts only a file named `knowledge_base.production.vi.json`, requires `mode=production`, validates item count/unique IDs/intents, and rejects every item that is pending or requires clinical review.
- The runtime uses only local standard-library modules plus existing project dependencies. It has no HTTP client, LLM, cloud API, API key, database, or network fallback.
- If the KB is missing or invalid, startup logs a clear warning, leaves the assistant unavailable (HTTP 503), and keeps all prediction endpoints working.

## Files changed

### New runtime and API files

- `knowledge_base/compiled/knowledge_base.production.vi.json` — copied verbatim from the approved workspace production index only; SHA-256 `D80AAE35D480C58A2A2C140E5274FEA29E5A6C9A8030E21ED73333CEC2986D1B`.
- `src/lung_xray_api/assistant/{__init__,knowledge_base,safety_guard,state_validator,intent_router,retriever,response_renderer,service}.py`
- `src/lung_xray_api/api/v1/assistant.py`
- `src/lung_xray_api/schemas/assistant.py`

### Existing integration files changed by controlled diff

- `.env.example` — adds `KNOWLEDGE_BASE_PATH` with the production-only default.
- `src/lung_xray_api/core/config.py` — resolves a relative KB path from the project root.
- `src/lung_xray_api/core/lifespan.py` — builds the assistant once and isolates KB failure from prediction availability.
- `src/lung_xray_api/api/dependencies.py` — adds the assistant service dependency.
- `src/lung_xray_api/api/v1/router.py` — registers only the new assistant router; existing route prefixes remain unchanged.

### New focused tests

- `tests/unit/test_assistant_knowledge_base.py`
- `tests/unit/test_assistant_service.py`
- `tests/integration/test_assistant_api.py`

## Endpoint contract

`POST /api/v1/assistant/query` follows the existing optional API-key policy. The request accepts:

```json
{
  "message": "Giải thích kết quả và xác suất",
  "application_stage": "after_analysis",
  "prediction_context": {
    "predicted_label": "pneumonia",
    "probabilities": {
      "normal": 0.08,
      "pneumonia": 0.87,
      "tuberculosis": 0.05
    },
    "model_version": "1.1.0",
    "processing_time_ms": 720
  }
}
```

- `application_stage` supports `before_analysis`, `analysis_running`, `after_analysis`, and `analysis_failed`.
- `prediction_context` is optional in the schema. At `after_analysis`, its absence returns the controlled `needs_prediction` response; malformed context is rejected with HTTP 422.
- Context probabilities must contain exactly the three locked classes, each in `[0, 1]`, with total within `1e-4` of 1.
- The response always has `status`, `mode: "offline"`, `intent`, `answer`, `sources`, `disclaimer`, `suggested_questions`, and `confidence`.
- High-confidence intent/retrieval answers use source IDs from the exact approved KB item. Medium scores return `needs_clarification` with local suggestions; low scores return controlled `out_of_scope`.
- Definitive diagnosis, medication, dosage, treatment-change, unavailable patient-data, and unsupported-disease requests are handled before retrieval with controlled refusals/out-of-scope responses.

## Knowledge Base path and gate

Default runtime path:

```text
knowledge_base/compiled/knowledge_base.production.vi.json
```

`KNOWLEDGE_BASE_PATH` may override it with another production file path. Relative paths resolve from the project root, which supports source execution, tests, and a future portable package that retains this project-relative layout. There is no fallback to `knowledge_base.development.vi.json`.

The loaded production index has 21 items and no pending IDs. The 34 clinical/release-gate pending items were not copied to the runtime path, not loaded into `KnowledgeBase.items`, and are not available for retrieval. Consequently, disease-specific clinical questions without approved production content receive a controlled response rather than a synthesized answer.

## Test results

| Command | Result |
| --- | --- |
| `python -m pytest tests/unit/test_assistant_knowledge_base.py tests/unit/test_assistant_service.py tests/integration/test_assistant_api.py -q` | PASS — 19 passed. |
| `python -m compileall src scripts tests` | PASS — exit code 0. |
| `python -m pytest -q` | PASS — 53 passed. |
| `python -m pyright src scripts tests` | PASS — 0 errors, 0 warnings. |
| `python -m ruff check src scripts tests` | PASS — all checks passed. |

The test suite emits the pre-existing `StarletteDeprecationWarning` for TestClient/httpx; it does not fail tests.

Focused coverage proves production-only KB loading, pending-item rejection, before/after stage behavior, missing context, all required safety categories, unsupported disease behavior, source mapping, malformed payload HTTP 422, and the invariant that a missing KB does not break `POST /api/v1/predict`.

## Limitations

- The assistant has no server-side persistence or trusted session binding for `prediction_context`; it validates the supplied metadata and phrases it as supplied context. TASK 04 must clear stale context in every UI transition.
- Production has no clinically reviewed disease-information items. The assistant deliberately does not answer disease-specific clinical questions until the Knowledge Base review gate permits them.
- Browser UI, assistant context wiring, PDF export, branding, model evaluation, and any online rephrasing mode remain out of scope and unimplemented.
- The portable ZIP has not been rebuilt in this task. A later release task must include the new production KB JSON and exercise the local endpoint on a clean Windows package.

## Remaining work

1. TASK 04: integrate the assistant panel and ensure prediction context is created only after a successful prediction and cleared on select/reset/error.
2. Preserve the clinical review gate before promoting any disease-information or high-risk safety item into production.
3. Perform clean-Windows portable smoke testing and packaging only in the release task.
