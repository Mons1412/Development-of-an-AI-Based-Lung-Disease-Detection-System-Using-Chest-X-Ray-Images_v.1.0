import { apiRequest } from "../core/api-client.js";

export function queryAssistant(payload, signal) {
  return apiRequest("/api/v1/assistant/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
}

export function getAssistantStatus(signal) {
  return apiRequest("/api/v1/assistant/status", {
    method: "GET",
    signal,
  });
}
