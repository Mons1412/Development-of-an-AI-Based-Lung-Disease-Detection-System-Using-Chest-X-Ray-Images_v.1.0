import { createAppStore } from "./core/app-store.js";
import { byId } from "./core/dom.js";
import { createAssistantController } from "./assistant/assistant-controller.js";
import { createHistoryController } from "./history/history-controller.js";
import { createPatientController } from "./patient/patient-controller.js";
import { createPredictionController } from "./prediction/prediction-controller.js";
import { createPredictionRenderer } from "./prediction/prediction-renderer.js";
import { createResultViewPreferencesController } from "./prediction/result-view-preferences-controller.js";
import { createReportController } from "./report/report-controller.js";
import { initializeModalControls, openModal } from "./ui/modal.js";

export const FRONTEND_BUILD = "20260728.6";

export function initializeApplication() {
  const renderedBuild = document.querySelector('meta[name="frontend-build"]')?.content;
  if (renderedBuild && renderedBuild !== FRONTEND_BUILD) {
    console.warn(`[LungXrayUI] rendered build ${renderedBuild} does not match module ${FRONTEND_BUILD}`);
  }
  console.info(`[LungXrayUI] frontend build ${FRONTEND_BUILD}`);

  const store = createAppStore();
  initializeModalControls();
  const patient = createPatientController(store);
  const renderer = createPredictionRenderer();
  const prediction = createPredictionController(store, patient, renderer);
  createResultViewPreferencesController(store, renderer);
  createHistoryController();
  createAssistantController(store);
  createReportController(store);

  byId("about-project-button").addEventListener("click", () => {
    openModal(byId("about-project-modal"), byId("about-project-button"));
  });
  byId("reference-info-button").addEventListener("click", () => {
    const predictionState = store.getState().analysisResult;
    if (predictionState) {
      byId("reference-info-summary").textContent =
        `Mô hình phân loại ảnh vào lớp ${predictionState.prediction} với xác suất đầu ra ${(predictionState.model_probability * 100).toFixed(2)}%.`;
    }
    openModal(byId("reference-info-modal"), byId("reference-info-button"));
  });

  prediction.checkRuntime();
  return store;
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeApplication, { once: true });
} else {
  initializeApplication();
}
