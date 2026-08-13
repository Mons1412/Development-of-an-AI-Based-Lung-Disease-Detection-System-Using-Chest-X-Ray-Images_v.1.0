import { byId } from "../core/dom.js";
import { EVENTS } from "../core/events.js";
import { closeModal, openModal } from "../ui/modal.js";
import { showToast } from "../ui/toast.js";
import { openReportPreview } from "../report/report-controller.js";
import { renderHistoryTrend } from "../visualization/history-trend.js";
import { deleteHistoryRecord, getHistoryDetail, listHistory } from "./history-api.js";
import { renderHistoryDetail, renderHistoryList } from "./history-renderer.js";

export function createHistoryController() {
  const dialog = byId("history-dialog");
  const status = byId("history-status");
  let page = 1;
  let total = 0;
  let pageSize = 10;
  let listController = null;
  let currentItems = [];
  let detailRecords = [];
  let searchTimer = null;

  function params() {
    const search = byId("history-search").value.trim();
    return {
      page,
      page_size: pageSize,
      patient_query: search,
      predicted_label: byId("history-label-filter").value,
      date_from: byId("history-date-from").value,
      date_to: byId("history-date-to").value,
      sort_order: byId("history-sort").value,
      timezone_offset_minutes: -new Date().getTimezoneOffset(),
    };
  }

  async function load() {
    listController?.abort();
    listController = new AbortController();
    status.textContent = "Đang tải lịch sử…";
    try {
      const result = await listHistory(params(), listController.signal);
      currentItems = result.items;
      total = result.total;
      pageSize = result.page_size;
      renderHistoryList(result, {
        onDetail: showDetail,
        onReport: (id) => {
          try {
            openReportPreview(id);
          } catch (error) {
            showToast(error.message || "Không thể mở bản xem trước báo cáo.");
          }
        },
        onDelete: remove,
      });
      const lastPage = Math.max(1, Math.ceil(total / pageSize));
      byId("history-page-label").textContent = `Trang ${page} / ${lastPage}`;
      byId("history-prev").disabled = page <= 1;
      byId("history-next").disabled = page >= lastPage;
      status.textContent = `${total} lần phân tích.`;
      await prepareTrend();
    } catch (error) {
      if (error.name === "AbortError") return;
      status.textContent = error.message || "Không thể tải lịch sử.";
    }
  }

  async function prepareTrend() {
    const search = byId("history-search").value.trim();
    const section = byId("history-trend-section");
    if (!search) {
      section.hidden = true;
      detailRecords = [];
      return;
    }

    try {
      const trendPage = await listHistory(
        { ...params(), page: 1, page_size: 100 },
        listController?.signal,
      );
      const identityKeys = new Set(
        trendPage.items.map((item) => {
          if (item.is_anonymous_sample) return `anonymous:${item.analysis_id}`;
          if (item.patient_code) return `code:${item.patient_code.toLocaleLowerCase("vi")}`;
          return `name:${(item.patient_display_name || "").toLocaleLowerCase("vi")}`;
        }),
      );
      if (trendPage.items.length < 2 || identityKeys.size !== 1) {
        section.hidden = true;
        detailRecords = [];
        return;
      }
      const records = await Promise.all(
        trendPage.items.map((item) => getHistoryDetail(item.analysis_id).catch(() => null)),
      );
      detailRecords = records.filter(Boolean);
      section.hidden = detailRecords.length < 2;
      if (!section.hidden) renderTrend();
    } catch {
      section.hidden = true;
      detailRecords = [];
    }
  }


  function renderTrend() {
    renderHistoryTrend(
      byId("history-trend-chart"),
      detailRecords,
      byId("history-trend-class").value,
    );
  }

  async function showDetail(id) {
    try {
      const detail = await getHistoryDetail(id);
      renderHistoryDetail(detail);
      byId("history-detail").hidden = false;
    } catch (error) {
      showToast(error.message || "Không thể tải chi tiết.");
    }
  }

  async function remove(item) {
    const label = item.patient_display_name || item.patient_code || "ảnh ẩn danh";
    if (!window.confirm(`Xóa lịch sử của ${label} và thumbnail liên quan?`)) return;
    try {
      const result = await deleteHistoryRecord(item.analysis_id);
      showToast(result.cleanup_pending
        ? "Đã xóa lịch sử; thumbnail sẽ được dọn lại khi ứng dụng khởi động."
        : "Đã xóa lịch sử và thumbnail liên quan.");
      document.dispatchEvent(new CustomEvent(EVENTS.HISTORY_CHANGED));
      await load();
    } catch (error) {
      showToast(error.message || "Không thể xóa lịch sử.");
    }
  }

  byId("history-button").addEventListener("click", () => {
    openModal(dialog, byId("history-button"));
    load();
  });
  byId("history-filter-form").addEventListener("input", () => {
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(() => { page = 1; load(); }, 280);
  });
  byId("history-prev").addEventListener("click", () => { page = Math.max(1, page - 1); load(); });
  byId("history-next").addEventListener("click", () => { page += 1; load(); });
  byId("history-detail-close").addEventListener("click", () => { byId("history-detail").hidden = true; });
  byId("history-trend-class").addEventListener("change", renderTrend);
  document.addEventListener(EVENTS.HISTORY_CHANGED, () => { if (dialog.open) load(); });
  dialog.addEventListener("close", () => { listController?.abort(); byId("history-detail").hidden = true; });

  return { close: () => closeModal(dialog), refresh: load };
}
