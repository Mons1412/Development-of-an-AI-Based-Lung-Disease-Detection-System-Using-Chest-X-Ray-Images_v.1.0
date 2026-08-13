class FakeClassList {
  constructor(owner) {
    this.owner = owner;
    this.values = new Set();
  }

  add(...values) { values.forEach((value) => this.values.add(value)); }

  remove(...values) { values.forEach((value) => this.values.delete(value)); }

  toggle(value, force) {
    const shouldAdd = force === undefined ? !this.values.has(value) : Boolean(force);
    if (shouldAdd) this.values.add(value);
    else this.values.delete(value);
    return shouldAdd;
  }

  contains(value) { return this.values.has(value); }

  toString() { return [...this.values].join(" "); }
}

class FakeTextNode {
  constructor(value) {
    this.nodeType = 3;
    this.textContent = String(value);
    this.parentElement = null;
  }
}

export class FakeElement {
  constructor(tagName, namespaceURI = null) {
    this.tagName = tagName.toUpperCase();
    this.namespaceURI = namespaceURI;
    this.children = [];
    this.parentElement = null;
    this.attributes = new Map();
    this.dataset = {};
    this.style = {};
    this.classList = new FakeClassList(this);
    this.hidden = false;
    this.checked = false;
    this.disabled = false;
    this.value = "";
    this.type = "";
    this._textContent = "";
    this.listeners = new Map();
  }

  get className() { return this.classList.toString(); }

  set className(value) {
    this.classList.values = new Set(String(value).split(/\s+/u).filter(Boolean));
  }

  get id() { return this.getAttribute("id") || ""; }

  set id(value) { this.setAttribute("id", value); }

  get textContent() { return this._textContent; }

  set textContent(value) {
    this._textContent = String(value);
    this.children = [];
  }

  get lastChild() { return this.children.at(-1) || null; }

  append(...nodes) {
    nodes.forEach((node) => {
      const child = typeof node === "string" ? new FakeTextNode(node) : node;
      child.parentElement = this;
      this.children.push(child);
    });
  }

  appendChild(node) {
    this.append(node);
    return node;
  }

  replaceChildren(...nodes) {
    this.children = [];
    this._textContent = "";
    if (nodes.length) this.append(...nodes);
  }

  setAttribute(name, value) {
    const text = String(value);
    this.attributes.set(name, text);
    if (name === "class") this.className = text;
    if (name === "id") this._id = text;
    if (name.startsWith("data-")) {
      const key = name.slice(5).replace(/-([a-z])/gu, (_, letter) => letter.toUpperCase());
      this.dataset[key] = text;
    }
  }

  getAttribute(name) { return this.attributes.get(name) ?? null; }

  removeAttribute(name) { this.attributes.delete(name); }

  addEventListener(type, listener) {
    if (!this.listeners.has(type)) this.listeners.set(type, []);
    this.listeners.get(type).push(listener);
  }

  dispatch(type, detail = {}) {
    (this.listeners.get(type) || []).forEach((listener) => listener({ target: this, ...detail }));
  }

  closest(selector) {
    let candidate = this;
    while (candidate) {
      if (matchesSelector(candidate, selector)) return candidate;
      candidate = candidate.parentElement;
    }
    return null;
  }

  querySelectorAll(selector) {
    return descendants(this).filter((element) => matchesSelector(element, selector));
  }

  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
}

function descendants(root) {
  const result = [];
  const visit = (node) => {
    node.children?.forEach((child) => {
      if (child instanceof FakeElement) {
        result.push(child);
        visit(child);
      }
    });
  };
  visit(root);
  return result;
}

function matchesSelector(element, selector) {
  if (!(element instanceof FakeElement)) return false;
  if (selector === "svg") return element.tagName === "SVG";
  if (selector === "tr") return element.tagName === "TR";
  if (selector.startsWith("#")) return element.id === selector.slice(1);
  const attribute = selector.match(/^\[([^=\]]+)(?:="([^"]*)")?\]$/u);
  if (!attribute) return false;
  const [, name, expected] = attribute;
  const actual = element.getAttribute(name);
  return actual !== null && (expected === undefined || actual === expected);
}

export function createFakeDocument() {
  const ids = new Map();
  const body = new FakeElement("body");
  return {
    body,
    createElement(tagName) { return new FakeElement(tagName); },
    createElementNS(namespaceURI, tagName) { return new FakeElement(tagName, namespaceURI); },
    createTextNode(value) { return new FakeTextNode(value); },
    getElementById(id) { return ids.get(id) || null; },
    querySelectorAll(selector) { return body.querySelectorAll(selector); },
    querySelector(selector) { return body.querySelector(selector); },
    register(element, id = element.id) {
      if (id) {
        element.id = id;
        ids.set(id, element);
      }
      body.append(element);
      return element;
    },
  };
}

export function installFakeDocument() {
  const document = createFakeDocument();
  globalThis.document = document;
  return document;
}

export function findAll(root, selector) {
  return root.querySelectorAll(selector);
}
