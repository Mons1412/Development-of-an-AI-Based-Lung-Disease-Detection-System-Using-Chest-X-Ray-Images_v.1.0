import assert from "node:assert/strict";
import test from "node:test";

import { DEFAULT_RESULT_VIEWS } from "../../src/lung_xray_api/web/static/js/core/result-views.js";
import { createResultViewPreferencesController } from "../../src/lung_xray_api/web/static/js/prediction/result-view-preferences-controller.js";
import { installFakeDocument } from "./helpers/fake-dom.mjs";

function createStore() {
  let state = {
    phase: "idle",
    analysisResult: null,
    currentPrediction: null,
    selectedResultViews: [...DEFAULT_RESULT_VIEWS],
  };
  const listeners = new Set();
  const notify = () => listeners.forEach((listener) => listener(state));
  return {
    getState: () => state,
    subscribe(listener) { listeners.add(listener); return () => listeners.delete(listener); },
    setSelectedResultViews(selectedResultViews) {
      state = { ...state, selectedResultViews };
      notify();
    },
    setState(patch) { state = { ...state, ...patch }; notify(); },
    reset() {
      state = {
        phase: "idle",
        analysisResult: null,
        currentPrediction: null,
        selectedResultViews: [...DEFAULT_RESULT_VIEWS],
      };
      notify();
    },
  };
}

function setupPreferenceDom() {
  const document = installFakeDocument();
  document.register(document.createElement("p"), "result-view-preferences-status");
  document.register(document.createElement("span"), "selected-view-count");
  ["probability-bars", "column-chart", "donut-chart", "data-table"].forEach((value) => {
    const card = document.createElement("label");
    card.setAttribute("data-result-view-card", value);
    const input = document.createElement("input");
    input.setAttribute("name", "result-view-preference");
    input.value = value;
    input.checked = DEFAULT_RESULT_VIEWS.includes(value);
    card.append(input);
    document.body.append(card);
  });
  return document;
}

test("last selected preference cannot be unchecked and selection changes do not start inference", () => {
  const document = setupPreferenceDom();
  const store = createStore();
  const rendererCalls = [];
  createResultViewPreferencesController(store, {
    renderPredictionResult(payload) { rendererCalls.push(payload); },
  });
  const inputs = document.querySelectorAll('[name="result-view-preference"]');

  inputs[0].checked = false;
  inputs[0].dispatch("change");
  assert.deepEqual(store.getState().selectedResultViews, ["column-chart"]);
  assert.equal(rendererCalls.length, 0);

  inputs[1].checked = false;
  inputs[1].dispatch("change");
  assert.equal(inputs[1].checked, true);
  assert.equal(
    document.getElementById("result-view-preferences-status").textContent,
    "Cần chọn ít nhất một dạng hiển thị kết quả.",
  );
  assert.deepEqual(store.getState().selectedResultViews, ["column-chart"]);
  assert.equal(rendererCalls.length, 0);
});

test("new image state preserves preference, reset restores default, and post-result toggle re-renders", () => {
  const document = setupPreferenceDom();
  const store = createStore();
  const rendererCalls = [];
  createResultViewPreferencesController(store, {
    renderPredictionResult(payload) { rendererCalls.push(payload); },
  });
  const inputs = document.querySelectorAll('[name="result-view-preference"]');

  inputs[2].checked = true;
  inputs[2].dispatch("change");
  assert.deepEqual(store.getState().selectedResultViews, ["probability-bars", "column-chart", "donut-chart"]);

  store.setState({ phase: "selected", analysisResult: null, currentPrediction: null });
  assert.deepEqual(store.getState().selectedResultViews, ["probability-bars", "column-chart", "donut-chart"]);

  const currentPrediction = { prediction: "normal", probabilities: { normal: 1, pneumonia: 0, tuberculosis: 0 } };
  store.setState({
    phase: "success",
    analysisResult: currentPrediction,
    currentPrediction: {
      predicted_label: "normal",
      probabilities: currentPrediction.probabilities,
      model_version: "1.1.0",
    },
  });
  assert.equal(rendererCalls.length, 1);

  inputs[3].checked = true;
  inputs[3].dispatch("change");
  assert.equal(rendererCalls.length, 2);
  assert.equal(rendererCalls[1].prediction, currentPrediction);

  store.reset();
  assert.deepEqual(store.getState().selectedResultViews, DEFAULT_RESULT_VIEWS);
  assert.equal(inputs[0].checked, true);
  assert.equal(inputs[1].checked, true);
  assert.equal(inputs[2].checked, false);
  assert.equal(inputs[3].checked, false);
});
