import { apiRequest } from "../core/api-client.js";

export function parseFilename(filename, signal) {
  return apiRequest("/api/v1/analyses/parse-filename", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename }),
    signal,
  });
}
