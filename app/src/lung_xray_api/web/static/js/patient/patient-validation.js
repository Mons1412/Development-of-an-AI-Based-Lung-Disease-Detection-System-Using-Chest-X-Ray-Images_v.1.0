const CODE_MIN_LENGTH = 2;
const CODE_MAX_LENGTH = 32;
const NAME_MIN_LENGTH = 2;
const NAME_MAX_LENGTH = 80;

const LETTER_OR_NUMBER = /[\p{L}\p{N}]/u;
const LETTER_OR_MARK = /[\p{L}\p{M}]/u;

function normalizeCode(value) {
  return String(value ?? "").normalize("NFC").trim();
}

function normalizeName(value) {
  return String(value ?? "")
    .normalize("NFC")
    .trim()
    .replace(/\s+/gu, " ");
}

export function validatePatientCode(value) {
  const code = normalizeCode(value);
  if (!code) return "";
  if (code.length < CODE_MIN_LENGTH || code.length > CODE_MAX_LENGTH) {
    return `Mã ca cần từ ${CODE_MIN_LENGTH} đến ${CODE_MAX_LENGTH} ký tự.`;
  }
  if (!LETTER_OR_NUMBER.test(code[0])) {
    return "Mã ca phải bắt đầu bằng chữ hoặc số.";
  }
  if (code.includes("--")) {
    return "Mã ca không được chứa hai dấu gạch ngang liên tiếp.";
  }
  for (const character of code) {
    if (!LETTER_OR_NUMBER.test(character) && character !== "-") {
      return "Mã ca chỉ gồm chữ, số và dấu gạch ngang; có thể để trống.";
    }
  }
  return "";
}

export function validatePatientName(value, anonymous) {
  if (anonymous) return "";
  const name = normalizeName(value);
  if (!name) return "Tên hiển thị là bắt buộc với ca có định danh.";
  if (name.length < NAME_MIN_LENGTH || name.length > NAME_MAX_LENGTH) {
    return `Tên hiển thị cần từ ${NAME_MIN_LENGTH} đến ${NAME_MAX_LENGTH} ký tự.`;
  }
  if (name.startsWith("-") || name.startsWith("'") || name.endsWith("-") || name.endsWith("'")) {
    return "Tên hiển thị có ký tự đầu hoặc cuối không hợp lệ.";
  }
  for (const character of name) {
    const allowed = LETTER_OR_MARK.test(character) || character === " " || character === "-" || character === "'";
    if (!allowed) {
      return "Tên hiển thị chỉ gồm chữ, khoảng trắng, dấu gạch ngang hoặc dấu nháy đơn.";
    }
  }
  return "";
}

export function validatePatientDraft(patient) {
  const code = validatePatientCode(patient.code);
  const name = validatePatientName(patient.name, patient.anonymous);
  let confirmation = "";
  let source = "";

  if (!patient.confirmed) {
    confirmation = "Bạn cần xác nhận thông tin trước khi phân tích.";
  }
  if (patient.anonymous && patient.source !== "anonymous") {
    source = "Ảnh ẩn danh phải sử dụng nguồn thông tin ẩn danh.";
  }
  if (!patient.anonymous && !["manual", "filename"].includes(patient.source)) {
    source = "Nguồn thông tin ca phân tích chưa hợp lệ.";
  }

  return { code, name, confirmation, source };
}
