export const CLASS_ORDER = ["normal", "pneumonia", "tuberculosis"];
export const CLASS_LABELS = {
  normal: "Bình thường",
  pneumonia: "Viêm phổi",
  tuberculosis: "Lao phổi",
};
export const CLASS_COLORS = {
  normal: "#16866b",
  pneumonia: "#d98200",
  tuberculosis: "#d24b45",
};
export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
export const ACCEPTED_TYPES = new Set(["image/jpeg", "image/png"]);
export const DEFAULT_ASSISTANT_SUGGESTIONS = [
  "Ứng dụng hỗ trợ những lớp nào?",
  "Làm sao tải ảnh để phân tích?",
  "MobileNetV2 là gì?",
  "Dữ liệu được lưu như thế nào?",
];
export const AFTER_ANALYSIS_SUGGESTIONS = [
  "Giải thích kết quả hiện tại",
  "Xác suất của mô hình có ý nghĩa gì?",
  "Giới hạn của mô hình là gì?",
  "Làm sao phân tích ảnh khác?",
];
