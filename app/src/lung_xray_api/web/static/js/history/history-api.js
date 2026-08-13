import { apiRequest } from "../core/api-client.js";

export function listHistory(params, signal) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== "" && value !== null && value !== undefined) query.set(key, value);
  });
  return apiRequest(`/api/v1/analyses?${query.toString()}`, { signal });
}

export function getHistoryDetail(analysisId, signal) {
  return apiRequest(`/api/v1/analyses/${encodeURIComponent(analysisId)}`, { signal });
}

export function deleteHistoryRecord(analysisId, signal) {
  return apiRequest(`/api/v1/analyses/${encodeURIComponent(analysisId)}`, {
    method: "DELETE",
    signal,
  });
}
