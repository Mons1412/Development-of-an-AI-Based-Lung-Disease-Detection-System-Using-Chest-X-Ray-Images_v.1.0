import { CLASS_COLORS, CLASS_LABELS, CLASS_ORDER } from "../core/constants.js";
import { clearElement } from "../core/dom.js";
import { formatPercent } from "../ui/formatters.js";

const SVG_NS = "http://www.w3.org/2000/svg";

function svgElement(name, attributes = {}) {
  const element = document.createElementNS(SVG_NS, name);

  Object.entries(attributes).forEach(([key, value]) => {
    element.setAttribute(key, String(value));
  });

  return element;
}

function appendSvgText(svg, content, attributes = {}) {
  const element = svgElement("text", attributes);
  element.textContent = content;
  svg.append(element);
  return element;
}

function clampProbability(value) {
  const numericValue = Number(value);

  if (!Number.isFinite(numericValue)) {
    return 0;
  }

  return Math.min(1, Math.max(0, numericValue));
}

function probabilityEntries(probabilities) {
  return CLASS_ORDER.map((label) => [
    label,
    clampProbability(probabilities?.[label]),
  ]);
}

function normalizedSegments(entries) {
  const total = entries.reduce((sum, [, value]) => sum + value, 0);

  if (total <= 0) {
    return entries.map(([label]) => [label, 0]);
  }

  return entries.map(([label, value]) => [label, value / total]);
}

function resolvePredictedLabel(entries, predictedLabel) {
  if (CLASS_ORDER.includes(predictedLabel)) {
    return predictedLabel;
  }

  return [...entries].sort(
    (left, right) => right[1] - left[1],
  )[0]?.[0] ?? CLASS_ORDER[0];
}

/**
 * Render biểu đồ cột cho ba lớp phân loại.
 *
 * Dữ liệu đầu vào phải là probability đã được backend chuẩn hóa.
 * Hàm luôn xóa SVG cũ trước khi vẽ để tránh trùng biểu đồ sau
 * nhiều lần phân tích hoặc thay đổi dạng hiển thị.
 */
export function renderResultChart(container, probabilities) {
  clearElement(container);
  container.classList.add("chart-container--column");

  const entries = probabilityEntries(probabilities);

  const svg = svgElement("svg", {
    viewBox: "0 0 420 390",
    role: "img",
    "aria-labelledby":
      "result-column-chart-title-svg result-column-chart-description-svg",
    preserveAspectRatio: "xMidYMid meet",
    "data-chart": "column",
  });

  svg.classList.add("column-chart__svg");

  const title = svgElement("title", {
    id: "result-column-chart-title-svg",
  });

  title.textContent = "Biểu đồ cột xác suất đầu ra của ba lớp";

  const description = svgElement("desc", {
    id: "result-column-chart-description-svg",
  });

  description.textContent = entries
    .map(
      ([label, value]) =>
        `${CLASS_LABELS[label]} ${formatPercent(value)}`,
    )
    .join(", ");

  svg.append(title, description);

  /*
   * Vùng vẽ được thu gọn để cột sử dụng phần lớn chiều cao SVG,
   * tránh trường hợp biểu đồ nhỏ nằm giữa một card quá nhiều khoảng trắng.
   */
  const plot = {
    left: 42,
    right: 400,
    top: 30,
    bottom: 288,
  };

  const plotWidth = plot.right - plot.left;
  const plotHeight = plot.bottom - plot.top;
  const slotWidth = plotWidth / entries.length;
  const barWidth = Math.min(72, slotWidth * 0.56);

  /*
   * Ba đường tham chiếu đủ để người dùng đọc nhanh:
   * 0%, 50% và 100%.
   */
  [0, 0.5, 1].forEach((gridValue) => {
    const y = plot.bottom - gridValue * plotHeight;

    svg.append(
      svgElement("line", {
        x1: plot.left,
        x2: plot.right,
        y1: y,
        y2: y,
        class: "chart-gridline",
      }),
    );

    appendSvgText(svg, `${Math.round(gridValue * 100)}%`, {
      x: plot.left - 12,
      y: y + 4,
      "text-anchor": "end",
      class: "chart-axis-label",
    });
  });

  svg.append(
    svgElement("line", {
      x1: plot.left,
      x2: plot.right,
      y1: plot.bottom,
      y2: plot.bottom,
      class: "chart-baseline",
    }),
  );

  entries.forEach(([label, value], index) => {
    const slotStart = plot.left + index * slotWidth;
    const x = slotStart + (slotWidth - barWidth) / 2;

    const rawHeight = value * plotHeight;

    /*
     * Giá trị rất nhỏ vẫn có một vạch tối thiểu 3px để người dùng
     * nhận biết lớp đó không hoàn toàn bằng 0.
     */
    const visualHeight =
      value > 0 ? Math.max(3, rawHeight) : 0;

    const y = plot.bottom - visualHeight;

    const group = svgElement("g", {
      class: "column-chart__group",
      "data-class": label,
    });

    const bar = svgElement("rect", {
      x,
      y,
      width: barWidth,
      height: visualHeight,
      rx: 9,
      fill: CLASS_COLORS[label],
      class: "column-chart__bar",
      "data-column-segment": "true",
      "data-class": label,
      "data-probability": value.toFixed(8),
    });

    const barTitle = svgElement("title");

    barTitle.textContent =
      `${CLASS_LABELS[label]}: ${formatPercent(value)}`;

    bar.append(barTitle);
    group.append(bar);

    appendSvgText(group, formatPercent(value), {
      x: x + barWidth / 2,
      y: Math.max(plot.top + 13, y - 10),
      "text-anchor": "middle",
      class: "chart-value",
    });

    appendSvgText(group, CLASS_LABELS[label], {
      x: x + barWidth / 2,
      y: 332,
      "text-anchor": "middle",
      class: "chart-label",
    });

    appendSvgText(group, label, {
      x: x + barWidth / 2,
      y: 354,
      "text-anchor": "middle",
      class: "chart-sublabel",
    });

    svg.append(group);
  });

  container.append(svg);
}

