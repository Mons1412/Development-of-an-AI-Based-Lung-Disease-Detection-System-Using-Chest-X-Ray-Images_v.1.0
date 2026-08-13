export const RESULT_VIEW_IDS = Object.freeze({
  PROBABILITY_BARS: "probability-bars",
  COLUMN_CHART: "column-chart",
  DONUT_CHART: "donut-chart",
  DATA_TABLE: "data-table",
});

export const RESULT_VIEW_ORDER = Object.freeze([
  RESULT_VIEW_IDS.PROBABILITY_BARS,
  RESULT_VIEW_IDS.COLUMN_CHART,
  RESULT_VIEW_IDS.DONUT_CHART,
  RESULT_VIEW_IDS.DATA_TABLE,
]);

export const DEFAULT_RESULT_VIEWS = Object.freeze([
  RESULT_VIEW_IDS.PROBABILITY_BARS,
  RESULT_VIEW_IDS.COLUMN_CHART,
]);

export const RESULT_VIEW_LABELS = Object.freeze({
  [RESULT_VIEW_IDS.PROBABILITY_BARS]: "Thanh xác suất",
  [RESULT_VIEW_IDS.COLUMN_CHART]: "Biểu đồ cột",
  [RESULT_VIEW_IDS.DONUT_CHART]: "Biểu đồ tròn",
  [RESULT_VIEW_IDS.DATA_TABLE]: "Bảng số liệu",
});

export const RESULT_VIEW_SECTION_IDS = Object.freeze({
  [RESULT_VIEW_IDS.PROBABILITY_BARS]: "result-view-probability-bars",
  [RESULT_VIEW_IDS.COLUMN_CHART]: "result-view-column-chart",
  [RESULT_VIEW_IDS.DONUT_CHART]: "result-view-donut-chart",
  [RESULT_VIEW_IDS.DATA_TABLE]: "result-view-data-table",
});

export function normalizeResultViews(values) {
  const requested = new Set(Array.isArray(values) ? values : []);
  const normalized = RESULT_VIEW_ORDER.filter((view) => requested.has(view));
  return normalized.length > 0 ? normalized : [...DEFAULT_RESULT_VIEWS];
}

export function resultViewsEqual(left, right) {
  const normalizedLeft = normalizeResultViews(left);
  const normalizedRight = normalizeResultViews(right);
  return normalizedLeft.length === normalizedRight.length
    && normalizedLeft.every((value, index) => value === normalizedRight[index]);
}
