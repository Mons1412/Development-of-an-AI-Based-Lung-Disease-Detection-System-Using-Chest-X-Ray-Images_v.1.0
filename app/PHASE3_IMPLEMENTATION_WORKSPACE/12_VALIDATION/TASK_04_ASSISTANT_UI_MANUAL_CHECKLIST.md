# TASK 04 — Assistant UI Manual Approval Checklist

## Preconditions

1. Start the existing FastAPI demo and open `http://127.0.0.1:8000/demo`.
2. Use a valid JPG/JPEG/PNG image for the successful prediction path.
3. Use browser DevTools only for observing `window.lungXrayAssistantContext`; do not inject a different Knowledge Base or endpoint.

## Required screenshots

| Screenshot | Required evidence |
| --- | --- |
| Desktop before analysis | Full assistant panel, visible `Ngoại tuyến` badge, welcome message, six before-analysis suggestions |
| Desktop after analysis | Prediction result and assistant panel with after-analysis suggestions, one assistant response, sources, and disclaimer |
| Mobile width (320–620 px) | No horizontal overflow; chat bubbles, textarea, and both buttons remain usable |
| Error state | Assistant endpoint unavailable response shows `Không khả dụng` and prediction UI remains independent |
| Keyboard focus | Visible focus on suggestion, textarea, send button, and new-conversation button |

## Functional checks

- [ ] Panel title is exactly `Trợ lý thông tin X-quang phổi`.
- [ ] Before analysis, suggestions cover usage, formats, model classes, MobileNetV2, privacy, and model limitations.
- [ ] Typing a question and pressing Enter sends exactly one request; Shift + Enter adds a line break.
- [ ] Send is disabled and a loading status is announced while the request is pending.
- [ ] A successful assistant response renders answer, source IDs when supplied, and disclaimer as text rather than HTML.
- [ ] `Cuộc trò chuyện mới` clears the chat transcript, restores the welcome message, and does not alter a valid current prediction context.
- [ ] Assistant error presents `Không khả dụng`; image prediction remains usable.

## Prediction-context lifecycle checks

- [ ] On initial load, `window.lungXrayAssistantContext.stage` is `before_analysis` and all prediction fields are empty.
- [ ] On prediction submit, the stage becomes `analysis_running` before the request completes.
- [ ] On successful prediction, the global object has `stage: "after_analysis"`, the three probabilities, predicted label, model version, and processing time from that result.
- [ ] Selecting another image immediately resets stage to `before_analysis` and clears the previous probabilities/label.
- [ ] Removing the selected image, clicking demo `Chọn lại`, or using `Chọn ảnh khác` from a prediction error resets to `before_analysis`.
- [ ] A failed prediction produces `analysis_failed` with no old prediction fields.
- [ ] Under network throttling, select image B while image A is pending; a late response for A must not restore A's context or result.

## Accessibility checks

- [ ] The chat log announces added assistant messages without moving focus automatically.
- [ ] All controls are reachable by keyboard and have visible focus.
- [ ] The offline/unavailable state has text in addition to color.
- [ ] Long Vietnamese text wraps without clipping.
- [ ] With `prefers-reduced-motion: reduce`, no new essential animation is required for comprehension.
