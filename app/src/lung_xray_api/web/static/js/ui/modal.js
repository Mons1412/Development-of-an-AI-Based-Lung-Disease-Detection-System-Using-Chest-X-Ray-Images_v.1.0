const focusOrigins = new WeakMap();

export function openModal(dialog, origin = document.activeElement) {
  if (!(dialog instanceof HTMLDialogElement)) return;
  if (origin instanceof HTMLElement) focusOrigins.set(dialog, origin);
  if (!dialog.open) dialog.showModal();
}

export function closeModal(dialog) {
  if (!(dialog instanceof HTMLDialogElement)) return;
  if (dialog.open) dialog.close();
  const focusOrigin = focusOrigins.get(dialog);
  if (focusOrigin instanceof HTMLElement) focusOrigin.focus();
}

export function initializeModalControls() {
  document.querySelectorAll("[data-modal-close]").forEach((button) => {
    button.addEventListener("click", () => {
      const dialog = document.getElementById(button.dataset.modalClose || "");
      closeModal(dialog);
    });
  });
  document.querySelectorAll("dialog").forEach((dialog) => {
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) closeModal(dialog);
    });
  });
}
