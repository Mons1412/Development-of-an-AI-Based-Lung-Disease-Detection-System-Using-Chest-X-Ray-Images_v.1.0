import { openReportPreview } from "../report/report-controller.js";
import { CLASS_LABELS } from "../core/constants.js";
import { byId, clearElement, text } from "../core/dom.js";
import { showToast } from "../ui/toast.js";
import { formatDateTime, formatPercent } from "../ui/formatters.js";

function frontendAssetUrl(relativePath) {
  const base = document.querySelector('meta[name="frontend-static-base"]')?.content || "/static";
  return `${base.replace(/\/$/u, "")}/${relativePath}`;
}

export function renderHistoryList(page, handlers) {
  const list = byId("history-list");
  clearElement(list);
  if (!page.items.length) {
    list.append(text("p", "Không có lần phân tích phù hợp.", "inline-alert"));
    return;
  }
  page.items.forEach((item) => {
    const card = document.createElement("article");
    card.className = "history-card";
    const image = document.createElement("img");
    image.loading = "lazy";
    image.alt = "Thumbnail ảnh X-quang";
    image.src = item.thumbnail_available
      ? `/api/v1/analyses/${encodeURIComponent(item.analysis_id)}/thumbnail`
      : frontendAssetUrl("assets/lungs-result.svg");
    const copy = document.createElement("div");
    const title = item.is_anonymous_sample
      ? "Ca ẩn danh / ảnh minh họa"
      : item.patient_display_name || item.patient_code || "Ca không tên";
    copy.append(
      text("h3", title),
      text("p", `${CLASS_LABELS[item.predicted_label]} · ${formatPercent(item.model_probability)}`),
      text("p", `${formatDateTime(item.analyzed_at)} · Model ${item.model_version}`),
    );
    const actions = document.createElement("div");
    actions.className = "history-card__actions";
    const detail = text("button", "Xem", "button button--secondary button--small");
    detail.type = "button";
    detail.addEventListener("click", () => handlers.onDetail(item.analysis_id));
    const report = text("button", "Xem PDF", "button button--ghost button--small");
    report.type = "button";
    report.addEventListener("click", () => handlers.onReport(item.analysis_id));
    const remove = text("button", "Xóa", "button button--ghost button--small");
    remove.type = "button";
    remove.addEventListener("click", () => handlers.onDelete(item));
    actions.append(detail, report, remove);
    card.append(image, copy, actions);
    list.append(card);
  });
}

export function renderHistoryDetail(detail) {
  const container = byId("history-detail-content");
  clearElement(container);
  const grid = document.createElement("div");
  grid.className = "history-detail-grid";
  const image = document.createElement("img");
  image.alt = "Thumbnail ảnh X-quang của lần phân tích";
  image.src = detail.thumbnail_url || frontendAssetUrl("assets/lungs-result.svg");
  const data = document.createElement("dl");
  data.className = "file-metadata";
  const values = [
    ["Mã phân tích", detail.analysis_id],
    ["Bệnh nhân / ca", detail.is_anonymous_sample ? "Ca ẩn danh / ảnh minh họa" : detail.patient_display_name],
    ["Mã người bệnh / mã ca", detail.patient_code || "Không cung cấp"],
    ["Tệp ảnh ban đầu", detail.original_filename],
    ["Kết quả", `${CLASS_LABELS[detail.predicted_label]} (${detail.predicted_label})`],
    ["Bình thường", formatPercent(detail.normal_probability)],
    ["Viêm phổi", formatPercent(detail.pneumonia_probability)],
    ["Lao phổi", formatPercent(detail.tuberculosis_probability)],
    ["Thời điểm", formatDateTime(detail.analyzed_at)],
    ["Phiên bản mô hình", detail.model_version],
    ["Phiên bản kho tri thức", detail.knowledge_base_version || "Không khả dụng"],
  ];
  values.forEach(([label, value]) => {
    const wrapper = document.createElement("div");
    wrapper.append(text("dt", label), text("dd", String(value || "—")));
    data.append(wrapper);
  });
  const actions = document.createElement("div");
  actions.className = "primary-actions";
  const report = text("button", "Xem trước báo cáo PDF", "button button--primary");
  report.type = "button";
  report.addEventListener("click", () => {
    try {
      openReportPreview(detail.analysis_id);
    } catch (error) {
      showToast(error.message || "Không thể mở bản xem trước báo cáo.");
    }
  });
  actions.append(report);
  const right = document.createElement("div");
  right.append(data, text("p", detail.prediction_disclaimer, "academic-notice"), actions);
  grid.append(image, right);
  container.append(grid);
}
