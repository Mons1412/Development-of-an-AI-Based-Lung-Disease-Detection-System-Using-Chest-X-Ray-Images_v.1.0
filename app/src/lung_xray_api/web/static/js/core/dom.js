export function byId(id) {
  const element = document.getElementById(id);
  if (!element) throw new Error(`Missing required element: ${id}`);
  return element;
}

export function clearElement(element) {
  element.replaceChildren();
}

export function text(tag, value, className = "") {
  const element = document.createElement(tag);
  if (className) element.className = className;
  element.textContent = value;
  return element;
}
