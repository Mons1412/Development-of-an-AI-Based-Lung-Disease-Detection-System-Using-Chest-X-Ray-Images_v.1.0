import { DEFAULT_RESULT_VIEWS, normalizeResultViews } from "./result-views.js";

const initialState = () => ({
  file: null,
  previewUrl: null,
  phase: "idle",
  selectedResultViews: [...DEFAULT_RESULT_VIEWS],
  patient: {
    code: "",
    name: "",
    source: "manual",
    anonymous: false,
    confirmed: false,
    parsedDate: null,
  },
  analysisResult: null,
  currentPrediction: null,
  analysisId: null,
});

export function createAppStore() {
  let state = initialState();
  const listeners = new Set();

  function notify() {
    listeners.forEach((listener) => listener(state));
  }

  return {
    getState: () => state,
    setState(patch) {
      state = { ...state, ...patch };
      notify();
    },
    setSelectedResultViews(selectedResultViews) {
      state = {
        ...state,
        selectedResultViews: normalizeResultViews(selectedResultViews),
      };
      notify();
    },
    updatePatient(patch) {
      state = { ...state, patient: { ...state.patient, ...patch } };
      notify();
    },
    reset() {
      if (state.previewUrl) URL.revokeObjectURL(state.previewUrl);
      state = initialState();
      notify();
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}
