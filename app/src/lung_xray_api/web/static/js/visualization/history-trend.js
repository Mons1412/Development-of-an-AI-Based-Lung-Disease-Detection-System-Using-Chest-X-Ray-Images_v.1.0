import { CLASS_COLORS, CLASS_LABELS } from "../core/constants.js";
import { clearElement } from "../core/dom.js";

const SVG_NS = "http://www.w3.org/2000/svg";

function node(name, attrs = {}, textContent = "") {
  const element = document.createElementNS(SVG_NS, name);
  Object.entries(attrs).forEach(([key, value]) => element.setAttribute(key, String(value)));
  if (textContent) element.textContent = textContent;
  return element;
}

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Không xác định";
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
  }).format(date);
}

export function renderHistoryTrend(container, records, className) {
  clearElement(container);
  if (records.length < 2) {
    const message = document.createElement("p");
    message.textContent = "Cần ít nhất hai lần phân tích của cùng một ca để hiển thị biểu đồ đường.";
    container.append(message);
    return;
  }

  const sorted = [...records].sort((a, b) => new Date(a.analyzed_at) - new Date(b.analyzed_at));
  const svg = node("svg", { viewBox: "0 0 760 300", role: "img" });
  svg.setAttribute(
    "aria-label",
    `Biểu đồ đường theo lịch sử xác suất đầu ra lớp ${CLASS_LABELS[className]}`,
  );

  const left = 64;
  const right = 724;
  const top = 28;
  const bottom = 236;
  const width = right - left;
  const height = bottom - top;

  [0, 0.5, 1].forEach((value) => {
    const y = bottom - value * height;
    svg.append(node("line", {
      x1: left,
      y1: y,
      x2: right,
      y2: y,
      stroke: value === 0 ? "#94a3b8" : "#dbe3ef",
      "stroke-dasharray": value === 0 ? "0" : "5 5",
    }));
    svg.append(node("text", {
      x: left - 12,
      y: y + 4,
      "text-anchor": "end",
      class: "chart-label",
    }, `${Math.round(value * 100)}%`));
  });

  svg.append(node("line", { x1: left, y1: top, x2: left, y2: bottom, stroke: "#94a3b8" }));

  const points = sorted.map((record, index) => {
    const x = left + (index / (sorted.length - 1)) * width;
    const value = Math.max(0, Math.min(1, Number(record[`${className}_probability`] || 0)));
    const y = bottom - value * height;
    return {
      x,
      y,
      value,
      analyzedAt: record.analyzed_at,
      analysisId: record.analysis_id,
    };
  });

  svg.append(node("polyline", {
    points: points.map((point) => `${point.x},${point.y}`).join(" "),
    fill: "none",
    stroke: CLASS_COLORS[className],
    "stroke-width": 3,
    "stroke-linejoin": "round",
    "stroke-linecap": "round",
  }));

  points.forEach((point, index) => {
    const circle = node("circle", {
      cx: point.x,
      cy: point.y,
      r: 5,
      fill: CLASS_COLORS[className],
      tabindex: 0,
    });
    circle.append(node(
      "title",
      {},
      `${formatDate(point.analyzedAt)} · ${(point.value * 100).toFixed(2)}% · ${point.analysisId}`,
    ));
    svg.append(circle);

    const shouldShowDate = points.length <= 6 || index === 0 || index === points.length - 1;
    if (shouldShowDate) {
      svg.append(node("text", {
        x: point.x,
        y: bottom + 24,
        "text-anchor": "middle",
        class: "chart-label",
      }, formatDate(point.analyzedAt)));
    }
  });

  svg.append(node("text", {
    x: (left + right) / 2,
    y: 286,
    "text-anchor": "middle",
    class: "chart-label",
  }, "Thời điểm phân tích"));
  svg.append(node("text", {
    x: 16,
    y: (top + bottom) / 2,
    transform: `rotate(-90 16 ${(top + bottom) / 2})`,
    "text-anchor": "middle",
    class: "chart-label",
  }, "Xác suất đầu ra"));

  container.append(svg);
}
