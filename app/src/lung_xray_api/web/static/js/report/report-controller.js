import { byId } from "../core/dom.js";
import { normalizeResultViews } from "../core/result-views.js";
import { showToast } from "../ui/toast.js";

function sanitizeDownloadFilename(value, fallback) {
  const normalized = String(value || "")
    .replace(/[\r\n]/g, " ")
    .replace(/[<>:"/\\|?*\u0000-\u001f]/g, "-")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/[. ]+$/g, "");
  if (!normalized) return fallback;
  return normalized.toLowerCase().endsWith(".pdf") ? normalized : `${normalized}.pdf`;
}

export function filenameFromContentDisposition(disposition, fallback) {
  if (!disposition) return fallback;

  const utf8Match = disposition.match(/filename\*\s*=\s*UTF-8''([^;]+)/i);
  if (utf8Match) {
    try {
      return sanitizeDownloadFilename(decodeURIComponent(utf8Match[1].trim()), fallback);
    } catch {
      // Continue to the ASCII fallback when a malformed header is received.
    }
  }

  const quotedMatch = disposition.match(/filename\s*=\s*"([^"]+)"/i);
  if (quotedMatch) return sanitizeDownloadFilename(quotedMatch[1], fallback);

  const plainMatch = disposition.match(/filename\s*=\s*([^;]+)/i);
  return sanitizeDownloadFilename(plainMatch?.[1], fallback);
}

export function buildReportUrl(analysisId, { pdf = false, selectedViews } = {}) {
  const path = `/api/v1/analyses/${encodeURIComponent(analysisId)}/report${pdf ? ".pdf" : ""}`;
  if (!Array.isArray(selectedViews)) return path;
  const query = new URLSearchParams();
  normalizeResultViews(selectedViews).forEach((view) => query.append("view", view));
  return `${path}?${query.toString()}`;
}

export function openReportPreview(analysisId, selectedViews) {
  const preview = window.open(
    buildReportUrl(analysisId, { selectedViews }),
    "_blank",
  );
  if (!preview) throw new Error("Trình duyệt đã chặn cửa sổ xem trước báo cáo.");
  try {
    preview.opener = null;
  } catch {
    // The preview remains safe when the browser prevents this assignment.
  }
}

export async function downloadReportPdf(analysisId, selectedViews) {
  const response = await fetch(
    buildReportUrl(analysisId, { pdf: true, selectedViews }),
    { cache: "no-store" },
  );
  if (!response.ok) {
    let message = "Không thể tạo file PDF.";
    try {
      const payload = await response.json();
      message = payload.detail || payload.message || message;
    } catch {
      // The response may not be JSON; keep the controlled Vietnamese message.
    }
    throw new Error(message);
  }

  const blob = await response.blob();
  if (blob.type !== "application/pdf") {
    throw new Error("Server không trả về đúng định dạng PDF.");
  }

  const fallback = `Bao_cao_phan_loai_X_quang_phoi_${analysisId}.pdf`;
  const filename = filenameFromContentDisposition(
    response.headers.get("Content-Disposition"),
    fallback,
  );
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

export function createReportController(store) {
  const previewButton = byId("preview-report-button");
  const exportButton = byId("export-report-button");

  previewButton.addEventListener("click", () => {
    const state = store.getState();
    const analysisId = state.analysisId;
    if (!analysisId) {
      showToast("Chưa có lần phân tích hợp lệ để xem trước báo cáo.");
      return;
    }
    try {
      openReportPreview(analysisId, state.selectedResultViews);
    } catch (error) {
      showToast(error.message || "Không thể mở bản xem trước báo cáo.");
    }
  });

  exportButton.addEventListener("click", async () => {
    const analysisId = store.getState().analysisId;
    if (!analysisId) {
      showToast("Chưa có lần phân tích hợp lệ để xuất báo cáo.");
      return;
    }

    exportButton.disabled = true;
    const originalLabel = exportButton.textContent;
    exportButton.textContent = "Đang tạo PDF…";
    try {
      await downloadReportPdf(analysisId, store.getState().selectedResultViews);
      showToast("Đã tạo và tải báo cáo PDF.");
    } catch (error) {
      showToast(error.message || "Không thể tải báo cáo PDF.");
    } finally {
      exportButton.disabled = false;
      exportButton.textContent = originalLabel;
    }
  });
  return {};
}
