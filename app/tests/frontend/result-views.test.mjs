import assert from "node:assert/strict";
import test from "node:test";

import {
  DEFAULT_RESULT_VIEWS,
  normalizeResultViews,
  RESULT_VIEW_IDS,
  RESULT_VIEW_LABELS,
  RESULT_VIEW_ORDER,
} from "../../src/lung_xray_api/web/static/js/core/result-views.js";

test("result-view contract has stable ordered IDs and default bars plus column chart", () => {
  assert.deepEqual(RESULT_VIEW_ORDER, [
    RESULT_VIEW_IDS.PROBABILITY_BARS,
    RESULT_VIEW_IDS.COLUMN_CHART,
    RESULT_VIEW_IDS.DONUT_CHART,
    RESULT_VIEW_IDS.DATA_TABLE,
  ]);
  assert.deepEqual(DEFAULT_RESULT_VIEWS, [
    RESULT_VIEW_IDS.PROBABILITY_BARS,
    RESULT_VIEW_IDS.COLUMN_CHART,
  ]);
  assert.equal(RESULT_VIEW_LABELS[RESULT_VIEW_IDS.DONUT_CHART], "Biểu đồ tròn");
});

test("normalization preserves contract order, discards unknown values, and keeps a usable fallback", () => {
  assert.deepEqual(
    normalizeResultViews(["data-table", "unknown", "probability-bars"]),
    [RESULT_VIEW_IDS.PROBABILITY_BARS, RESULT_VIEW_IDS.DATA_TABLE],
  );
  assert.deepEqual(normalizeResultViews([]), DEFAULT_RESULT_VIEWS);
  assert.deepEqual(normalizeResultViews(null), DEFAULT_RESULT_VIEWS);
});
