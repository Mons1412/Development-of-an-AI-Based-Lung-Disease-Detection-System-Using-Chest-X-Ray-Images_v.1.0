import assert from "node:assert/strict";
import test from "node:test";

import { buildReportUrl } from "../../src/lung_xray_api/web/static/js/report/report-controller.js";

test("current report preview and download preserve every selected visualization in canonical order", () => {
  const preview = buildReportUrl("analysis-1", {
    selectedViews: ["donut-chart", "probability-bars", "column-chart"],
  });
  const pdf = buildReportUrl("analysis-1", {
    pdf: true,
    selectedViews: ["donut-chart", "probability-bars", "column-chart"],
  });

  assert.equal(
    preview,
    "/api/v1/analyses/analysis-1/report?view=probability-bars&view=column-chart&view=donut-chart",
  );
  assert.equal(
    pdf,
    "/api/v1/analyses/analysis-1/report.pdf?view=probability-bars&view=column-chart&view=donut-chart",
  );
});

test("history reports retain the backward-compatible presentation default", () => {
  assert.equal(
    buildReportUrl("analysis-2", { pdf: true }),
    "/api/v1/analyses/analysis-2/report.pdf",
  );
});
