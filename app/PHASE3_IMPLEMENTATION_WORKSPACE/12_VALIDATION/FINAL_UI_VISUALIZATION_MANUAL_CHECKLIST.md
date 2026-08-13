# Final UI visualization manual checklist

## Gate and setup

- [ ] Start the app with the normal local command and open `/demo` with a hard refresh.
- [ ] Confirm the console prints exactly `[LungXrayUI] frontend build 20260728.1` and has no JavaScript error.
- [ ] Confirm the document contains one module entry, `/static/v/20260728.1/js/app.js`, and no loaded `demo.js`, `assistant.js`, or `report_export.js` entry.
- [ ] Confirm the page is usable with Internet disconnected; no external script, CDN, or AI request is made.

## Source and case information workspace

- [ ] On first load, the upload card, patient/case form, standalone result-view preference card, and action row have balanced widths and readable spacing.
- [ ] Select a valid image and confirm the preview, filename metadata, patient confirmation controls, and result-view preferences remain visible without overlap.
- [ ] Confirm the result-view preference fieldset is outside the patient/case fieldset and directly before the action buttons.
- [ ] Confirm the default selections are `Thanh xác suất` and `Biểu đồ cột`.
- [ ] Toggle any one, two, three, then all four cards. Each selected card has a clear checked and selected visual state.
- [ ] Try to uncheck the final selected card. It must remain checked and announce: `Cần chọn ít nhất một dạng hiển thị kết quả.`
- [ ] Use Tab, Space, and Shift+Tab to operate every checkbox card. Focus must be visible and labels must activate their checkbox.

## Prediction and visualization behavior

- [ ] Complete one successful prediction with two selected views. Only those two result sections are shown together; no tab switching is required.
- [ ] Add the remaining two selections after the successful result. The newly selected views appear together with the existing views without a second upload, inference request, or history record.
- [ ] Deselect a view after the result. Only that visual section is hidden; prediction text, analysis ID, actions, and the other selected views remain intact.
- [ ] Confirm probability bars, column bars, donut legend, and table use the same class colors for `normal`, `pneumonia`, and `tuberculosis`.
- [ ] Confirm the table has exactly three rows in `normal`, `pneumonia`, `tuberculosis` order and no technical JSON/debug dump is visible.
- [ ] Confirm the donut has exactly three colored segments, three legend items, a central predicted class, and the top model output percentage.
- [ ] Exercise representative probabilities including 100/0/0 and a near-zero value. The donut must not be blank, overflow, or duplicate segments.
- [ ] Select a new valid image after a prediction. Old result visuals and report/reference actions disappear; the current result-view preference is preserved.
- [ ] Press `Đặt lại`. Preview, patient data, prediction, assistant prediction context, and rendered views clear; result-view preferences return to default bars plus column chart.
- [ ] Cause validation and prediction failure. No stale chart, reference action, or PDF action from the prior result may remain visible.

## Responsive visual review

For each viewport below, capture a screenshot before prediction, after selecting all four views, and after reset.

| Viewport | Required checks | Screenshot recorded |
| --- | --- | --- |
| 1920 × 1080 | Balanced two-column workspace; all result sections readable. | [ ] |
| 1440 × 900 | No cramped patient fields or preference cards. | [ ] |
| 1366 × 768 | No horizontal page scroll; primary actions remain accessible. | [ ] |
| 1024 × 768 | Columns remain balanced or stack cleanly before collision. | [ ] |
| 768 × 1024 | Workspace stacks cleanly; cards remain two-column where space permits. | [ ] |
| 430 × 932 | One-column preferences; donut above legend; assistant launcher does not cover actions. | [ ] |
| 390 × 844 | No clipped text, SVG, table, or focus outline. | [ ] |
| 360 × 800 | No horizontal overflow; table has an intentional internal horizontal scroll only. | [ ] |

## Accessibility and interaction review

- [ ] Open/close the floating assistant and both existing modals with keyboard. Focus remains managed by the existing modal behavior.
- [ ] At mobile widths, the floating assistant launcher/panel does not cover the result-view controls or primary action buttons.
- [ ] Screen-reader review: checkbox group has a legend/help text; result update is announced once; SVG has a title and description; table has descriptive context.
- [ ] Verify reduced-motion preference avoids disruptive progress/typing animation.

## Cache and regression review

- [ ] In development/test, `/demo` and versioned static assets return `Cache-Control: no-store`.
- [ ] In production configuration, `/static/v/20260728.1/...` is immutable and legacy `/static/...` revalidates.
- [ ] Hard refresh and restart the app; the current build marker, CSS, and ES modules all update together.
- [ ] Re-run upload, patient confirmation, history, offline assistant, reference panel, and PDF export flows to confirm no regression outside visualization.

## Manual approval result

- Reviewer:
- Date/time:
- Browser/version:
- Result: [ ] PASS  [ ] FAIL
- Findings / screenshot paths:

