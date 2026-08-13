# TASK 05 — Teacher UI (không bao gồm PDF)

Ngày thực hiện: 2026-07-27  
Phạm vi: tích hợp giao diện đã duyệt vào `/demo` của FastAPI/Jinja2; không thay đổi
prediction algorithm, model artifact, assistant backend, Knowledge Base hoặc API contract.

## Kết quả

- Đã tích hợp logo Đại học Nguyễn Tất Thành, tên dự án, trạng thái API/model và
  phiên bản model vào header hiện hữu.
- Vùng kết quả sử dụng ngôn ngữ an toàn: **“Kết quả phân loại của mô hình”**,
  có nhãn tiếng Việt/API, xác suất chính, ba thanh xác suất, model version,
  processing time và disclaimer.
- Đã thêm nút `Xem thông tin tham khảo` sau prediction thành công. Modal này chỉ
  hiển thị output model cùng source `MODEL_ARTIFACT_1_1_0`; clinical content
  production chưa có nên hiển thị đúng trạng thái `Nội dung chuyên môn đang chờ duyệt`.
  Không nạp Knowledge Base development/pending và không hiển thị điều trị, thuốc hay liều dùng.
- Đã thêm modal `Về dự án`, footer nhóm, responsive styles và modal keyboard/focus behavior.
- Không có nút PDF, visitor counter, model bổ sung, database hoặc external AI/API.

## Files changed

| Path | Thay đổi |
| --- | --- |
| `src/lung_xray_api/web/templates/demo.html` | Header branding, wording kết quả, action tham khảo, footer và hai native dialogs. |
| `src/lung_xray_api/web/static/demo.js` | Model-version header, lifecycle reference context, native dialog open/close/focus restore. |
| `src/lung_xray_api/web/static/demo.css` | Responsive layout, styles header/footer/modal, focus-visible và result action. |
| `src/lung_xray_api/web/static/assets/nttu_logo.png` | Bản copy nguyên trạng của approved NTTU logo asset. |
| `tests/integration/test_demo_ui.py` | Cập nhật assertion UI và static asset NTTU. |
| `tests/unit/test_teacher_ui_contract.py` | Contract tests cho clinical gate, modal accessibility, stale prediction reset và responsive styles. |

## UI state model

`demo.js` vẫn giữ owner của prediction flow. Các trạng thái quan sát được:

| State | Owner / transition | Teacher UI behavior |
| --- | --- | --- |
| Initial / reset | `resetDemo()` | Kết quả rỗng, reference action ẩn, assistant context `before_analysis`. |
| Image selected | `handleFileSelection()` → `renderImagePreview()` | Xóa reference của prediction cũ trước validation/render preview. |
| Analyzing | `submitPrediction()` | Giữ prediction flow cũ, trạng thái loading; assistant context `analysis_running`. |
| Success | `renderPrediction()` | Hiển thị output model, ba probability bars và enable reference action cho đúng result hiện tại. |
| Invalid file | `validateClientFile()` / `showFileError()` | Hiển thị lỗi upload, không cho dùng prediction context cũ. |
| Model unavailable | `checkApiHealth()` / request error | Badge API báo chưa sẵn sàng; header model version báo `Chưa sẵn sàng` khi health check fail. |
| Failed prediction | `renderError()` | Reference action bị ẩn và assistant context chuyển `analysis_failed`. |

`clearCurrentPrediction()` được gọi khi chọn tệp mới, lỗi prediction và reset; do đó modal
reference không thể dùng output cũ cho ảnh mới.

## Accessibility và responsive

- Dùng native `<dialog>`: `showModal()` tạo focus trap của browser; `Escape`, click backdrop
  và close button đều đóng modal; focus được trả về trigger.
