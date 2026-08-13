import { apiRequest } from "../core/api-client.js";

export function createPersistedAnalysis(formData, signal) {
  return apiRequest("/api/v1/analyses", {
    method: "POST",
    body: formData,
    signal,
  });
}

export function getHealth(signal) {
  return apiRequest("/health/ready", { signal });
}

export function getModelInfo(signal) {
  return apiRequest("/api/v1/model-info", { signal });
}
