import { byId } from "../core/dom.js";

let hideTimer = null;
export function showToast(message, duration = 2600) {
  const toast = byId("toast");
  toast.textContent = message;
  toast.hidden = false;
  window.clearTimeout(hideTimer);
  hideTimer = window.setTimeout(() => { toast.hidden = true; }, duration);
}