- Các buttons có label/`aria-controls`/`aria-haspopup="dialog"`; close buttons có accessible name.
- Có `:focus-visible`, reduced-motion support kế thừa, contrast cho badge/clinical gate/disclaimer.
- Runtime check xác nhận không horizontal overflow ở viewport 390 px; modal mobile nằm hoàn toàn
  trong viewport (left 19 px, right 371 px).

## Requirement traceability

| Requirement | Implementation path | Test / evidence | Status |
| --- | --- | --- | --- |
| Logo NTTU, title, academic label, API/model status, version, responsive header | `demo.html`, `demo.css`, `demo.js`, `static/assets/nttu_logo.png` | `test_demo_ui.py`; Edge local runtime: logo loaded, API ready, version `1.1.0` | Complete |
| Result language, Vietnamese/API label, main probability, 3 bars, version/time, disclaimer | `demo.html` result section; existing `renderPrediction()` | Full pytest regression; actual local UI success state | Complete |
| Reference action only after success | `#reference-info-button`, `renderPrediction()`, `clearCurrentPrediction()` | `test_teacher_ui_contract.py`; Edge local runtime | Complete |
| Production-only disease/reference content, sources, medical disclaimer, no treatment | `#reference-info-modal` | Static contract test; runtime modal showed `MODEL_ARTIFACT_1_1_0` and clinical gate | Complete with honest unavailable-content state |
| About Project | `#about-project-modal` | Edge local modal open/Escape/focus-return runtime check | Complete |
| Footer team/academic disclaimer | `project-footer` in `demo.html` | `test_demo_ui.py`; source matches approved `team.json` | Complete pending name confirmation |
| UX states initial/selected/analyzing/success/invalid/model unavailable/failure/reset | Existing `demo.js` state owner plus Task 05 reference reset hooks | Full regression + browser success/reset flow | Complete |
| Keyboard, focus, desktop/mobile | `demo.js` modal controls; `demo.css` media rules | Unit contract tests + Edge 1440 px / 390 px runtime check | Complete |
| PDF | No button or implementation added | Source review | Intentionally out of scope |

## Verification

| Command / check | Result |
| --- | --- |
| `node --check src\\lung_xray_api\\web\\static\\demo.js` | PASS |
| `python -m pytest tests\\unit\\test_teacher_ui_contract.py tests\\integration\\test_demo_ui.py -q` | PASS — 6 passed, 1 existing Starlette/httpx deprecation warning |
| `python -m compileall src scripts tests` | PASS |
| `python -m pytest -q` | PASS — 242 passed, 1 existing Starlette/httpx deprecation warning |
| `python -m pyright src scripts tests` | PASS — 0 errors, 0 warnings, 0 informations |
| `python -m ruff check src scripts tests` | PASS — All checks passed |
| Edge headless, local `http://127.0.0.1:8008/demo` | PASS — header, About modal focus return, actual success state, reference gate/source, reset, mobile width; no console errors or failed requests |

Browser flow used the approved logo PNG only as a local client-side image fixture to exercise success
state and modal lifecycle. Its classification output is **not** clinical evidence and is not presented
as model-quality validation.

## Known limitations / manual approval

1. Production Knowledge Base contains no clinically reviewed disease reference item for the three
   predicted classes. This release correctly withholds clinical text and states that it is awaiting
   approval. Publishing such text requires a separately approved production KB update.
2. Confirm the spelling of `Vô Văn Nghĩa` with the project owner before release. It is rendered exactly
   as the approved workspace `team.json`, which flags `needs_name_spelling_confirmation: true`.
3. Automated runtime verification covered 1440 px and 390 px. A human visual/academic approval should
   still review the final desktop/tablet/mobile screenshots and Vietnamese copy before submission.
4. The repository worktree already contained prior TASK 01–04 and handoff changes. This task preserved
   them; the Git diff against `HEAD` is therefore broader than the Task 05 file list above.

## Remaining work

No PDF work was performed. The next task, only after approval, can address the separately requested PDF
or clinical-content publication workflow; neither is included in this task.
