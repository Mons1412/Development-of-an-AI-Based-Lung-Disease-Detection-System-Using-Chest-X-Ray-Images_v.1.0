import { byId } from "../core/dom.js";
import { parseFilename } from "./patient-api.js";
import { validatePatientDraft } from "./patient-validation.js";

function metadataErrorPayload(payload) {
  const detail = payload && typeof payload === "object" ? payload.detail : null;
  if (!detail || typeof detail !== "object") return null;
  if (!["invalid_case_metadata", "filename_metadata_mismatch"].includes(detail.code)) return null;
  return detail;
}

export function createPatientController(store) {
  const codeInput = byId("patient-code");
  const nameInput = byId("patient-name");
  const anonymousToggle = byId("anonymous-toggle");
  const confirmedInput = byId("patient-confirmed");
  const sourceLabel = byId("metadata-source-label");
  const parseStatus = byId("filename-parse-status");
  const codeError = byId("patient-code-error");
  const nameError = byId("patient-name-error");
  const confirmationError = byId("patient-confirmation-error");
  let parseController = null;
  let serverErrors = {};

  function readForm() {
    const anonymous = anonymousToggle.checked;
    store.updatePatient({
      code: anonymous ? "" : codeInput.value.normalize("NFC").trim(),
      name: anonymous ? "" : nameInput.value.normalize("NFC").trim().replace(/\s+/gu, " "),
      source: anonymous ? "anonymous" : store.getState().patient.source,
      anonymous,
      confirmed: confirmedInput.checked,
    });
    updateValidity();
  }

  function setSource(source) {
    store.updatePatient({ source });
    sourceLabel.textContent = source === "filename"
      ? "Tự nhận từ tên tệp"
      : source === "anonymous"
        ? "Ảnh ẩn danh / demo"
        : "Nhập thủ công";
  }

  function clearServerError(field) {
    if (!Object.hasOwn(serverErrors, field)) return;
    const { [field]: _removed, ...remaining } = serverErrors;
    serverErrors = remaining;
  }

  function setFieldState(input, errorElement, message) {
    errorElement.textContent = message;
    input.setAttribute("aria-invalid", String(Boolean(message)));
  }

  function updateValidity() {
    const state = store.getState();
    const patient = state.patient;
    const clientErrors = validatePatientDraft(patient);
    const codeMessage = serverErrors.patient_code || clientErrors.code;
    const nameMessage = serverErrors.patient_display_name || clientErrors.name;
    const confirmationMessage = serverErrors.patient_info_confirmed
      || serverErrors.is_anonymous_sample
      || serverErrors.patient_name_source
      || clientErrors.confirmation
      || clientErrors.source;

    setFieldState(codeInput, codeError, codeMessage);
    setFieldState(nameInput, nameError, nameMessage);
    confirmationError.textContent = confirmationMessage;
    confirmedInput.setAttribute("aria-invalid", String(Boolean(confirmationMessage)));

    codeInput.disabled = patient.anonymous;
    nameInput.disabled = patient.anonymous;

    const valid = Boolean(
      state.file
      && !codeMessage
      && !nameMessage
      && !confirmationMessage,
    );
    byId("submit-button").disabled = !valid || state.phase === "loading";
    return valid;
  }

  async function applyFile(file) {
    parseController?.abort();
    parseController = new AbortController();
    serverErrors = {};
    codeInput.value = "";
    nameInput.value = "";
    anonymousToggle.checked = false;
    confirmedInput.checked = false;
    setSource("manual");
    store.updatePatient({
      code: "",
      name: "",
      source: "manual",
      anonymous: false,
      confirmed: false,
      parsedDate: null,
    });
    parseStatus.textContent = "Đang kiểm tra quy tắc tên tệp…";
    try {
      const result = await parseFilename(file.name, parseController.signal);
      if (result.matched) {
        codeInput.value = result.patient_code || "";
        nameInput.value = result.patient_display_name || "";
        store.updatePatient({
          code: codeInput.value,
          name: nameInput.value,
          source: "filename",
          parsedDate: result.parsed_date,
        });
        setSource("filename");
        parseStatus.textContent = "Đã nhận diện theo quy tắc; cần xác nhận lại.";
      } else {
        parseStatus.textContent = "Tên tệp không theo quy tắc; vui lòng nhập thủ công.";
      }
    } catch (error) {
      if (error.name !== "AbortError") {
        parseStatus.textContent = "Không thể kiểm tra tên tệp; vui lòng nhập thủ công.";
      }
    }
    updateValidity();
  }

  function reset() {
    parseController?.abort();
    serverErrors = {};
    codeInput.value = "";
    nameInput.value = "";
    anonymousToggle.checked = false;
    confirmedInput.checked = false;
    parseStatus.textContent = "Chưa kiểm tra";
    store.updatePatient({
      code: "",
      name: "",
      source: "manual",
      anonymous: false,
      confirmed: false,
      parsedDate: null,
    });
    setSource("manual");
    codeError.textContent = "";
    nameError.textContent = "";
    confirmationError.textContent = "";
    codeInput.setAttribute("aria-invalid", "false");
    nameInput.setAttribute("aria-invalid", "false");
    confirmedInput.setAttribute("aria-invalid", "false");
  }

  function applyServerErrors(payload) {
    const detail = metadataErrorPayload(payload);
    if (!detail) return false;
    serverErrors = detail.field_errors && typeof detail.field_errors === "object"
      ? { ...detail.field_errors }
      : { patient_info_confirmed: detail.message || "Thông tin ca phân tích chưa hợp lệ." };
    confirmedInput.checked = false;
    store.updatePatient({ confirmed: false });
    updateValidity();

    if (serverErrors.patient_code) codeInput.focus();
    else if (serverErrors.patient_display_name) nameInput.focus();
    else confirmedInput.focus();
    return true;
  }

  codeInput.addEventListener("input", () => {
    clearServerError("patient_code");
    clearServerError("patient_name_source");
    if (!anonymousToggle.checked) setSource("manual");
    confirmedInput.checked = false;
    readForm();
  });
  nameInput.addEventListener("input", () => {
    clearServerError("patient_display_name");
    clearServerError("patient_name_source");
    if (!anonymousToggle.checked) setSource("manual");
    confirmedInput.checked = false;
    readForm();
  });
  anonymousToggle.addEventListener("change", () => {
    serverErrors = {};
    if (anonymousToggle.checked) {
      codeInput.value = "";
      nameInput.value = "";
      setSource("anonymous");
    } else {
      setSource("manual");
    }
    confirmedInput.checked = false;
    readForm();
  });
  confirmedInput.addEventListener("change", () => {
    clearServerError("patient_info_confirmed");
    clearServerError("is_anonymous_sample");
    readForm();
  });
  store.subscribe(updateValidity);

  return {
    applyFile,
    reset,
    isValid: updateValidity,
    applyServerErrors,
    appendToFormData(formData) {
      const patient = store.getState().patient;
      if (patient.code) formData.set("patient_code", patient.code);
      if (patient.name) formData.set("patient_display_name", patient.name);
      formData.set("patient_name_source", patient.source);
      formData.set("patient_info_confirmed", String(patient.confirmed));
      formData.set("is_anonymous_sample", String(patient.anonymous));
    },
  };
}
