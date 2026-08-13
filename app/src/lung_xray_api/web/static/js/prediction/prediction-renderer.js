import { CLASS_COLORS, CLASS_LABELS, CLASS_ORDER } from "../core/constants.js";
import {
  DEFAULT_RESULT_VIEWS,
  normalizeResultViews,
  RESULT_VIEW_LABELS,
  RESULT_VIEW_SECTION_IDS,
  RESULT_VIEW_IDS,
} from "../core/result-views.js";
import { byId, clearElement, text } from "../core/dom.js";
import { formatPercent } from "../ui/formatters.js";
import { renderResultChart, renderResultDonut } from "../visualization/result-chart.js";

const RESULT_STATE_IDS = ["result-empty", "result-loading", "result-error", "result-success"];

function showOnly(id) {
  RESULT_STATE_IDS.forEach((candidate) => {
    byId(candidate).hidden = candidate !== id;
  });
}

function probabilityFor(probabilities, label) {
  const value = Number(probabilities?.[label]);
  return Number.isFinite(value) ? Math.min(1, Math.max(0, value)) : 0;
}

function clearPreviousResultVisualizations() {
  CLASS_ORDER.forEach((label) => {
    byId(`bar-${label}`).style.transform = "scaleX(0)";
    byId(`value-${label}`).textContent = "0.00%";
  });
  clearElement(byId("result-chart"));
  clearElement(byId("result-donut"));
  clearElement(byId("result-table-body"));
  clearElement(byId("result-view-badges"));
  byId("result-visualization-summary").textContent = "";
}

function setResultViewVisibility(selectedViews) {
  const selected = new Set(normalizeResultViews(selectedViews));
  Object.entries(RESULT_VIEW_SECTION_IDS).forEach(([view, sectionId]) => {
    byId(sectionId).hidden = !selected.has(view);
  });
}

function renderProbabilityBars(probabilities) {
  CLASS_ORDER.forEach((label) => {
    const value = probabilityFor(probabilities, label);
    byId(`bar-${label}`).style.transform = `scaleX(${value})`;
    byId(`value-${label}`).textContent = formatPercent(value);
  });
}

function renderDataTable(probabilities) {
  const body = byId("result-table-body");
  clearElement(body);
  CLASS_ORDER.forEach((label) => {
    const classCell = document.createElement("td");
    const marker = document.createElement("span");
    marker.className = "class-indicator";
    marker.style.backgroundColor = CLASS_COLORS[label];
    marker.setAttribute("aria-hidden", "true");
    classCell.append(marker, document.createTextNode(CLASS_LABELS[label]));
    const row = document.createElement("tr");
    row.dataset.class = label;
    row.append(
      classCell,
      text("td", label),
      text("td", formatPercent(probabilityFor(probabilities, label))),
    );
    body.append(row);
  });
}

function renderSelectionBadges(selectedViews) {
  const container = byId("result-view-badges");
  clearElement(container);
  selectedViews.forEach((view) => {
    const badge = document.createElement("span");
    badge.className = "result-view-badge";
    badge.textContent = RESULT_VIEW_LABELS[view];
    container.append(badge);
  });
}

function renderSelectionSummary(selectedViews) {
  const labels = selectedViews.map((view) => RESULT_VIEW_LABELS[view]).join(", ");
  byId("result-visualization-summary").textContent = `Đã hiển thị ${selectedViews.length} dạng kết quả: ${labels}.`;
}

/** Owns all result-only DOM mutations. */
export function createPredictionRenderer() {
  function renderIdle() {
    clearPreviousResultVisualizations();
    showOnly("result-empty");
    byId("reference-info-button").hidden = true;
    byId("preview-report-button").hidden = true;
    byId("export-report-button").hidden = true;
  }

  function renderLoading() {
    clearPreviousResultVisualizations();
    showOnly("result-loading");
    byId("reference-info-button").hidden = true;
    byId("preview-report-button").hidden = true;
    byId("export-report-button").hidden = true;
  }

  function renderError(message) {
    clearPreviousResultVisualizations();
    showOnly("result-error");
    byId("result-error-message").textContent = message;
    byId("reference-info-button").hidden = true;
    byId("preview-report-button").hidden = true;
    byId("export-report-button").hidden = true;
  }

  function renderPredictionResult({ prediction, selectedViews = DEFAULT_RESULT_VIEWS }) {
    const normalizedViews = normalizeResultViews(selectedViews);
    clearPreviousResultVisualizations();
    showOnly("result-success");
    setResultViewVisibility(normalizedViews);

    byId("prediction-label").textContent = CLASS_LABELS[prediction.prediction] || prediction.prediction;
    byId("api-label").textContent = prediction.prediction;
    byId("prediction-confidence").textContent = formatPercent(prediction.model_probability);
    byId("model-version").textContent = prediction.model_version;
    byId("processing-time").textContent = `${prediction.processing_time_ms} ms`;
    byId("analysis-id").textContent = prediction.analysis_id;

    if (normalizedViews.includes(RESULT_VIEW_IDS.PROBABILITY_BARS)) {
      renderProbabilityBars(prediction.probabilities);
    }
    if (normalizedViews.includes(RESULT_VIEW_IDS.COLUMN_CHART)) {
      renderResultChart(byId("result-chart"), prediction.probabilities);
    }
    if (normalizedViews.includes(RESULT_VIEW_IDS.DONUT_CHART)) {
      renderResultDonut(byId("result-donut"), prediction.probabilities, prediction.prediction);
    }
    if (normalizedViews.includes(RESULT_VIEW_IDS.DATA_TABLE)) {
      renderDataTable(prediction.probabilities);
    }

    renderSelectionBadges(normalizedViews);
    renderSelectionSummary(normalizedViews);
    byId("reference-info-button").hidden = false;
    byId("preview-report-button").hidden = false;
    byId("export-report-button").hidden = false;
  }

  return { renderIdle, renderLoading, renderError, renderPredictionResult };
}
