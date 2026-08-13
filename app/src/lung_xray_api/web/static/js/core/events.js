export const EVENTS = {
  ANALYSIS_COMPLETED: "lungxray:analysis-completed",
  ANALYSIS_RESET: "lungxray:analysis-reset",
  HISTORY_CHANGED: "lungxray:history-changed",
};

export function emit(name, detail = {}) {
  document.dispatchEvent(new CustomEvent(name, { detail }));
}
