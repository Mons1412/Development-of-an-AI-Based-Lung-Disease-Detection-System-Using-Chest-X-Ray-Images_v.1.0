import assert from "node:assert/strict";
import test from "node:test";

import {
  buildAssistantContext,
} from "../../src/lung_xray_api/web/static/js/assistant/assistant-controller.js";

test("assistant context contains only the approved current prediction fields", () => {
  const context = buildAssistantContext({
    phase: "success",
    currentPrediction: {
      predicted_label: "tuberculosis",
      probabilities: {
        normal: 0.2722,
        pneumonia: 0.0669,
        tuberculosis: 0.6609,
      },
      model_version: "1.1.0",
      patient_code: "MUST_NOT_LEAK",
      filename: "MUST_NOT_LEAK.png",
    },
  });

  assert.deepEqual(context, {
    application_stage: "after_analysis",
    prediction_context: {
      predicted_label: "tuberculosis",
      probabilities: {
        normal: 0.2722,
        pneumonia: 0.0669,
        tuberculosis: 0.6609,
      },
      model_version: "1.1.0",
    },
  });
  assert.equal(JSON.stringify(context).includes("MUST_NOT_LEAK"), false);
});

test("assistant context is cleared outside a successful analysis", () => {
  const stalePrediction = {
    predicted_label: "pneumonia",
    probabilities: { normal: 0.1, pneumonia: 0.8, tuberculosis: 0.1 },
    model_version: "1.1.0",
  };

  assert.deepEqual(
    buildAssistantContext({ phase: "selected", currentPrediction: stalePrediction }),
    { application_stage: "before_analysis" },
  );
  assert.deepEqual(
    buildAssistantContext({ phase: "loading", currentPrediction: stalePrediction }),
    { application_stage: "analysis_running" },
  );
});
