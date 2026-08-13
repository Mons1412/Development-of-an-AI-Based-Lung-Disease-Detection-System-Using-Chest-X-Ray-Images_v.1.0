import assert from "node:assert/strict";
import test from "node:test";

import { RESULT_VIEW_ORDER } from "../../src/lung_xray_api/web/static/js/core/result-views.js";
import { createPredictionRenderer } from "../../src/lung_xray_api/web/static/js/prediction/prediction-renderer.js";
import { findAll, installFakeDocument } from "./helpers/fake-dom.mjs";

function buildResultDom() {
  const document = installFakeDocument();
  ["result-empty", "result-loading", "result-error", "result-success"].forEach((id) => {
    document.register(document.createElement("section"), id);
  });
  [
    "prediction-label",
    "api-label",
    "prediction-confidence",
    "model-version",
    "processing-time",
    "analysis-id",
    "result-error-message",
    "result-visualization-summary",
    "result-view-badges",
    "result-chart",
    "result-donut",
    "result-table-body",
    "reference-info-button",
    "preview-report-button",
    "export-report-button",
  ].forEach((id) => document.register(document.createElement("div"), id));
  ["normal", "pneumonia", "tuberculosis"].forEach((label) => {
    document.register(document.createElement("span"), `bar-${label}`);
    document.register(document.createElement("strong"), `value-${label}`);
  });
  RESULT_VIEW_ORDER.forEach((view) => {
    const section = document.createElement("section");
    document.register(section, `result-view-${view}`);
  });
  return document;
}

const prediction = {
  prediction: "pneumonia",
  model_probability: 0.72,
  probabilities: { normal: 0.18, pneumonia: 0.72, tuberculosis: 0.1 },
  model_version: "1.1.0",
  processing_time_ms: 321,
  analysis_id: "analysis-1",
};

test("selected views render together without duplicate charts or table rows", () => {
  const document = buildResultDom();
  const renderer = createPredictionRenderer();

  renderer.renderPredictionResult({ prediction, selectedViews: RESULT_VIEW_ORDER });

  assert.equal(document.getElementById("result-success").hidden, false);
  RESULT_VIEW_ORDER.forEach((view) => {
    assert.equal(document.getElementById(`result-view-${view}`).hidden, false, view);
  });
  const columnContainer = document.getElementById("result-chart");
  const columnSvg = findAll(columnContainer, "svg")[0];
  const columnSegments = findAll(columnSvg, "[data-column-segment]");

  assert.equal(findAll(columnContainer, "svg").length, 1);
  assert.equal(columnContainer.classList.contains("chart-container--column"), true);
  assert.equal(columnSvg.getAttribute("viewBox"), "0 0 420 390");
  assert.deepEqual(columnSegments.map((segment) => segment.getAttribute("data-class")), [
    "normal",
    "pneumonia",
    "tuberculosis",
  ]);
  assert.deepEqual(columnSegments.map((segment) => segment.getAttribute("data-probability")), [
    "0.18000000",
    "0.72000000",
    "0.10000000",
  ]);
  assert.equal(findAll(document.getElementById("result-donut"), "svg").length, 1);
  assert.equal(document.getElementById("result-table-body").children.length, 3);
  assert.equal(document.getElementById("bar-pneumonia").style.transform, "scaleX(0.72)");

  renderer.renderPredictionResult({ prediction, selectedViews: RESULT_VIEW_ORDER });

  assert.equal(findAll(document.getElementById("result-chart"), "svg").length, 1);
  assert.equal(findAll(document.getElementById("result-donut"), "svg").length, 1);
  assert.equal(document.getElementById("result-table-body").children.length, 3);
});

test("donut renders exactly normal, pneumonia, tuberculosis segments for zero and 100 percent values", () => {
  const document = buildResultDom();
  const renderer = createPredictionRenderer();

  renderer.renderPredictionResult({
    prediction: { ...prediction, prediction: "normal", model_probability: 1, probabilities: { normal: 1, pneumonia: 0, tuberculosis: 0 } },
    selectedViews: ["donut-chart"],
  });

  const donut = document.getElementById("result-donut");
  const svg = findAll(donut, "svg")[0];
  const segments = svg.children.filter((child) => child.getAttribute?.("data-class"));
  assert.deepEqual(segments.map((segment) => segment.getAttribute("data-class")), [
    "normal",
    "pneumonia",
    "tuberculosis",
  ]);
  assert.equal(segments.length, 3);
  assert.equal(segments[0].getAttribute("data-probability"), "1.00000000");
  assert.equal(segments[1].getAttribute("data-probability"), "0.00000000");
  assert.equal(findAll(donut, "svg").length, 1);
  assert.equal(donut.children[0].children[1].children.length, 3);

  renderer.renderPredictionResult({
    prediction: {
      ...prediction,
      probabilities: { normal: 0.0001, pneumonia: 0.4999, tuberculosis: 0.5 },
    },
    selectedViews: ["donut-chart"],
  });
  const nearZeroSegments = findAll(document.getElementById("result-donut"), "svg")[0]
    .children.filter((child) => child.getAttribute?.("data-class"));
  assert.equal(nearZeroSegments.length, 3);
  assert.equal(nearZeroSegments[0].getAttribute("data-probability"), "0.00010000");
});

test("idle state clears charts, rows, and result actions after a prediction", () => {
  const document = buildResultDom();
  const renderer = createPredictionRenderer();
  renderer.renderPredictionResult({ prediction, selectedViews: RESULT_VIEW_ORDER });

  renderer.renderIdle();

  assert.equal(document.getElementById("result-empty").hidden, false);
  assert.equal(document.getElementById("result-chart").children.length, 0);
  assert.equal(document.getElementById("result-donut").children.length, 0);
  assert.equal(document.getElementById("result-table-body").children.length, 0);
  assert.equal(document.getElementById("reference-info-button").hidden, true);
  assert.equal(document.getElementById("preview-report-button").hidden, true);
  assert.equal(document.getElementById("export-report-button").hidden, true);
});
