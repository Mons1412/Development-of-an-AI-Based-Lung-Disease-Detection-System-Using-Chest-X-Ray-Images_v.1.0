export class ApiError extends Error {
  constructor(message, status = 0, payload = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

function firstValidationMessage(items) {
  if (!Array.isArray(items)) return "";
  const first = items.find((item) => item && typeof item.msg === "string");
  return first?.msg || "";
}

function extractApiMessage(payload) {
  if (!payload || typeof payload !== "object") return String(payload || "");
  if (typeof payload.message === "string") return payload.message;
  if (typeof payload.detail === "string") return payload.detail;
  if (Array.isArray(payload.detail)) return firstValidationMessage(payload.detail);
  if (payload.detail && typeof payload.detail === "object") {
    if (typeof payload.detail.message === "string") return payload.detail.message;
    if (Array.isArray(payload.detail.errors)) return firstValidationMessage(payload.detail.errors);
  }
  return "";
}

export async function apiRequest(url, options = {}) {
  const response = await fetch(url, { cache: "no-store", ...options });
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();
  if (!response.ok) {
    const message = typeof payload === "object"
      ? extractApiMessage(payload) || "Yêu cầu không thành công"
      : payload || "Yêu cầu không thành công";
    throw new ApiError(String(message), response.status, payload);
  }
  return payload;
}
