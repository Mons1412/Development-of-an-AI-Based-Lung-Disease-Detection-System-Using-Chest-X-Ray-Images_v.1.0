import { ACCEPTED_TYPES, MAX_UPLOAD_BYTES } from "../core/constants.js";
import { byId } from "../core/dom.js";
import { emit, EVENTS } from "../core/events.js";
import { formatBytes } from "../ui/formatters.js";
import { showToast } from "../ui/toast.js";
import { readImageDimensions } from "./file-preview.js";
import { createPersistedAnalysis, getHealth, getModelInfo } from "./prediction-api.js";

export function createPredictionController(store, patientController, renderer) {
  const form = byId("prediction-form");
  const fileInput = byId("file-input");
  const dropzone = byId("dropzone");
  const previewCard = byId("preview-card");
  const preview = byId("image-preview");
  const fileError = byId("file-error");
  let requestController = null;

  async function selectFile(file) {
    clearPrediction();
    if (!file) return;
    const validationMessage = validateFile(file);
    if (validationMessage) {
      fileError.textContent = validationMessage;
      fileError.hidden = false;
      return;
    }
    fileError.hidden = true;
    const previousUrl = store.getState().previewUrl;
    if (previousUrl) URL.revokeObjectURL(previousUrl);
    const previewUrl = URL.createObjectURL(file);
    store.setState({
      file,
      previewUrl,
      phase: "selected",
      analysisResult: null,
      currentPrediction: null,
      analysisId: null,
    });
    preview.src = previewUrl;
    previewCard.hidden = false;
    byId("file-name").textContent = file.name;
    byId("reset-button").disabled = false;
    try {
      const dimensions = await readImageDimensions(previewUrl);
      byId("file-meta").textContent = `${formatBytes(file.size)} · ${dimensions.width} × ${dimensions.height}px`;
    } catch {
      byId("file-meta").textContent = `${formatBytes(file.size)} · không đọc được kích thước`;
    }
    await patientController.applyFile(file);
    emit(EVENTS.ANALYSIS_RESET);
  }

  function validateFile(file) {
    if (!ACCEPTED_TYPES.has(file.type)) return "Chỉ chấp nhận ảnh JPG, JPEG hoặc PNG.";
    if (file.size > MAX_UPLOAD_BYTES) return "Tệp vượt quá giới hạn 10 MB.";
    if (file.size === 0) return "Tệp ảnh rỗng.";
    return "";
  }

  /** Clears stale result data without changing a user's visualization preference. */
  function clearPrediction() {
    requestController?.abort();
    store.setState({
      phase: store.getState().file ? "selected" : "idle",
      analysisResult: null,
      currentPrediction: null,
      analysisId: null,
    });
    renderer.renderIdle();
    emit(EVENTS.ANALYSIS_RESET);
  }

  function resetAll() {
    requestController?.abort();
    store.reset();
    fileInput.value = "";
    preview.removeAttribute("src");
    previewCard.hidden = true;
    byId("reset-button").disabled = true;
    patientController.reset();
    fileError.hidden = true;
    renderer.renderIdle();
    emit(EVENTS.ANALYSIS_RESET);
  }

  async function submit(event) {
    event.preventDefault();
    const { file } = store.getState();
    if (!file || !patientController.isValid()) return;
    requestController?.abort();
    requestController = new AbortController();
    store.setState({
      phase: "loading",
      analysisResult: null,
      currentPrediction: null,
      analysisId: null,
    });
    renderer.renderLoading();
    patientController.isValid();
    const formData = new FormData();
    formData.set("file", file, file.name);
    patientController.appendToFormData(formData);
    try {
      const result = await createPersistedAnalysis(formData, requestController.signal);
      if (store.getState().file !== file) return;
      // The preference controller observes this state transition and renders once.
      store.setState({
        phase: "success",
        analysisResult: result,
        currentPrediction: {
          predicted_label: result.prediction,
          probabilities: { ...result.probabilities },
          model_version: result.model_version,
        },
        analysisId: result.analysis_id,
      });
      patientController.isValid();
      emit(EVENTS.ANALYSIS_COMPLETED, { result });
      emit(EVENTS.HISTORY_CHANGED);
      showToast("Đã phân tích và lưu lịch sử cục bộ.");
    } catch (error) {
      if (error.name === "AbortError") return;
      const metadataHandled = error.status === 422
        && patientController.applyServerErrors(error.payload);
      if (metadataHandled) {
        store.setState({
          phase: "selected",
          analysisResult: null,
          currentPrediction: null,
          analysisId: null,
        });
        renderer.renderIdle();
        showToast("Thông tin ca phân tích chưa hợp lệ. Vui lòng kiểm tra trường được đánh dấu.", 4200);
        emit(EVENTS.ANALYSIS_RESET);
        return;
      }
      store.setState({
        phase: "error",
        analysisResult: null,
        currentPrediction: null,
        analysisId: null,
      });
      renderer.renderError(error.message || "Không thể hoàn tất phân tích.");
      emit(EVENTS.ANALYSIS_RESET);
    }
  }

  async function checkRuntime() {
    const statusElement = byId("api-status");
    try {
      await getHealth();
      const info = await getModelInfo();
      statusElement.className = "status-pill status-pill--ready";
      byId("api-status-title").textContent = "API sẵn sàng";
      byId("header-model-version").textContent = info.model_version || "—";
    } catch {
      statusElement.className = "status-pill status-pill--error";
      byId("api-status-title").textContent = "API chưa sẵn sàng";
    }
  }

  dropzone.addEventListener("click", () => fileInput.click());
  dropzone.addEventListener("dragover", (event) => { event.preventDefault(); dropzone.classList.add("is-dragging"); });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("is-dragging"));
  dropzone.addEventListener("drop", (event) => {
    event.preventDefault();
    dropzone.classList.remove("is-dragging");
    selectFile(event.dataTransfer.files[0]);
  });
  fileInput.addEventListener("change", () => selectFile(fileInput.files[0]));
  byId("remove-file-button").addEventListener("click", resetAll);
  byId("reset-button").addEventListener("click", resetAll);
  form.addEventListener("submit", submit);

  return { checkRuntime, resetAll, selectFile };
}
