export function formatPercent(value) {
  return `${(Number(value) * 100).toFixed(2)}%`;
}
export function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}
export function formatDateTime(value) {
  return new Intl.DateTimeFormat("vi-VN", { dateStyle: "short", timeStyle: "medium" }).format(new Date(value));
}
