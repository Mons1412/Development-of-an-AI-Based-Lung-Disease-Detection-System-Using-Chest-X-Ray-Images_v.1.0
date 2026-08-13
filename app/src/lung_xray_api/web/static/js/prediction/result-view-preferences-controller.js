import { DEFAULT_RESULT_VIEWS, normalizeResultViews } from "../core/result-views.js";
import { byId } from "../core/dom.js";

const LAST_SELECTION_MESSAGE = "Cần chọn ít nhất một dạng hiển thị kết quả.";

function selectedValues(inputs) {
  return inputs.filter((input) => input.checked).map((input) => input.value);
}

/**
 * Owns multi-select preference interaction and asks the result renderer to
 * refresh the current prediction when preferences change. It never starts a
 * new inference request.
 */
export function createResultViewPreferencesController(store, renderer) {
  const inputs = Array.from(document.querySelectorAll('[name="result-view-preference"]'));
  const status = byId("result-view-preferences-status");
  const counter = byId("selected-view-count");
  let previousSelection = normalizeResultViews(store.getState().selectedResultViews);
  let lastRenderKey = "";

  function syncInputs(selectedViews) {
    const selected = normalizeResultViews(selectedViews);
    inputs.forEach((input) => {
      const checked = selected.includes(input.value);
      input.checked = checked;
      input.closest("[data-result-view-card]")?.classList.toggle("is-selected", checked);
    });
    counter.textContent = String(selected.length);
  }

  function renderCurrentPrediction(state, selected) {
    if (state.phase !== "success" || !state.analysisResult) {
      lastRenderKey = "";
      return;
    }
    const renderKey = `${state.analysisResult.analysis_id || "current"}:${selected.join(",")}`;
    if (renderKey === lastRenderKey) return;
    renderer.renderPredictionResult({
      prediction: state.analysisResult,
      selectedViews: selected,
    });
    lastRenderKey = renderKey;
  }

  function applyStoreState(state) {
    const selected = normalizeResultViews(state.selectedResultViews);
    syncInputs(selected);
    previousSelection = selected;
    if (state.phase !== "success") status.textContent = "";
    renderCurrentPrediction(state, selected);
  }

  inputs.forEach((input) => {
    input.addEventListener("change", () => {
      const requested = selectedValues(inputs);
      if (requested.length === 0) {
        syncInputs(previousSelection);
        status.textContent = LAST_SELECTION_MESSAGE;
        return;
      }
      status.textContent = "";
      store.setSelectedResultViews(requested);
    });
  });

  store.subscribe(applyStoreState);
  syncInputs(previousSelection.length ? previousSelection : DEFAULT_RESULT_VIEWS);

  return {
    resetStatus() {
      status.textContent = "";
    },
  };
}
