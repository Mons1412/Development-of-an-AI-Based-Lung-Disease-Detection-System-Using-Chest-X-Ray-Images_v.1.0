import { byId, clearElement, text } from "../core/dom.js";
import { EVENTS } from "../core/events.js";
import { getAssistantStatus, queryAssistant } from "./assistant-api.js";
import { revealText } from "./message-animation.js";

const INITIAL_SUGGESTIONS = [
  "Ứng dụng hỗ trợ những gì?",
  "Tên tệp hợp lệ có định dạng nào?",
  "MobileNetV2 hoạt động như thế nào?",
];

const RESULT_SUGGESTIONS = [
  "Giải thích kết quả hiện tại",
  "Xác suất đầu ra có ý nghĩa gì?",
  "Giới hạn của mô hình là gì?",
];

function createMessage(role, value, className = "") {
  const message = document.createElement("article");
  message.className = `assistant-message assistant-message--${role} ${className}`.trim();
  const body = text("div", value);
  message.append(body);
  return { message, body };
}

function createTypingMessage(onlineConfigured = false) {
  const { message, body } = createMessage("assistant", "", "assistant-message--typing");
  const label = text(
    "span",
    onlineConfigured
      ? "Đang thử Gemini và chuẩn bị phương án ngoại tuyến an toàn…"
      : "Đang tra cứu kho kiến thức ngoại tuyến…",
    "visually-hidden",
  );
  const dots = document.createElement("span");
  dots.className = "typing-dots";
  dots.setAttribute("aria-hidden", "true");
  dots.append(document.createElement("i"), document.createElement("i"), document.createElement("i"));
  body.append(label, dots);
  return message;
}

export function buildAssistantContext(state) {
  const { phase, currentPrediction } = state;
  if (phase !== "success" || !currentPrediction) {
    return { application_stage: phase === "loading" ? "analysis_running" : "before_analysis" };
  }
  return {
    application_stage: "after_analysis",
    prediction_context: {
      predicted_label: currentPrediction.predicted_label,
      probabilities: { ...currentPrediction.probabilities },
      model_version: currentPrediction.model_version,
    },
  };
}

export function createAssistantController(store) {
  const launcher = byId("assistant-launcher");
  const panel = byId("assistant-panel");
  const closeButton = byId("assistant-close");
  const minimizeButton = byId("assistant-minimize");
  const skipButton = byId("assistant-skip");
  const newButton = byId("assistant-new");
  const form = byId("assistant-form");
  const input = byId("assistant-input");
  const send = byId("assistant-send");
  const messages = byId("assistant-messages");
  const suggestions = byId("assistant-suggestions");
  const modeBadge = byId("assistant-mode-badge");
  const onlineNotice = byId("assistant-online-notice");
  let requestController = null;
  let revealController = null;
  let onlineConfigured = false;
  let runtimeState = "disabled";
  let requestSequence = 0;

  function setModeBadge(state, model = null) {
    modeBadge.classList.remove(
      "assistant-mode-badge--online",
      "assistant-mode-badge--offline",
      "assistant-mode-badge--fallback",
      "assistant-mode-badge--configured",
      "assistant-mode-badge--warning",
    );

    if (state === "degraded_offline") {
      modeBadge.textContent = "Đã chuyển sang ngoại tuyến";
      modeBadge.classList.add("assistant-mode-badge--fallback");
      return;
    }

    if (state === "online_verified") {
      modeBadge.textContent = model ? `Gemini trực tuyến · ${model}` : "Gemini trực tuyến";
      modeBadge.classList.add("assistant-mode-badge--online");
      return;
    }

    if (state === "configured_unverified") {
      modeBadge.textContent = "Đã cấu hình Gemini";
      modeBadge.classList.add("assistant-mode-badge--configured");
      return;
    }

    if (state === "misconfigured") {
      modeBadge.textContent = "Gemini chưa được cấu hình";
      modeBadge.classList.add("assistant-mode-badge--warning");
      return;
    }

    modeBadge.textContent = "Ngoại tuyến";
    modeBadge.classList.add("assistant-mode-badge--offline");
  }

  function setOnlineNotice(visible) {
    onlineNotice.hidden = !visible;
  }

  async function refreshRuntimeStatus(scheduleFollowup = true) {
    try {
      const status = await getAssistantStatus();
      runtimeState = status.state;
      onlineConfigured = Boolean(status.configured);
      setModeBadge(runtimeState, status.model);
      setOnlineNotice(onlineConfigured);
      if (scheduleFollowup && runtimeState === "configured_unverified") {
        window.setTimeout(() => refreshRuntimeStatus(false), 1200);
      }
    } catch {
      onlineConfigured = false;
      runtimeState = "disabled";
      setModeBadge(runtimeState);
      setOnlineNotice(false);
    }
  }

  function currentContext() {
    return buildAssistantContext(store.getState());
  }

  function scrollToLatest() {
    messages.scrollTop = messages.scrollHeight;
  }

  function renderSuggestions(values) {
    clearElement(suggestions);
    values.slice(0, 3).forEach((value) => {
      const button = text("button", value);
      button.type = "button";
      button.addEventListener("click", () => {
        input.value = value;
        input.focus();
      });
      suggestions.append(button);
    });
  }

  function addAssistantMessage(answer, sources = [], disclaimer = "", className = "") {
    const { message, body } = createMessage("assistant", "", className);
    if (sources.length || disclaimer) {
      const details = document.createElement("details");
      details.className = "assistant-message__sources";
      const summary = text("summary", `Nguồn và lưu ý (${sources.length})`);
      const sourceList = document.createElement("ul");
      sources.forEach((source) => sourceList.append(text("li", source)));
      details.append(summary, sourceList);
      if (disclaimer) details.append(text("p", disclaimer));
      message.append(details);
    }
    messages.append(message);
    scrollToLatest();
    skipButton.hidden = false;
    return revealText(body, answer, { signal: revealController?.signal })
      .finally(() => { skipButton.hidden = true; })
      .then(scrollToLatest);
  }

  function resetConversation() {
    requestSequence += 1;
    requestController?.abort();
    revealController?.abort();
    requestController = null;
    revealController = null;
    clearElement(messages);
    const welcome = createMessage(
      "assistant",
      onlineConfigured
        ? "Xin chào. Tôi có thể dùng Gemini trực tuyến để diễn giải nội dung đã được kiểm soát. Khi mạng hoặc quota gặp lỗi, tôi tự chuyển về kho kiến thức ngoại tuyến."
        : "Xin chào. Tôi có thể hướng dẫn sử dụng ứng dụng, giải thích đầu ra mô hình và giới hạn của hệ thống bằng kho kiến thức ngoại tuyến.",
    );
    messages.append(welcome.message);
    renderSuggestions(store.getState().phase === "success" ? RESULT_SUGGESTIONS : INITIAL_SUGGESTIONS);
    input.value = "";
    send.disabled = false;
  }

  function open() {
    panel.hidden = false;
    launcher.setAttribute("aria-expanded", "true");
    input.focus();
    scrollToLatest();
  }

  function close() {
    panel.hidden = true;
    launcher.setAttribute("aria-expanded", "false");
    launcher.focus();
  }

  async function submit(event) {
    event.preventDefault();
    const value = input.value.trim();
    if (!value || send.disabled) return;

    const sequenceId = ++requestSequence;
    messages.append(createMessage("user", value).message);
    input.value = "";
    send.disabled = true;
    requestController?.abort();
    revealController?.abort();
    requestController = new AbortController();
    revealController = new AbortController();
    const typing = createTypingMessage(onlineConfigured);
    messages.append(typing);
    scrollToLatest();

    try {
      const startedAt = performance.now();
      const response = await queryAssistant(
        { message: value, ...currentContext() },
        requestController.signal,
      );
      if (sequenceId !== requestSequence) return;
      const minimumThinkingMs = 360;
      const wait = Math.max(0, minimumThinkingMs - (performance.now() - startedAt));
      if (wait) await new Promise((resolve) => window.setTimeout(resolve, wait));
      if (sequenceId !== requestSequence) return;
      typing.remove();
      runtimeState = response.fallback_used
        ? "degraded_offline"
        : (response.mode === "online" ? "online_verified" : runtimeState);
      setModeBadge(runtimeState, response.model);
      await addAssistantMessage(response.answer, response.sources, response.disclaimer);
      if (sequenceId !== requestSequence) return;
      renderSuggestions(response.suggested_questions?.length
        ? response.suggested_questions
        : (store.getState().phase === "success" ? RESULT_SUGGESTIONS : INITIAL_SUGGESTIONS));
    } catch (error) {
      typing.remove();
      if (sequenceId === requestSequence && error.name !== "AbortError") {
        await addAssistantMessage(
          `${error.message || "Không thể kết nối với trợ lý."} Bạn có thể thử gửi lại câu hỏi.`,
          [],
          "",
          "assistant-message--error",
        );
      }
    } finally {
      if (sequenceId === requestSequence) {
        requestController = null;
        send.disabled = false;
        input.focus();
      }
    }
  }

  launcher.addEventListener("click", () => (panel.hidden ? open() : close()));
  closeButton.addEventListener("click", close);
  minimizeButton.addEventListener("click", close);
  skipButton.addEventListener("click", () => revealController?.abort());
  newButton.addEventListener("click", resetConversation);
  form.addEventListener("submit", submit);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });
  document.addEventListener(EVENTS.ANALYSIS_RESET, () => {
    resetConversation();
  });
  document.addEventListener(EVENTS.ANALYSIS_COMPLETED, () => {
    renderSuggestions(RESULT_SUGGESTIONS);
  });

  refreshRuntimeStatus().finally(resetConversation);
  return { open, close, resetConversation, refreshRuntimeStatus };
}