function createDonutLegend(entries) {
  const legend = document.createElement("ul");

  legend.className = "donut-legend";

  entries.forEach(([label, value]) => {
    const item = document.createElement("li");

    item.className = "donut-legend__item";
    item.dataset.class = label;

    const marker = document.createElement("span");

    marker.className = "donut-legend__swatch";
    marker.style.backgroundColor = CLASS_COLORS[label];
    marker.setAttribute("aria-hidden", "true");

    const copy = document.createElement("span");

    copy.className = "donut-legend__copy";

    const labelText = document.createElement("span");

    labelText.className = "donut-legend__label";
    labelText.textContent = CLASS_LABELS[label];

    const technicalLabel = document.createElement("span");

    technicalLabel.className = "donut-legend__technical";
    technicalLabel.textContent = label;

    copy.append(labelText, technicalLabel);

    const valueText = document.createElement("strong");

    valueText.className = "donut-legend__value";
    valueText.textContent = formatPercent(value);

    item.append(marker, copy, valueText);
    legend.append(item);
  });

  return legend;
}

/**
 * Render biểu đồ donut và phần chú thích HTML.
 *
 * SVG chỉ chịu trách nhiệm vẽ vòng tròn. Legend sử dụng HTML riêng
 * để có thể xuống dòng và responsive tốt hơn trên card hẹp.
 */
export function renderResultDonut(
  container,
  probabilities,
  predictedLabel,
) {
  clearElement(container);
  container.classList.add("chart-container--donut");

  const rawEntries = probabilityEntries(probabilities);
  const segments = normalizedSegments(rawEntries);

  const resolvedPrediction = resolvePredictedLabel(
    rawEntries,
    predictedLabel,
  );

  const predictionValue =
    rawEntries.find(
      ([label]) => label === resolvedPrediction,
    )?.[1] ?? 0;

  const visual = document.createElement("div");

  visual.className = "donut-layout";

  const svg = svgElement("svg", {
    viewBox: "0 0 280 280",
    role: "img",
    "aria-labelledby":
      "result-donut-title-svg result-donut-description-svg",
    preserveAspectRatio: "xMidYMid meet",
    "data-chart": "donut",
  });

  svg.classList.add("donut-chart__svg");

  const title = svgElement("title", {
    id: "result-donut-title-svg",
  });

  title.textContent =
    "Biểu đồ tròn tỷ trọng xác suất đầu ra của ba lớp";

  const description = svgElement("desc", {
    id: "result-donut-description-svg",
  });

  description.textContent = rawEntries
    .map(
      ([label, value]) =>
        `${CLASS_LABELS[label]} ${formatPercent(value)}`,
    )
    .join(", ");

  svg.append(title, description);

  const center = 140;
  const radius = 84;
  const strokeWidth = 34;
  const circumference = 2 * Math.PI * radius;

  svg.append(
    svgElement("circle", {
      cx: center,
      cy: center,
      r: radius,
      fill: "none",
      stroke: "#e8edf4",
      "stroke-width": strokeWidth,
      class: "donut-chart__track",
    }),
  );

  let offsetLength = 0;

  const visibleCount = segments.filter(
    ([, value]) => value > 0,
  ).length;

  segments.forEach(([label, value]) => {
    const segmentLength = value * circumference;

    /*
     * Tạo khoảng tách nhỏ giữa các segment nhưng không làm mất
     * khả năng hiển thị của các xác suất rất thấp.
     */
    const gapLength =
      visibleCount > 1 && value > 0
        ? Math.min(4, segmentLength * 0.3)
        : 0;

    const visibleLength = Math.max(
      0,
      segmentLength - gapLength,
    );

    const segment = svgElement("circle", {
      cx: center,
      cy: center,
      r: radius,
      fill: "none",
      stroke: CLASS_COLORS[label],
      "stroke-width": strokeWidth,
      "stroke-dasharray":
        `${visibleLength} ${Math.max(
          0,
          circumference - visibleLength,
        )}`,
      "stroke-dashoffset": `${-offsetLength}`,
      "stroke-linecap": "butt",
      transform: `rotate(-90 ${center} ${center})`,
      class: "donut-chart__segment",
      "data-donut-segment": "true",
      "data-class": label,
      "data-probability": value.toFixed(8),
    });

    const rawValue =
      rawEntries.find(
        ([entryLabel]) => entryLabel === label,
      )?.[1] ?? 0;

    const segmentTitle = svgElement("title");

    segmentTitle.textContent =
      `${CLASS_LABELS[label]}: ${formatPercent(rawValue)}`;

    segment.append(segmentTitle);
    svg.append(segment);

    offsetLength += segmentLength;
  });

  appendSvgText(svg, CLASS_LABELS[resolvedPrediction], {
    x: center,
    y: center - 7,
    "text-anchor": "middle",
    class: "donut-center-label",
  });

  appendSvgText(svg, formatPercent(predictionValue), {
    x: center,
    y: center + 27,
    "text-anchor": "middle",
    class: "donut-center-value",
  });

  visual.append(
    svg,
    createDonutLegend(rawEntries),
  );

  container.append(visual);
}
