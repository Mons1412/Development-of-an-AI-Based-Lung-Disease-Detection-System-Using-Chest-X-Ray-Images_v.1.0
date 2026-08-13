# Final UI/UX visualization refactor report

**Status: NOT_READY**

The implementation and automated behavior checks pass, but the required real-browser visual, responsive, focus, and screenshot gate could not run in this environment because no browser automation binding was available. This is not a Task 09 release package.

## Scope completed

- Replaced the old single-choice visualization behavior with a single shared multi-select state contract.
- Moved visualization preferences into a standalone partial after the source/patient row and before the analysis actions.
- Added simultaneous rendering for probability bars, column chart, donut chart, and data table.
- Rebuilt donut rendering using local SVG and DOM only; no CDN or chart dependency was added.
- Added versioned static asset routing and cache policy for nested CSS and ES-module imports.
- Removed the demo document references to compatibility/no-op wrapper entries. `js/app.js` is the only loaded application module.
- Added Node built-in behavior tests with a local fake DOM; no frontend framework, package, CDN, or external API was introduced.

## Architecture delivered

```text
result_view_preferences.html
  -> result-view-preferences-controller.js
     -> AppStore.selectedResultViews
        -> prediction-renderer.js
           -> bars / SVG column chart / SVG donut + legend / semantic table
```

`core/result-views.js` is the only result-view contract source. It owns:

- `RESULT_VIEW_IDS`: `probability-bars`, `column-chart`, `donut-chart`, `data-table`.
- `RESULT_VIEW_ORDER`, `DEFAULT_RESULT_VIEWS`, `RESULT_VIEW_LABELS` and `RESULT_VIEW_SECTION_IDS`.
- `normalizeResultViews()` and `resultViewsEqual()`.

The AppStore owns `selectedResultViews`. The checkbox-card controller owns user interaction, the at-least-one selection rule, and card selection styling. The renderer alone controls result-section visibility and result visual lifecycle. Changing a preference after a successful result invokes only renderer work; it does not upload, infer, or create history.

## State lifecycle

| Event | Prediction/result data | Result-view preference |
| --- | --- | --- |
| Initial page | Empty | Bars + column chart |
| Successful prediction | Current result renders all selected views | Preserved |
| Toggle after result | Current result re-renders only | Updated |
| New selected image | Old result/actions/visuals clear | Preserved |
| Invalid/failed analysis | No stale visual/action remains | Preserved |
| `Đặt lại` / remove current image | File, patient, result, assistant context clear | Reset to bars + column chart |

## Donut and data-display implementation

- The SVG creates exactly three `data-class` segments in the production class order: `normal`, `pneumonia`, `tuberculosis`.
- It uses the same `CLASS_COLORS` as bars, column chart, legend, and table indicator.
- Segment geometry handles zero, near-zero, and 100% values. Separators are represented by a small track gap only when more than one segment is non-zero.
- The center contains the API predicted class mapped to Vietnamese and its output probability; it does not infer a diagnosis.
- Desktop uses a `.donut-layout` grid (donut left, legend right); mobile stacks legend beneath the SVG.
- The semantic table is rendered with safe DOM text nodes, exactly three rows, and no raw JSON/debug panel.

## Cache and active asset contract

- Backend asset version: `20260728.1` in `lung_xray_api.web.assets`.
- Frontend module constant: `FRONTEND_BUILD = "20260728.1"` in `js/app.js`.
- `/demo` exposes `frontend-build` and `frontend-static-base` meta values and loads only `/static/v/20260728.1/js/app.js`.
- `/static/v/20260728.1/...` is mounted before the legacy static route, so relative CSS imports and ES-module imports inherit the versioned path.
- Development/test responses use `Cache-Control: no-store`; production versioned assets use `public, max-age=31536000, immutable`; legacy static paths revalidate.
- The application logs `[LungXrayUI] frontend build 20260728.1` at startup and warns if the rendered meta build differs from the module constant.

## Files changed for this refactor

See [FILE_CHANGELOG_UI_VISUALIZATION.csv](../../FILE_CHANGELOG_UI_VISUALIZATION.csv) for the authoritative scoped file list. The working tree was already dirty before this task; unrelated tracked and untracked changes were preserved.

## Verification evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Focused frontend contract tests | PASS | `15 passed` |
| Full Python suite | PASS | `310 passed, 1 Starlette deprecation warning` |
| Node behavior tests | PASS | `7 passed` |
| JavaScript syntax checks | PASS | `node --check` on all touched runtime modules |
| Python compile | PASS | `python -m compileall -q src tests scripts` |
| Local server smoke | PASS | `/demo` on port 8766 returned 200; versioned CSS/module returned 200 with `no-store` in development |
| Browser automation / screenshots | NOT RUN | Browser runtime reported no available browser binding; see release blocker |
| Ruff | NOT CLEAN (pre-existing) | One unrelated `F401` in `tests/conftest.py:10`; no new lint finding remains in refactor code |
| Pyright | NOT CLEAN (pre-existing) | Eight unrelated existing errors in PDF/model/schema/test typing paths |
| `git diff --check` | NOT CLEAN (pre-existing) | Existing trailing whitespace in `README.md` and `../SUBMISSION_CHECKLIST.md`; no scoped formatting fix applied |

Commands run:

```powershell
node --check src/lung_xray_api/web/static/js/core/result-views.js
node --check src/lung_xray_api/web/static/js/core/app-store.js
node --check src/lung_xray_api/web/static/js/app.js
node --check src/lung_xray_api/web/static/js/prediction/prediction-controller.js
node --check src/lung_xray_api/web/static/js/prediction/prediction-renderer.js
node --check src/lung_xray_api/web/static/js/prediction/result-view-preferences-controller.js
node --check src/lung_xray_api/web/static/js/visualization/result-chart.js
node --check src/lung_xray_api/web/static/js/history/history-renderer.js
node --experimental-default-type=module --test tests/frontend/result-views.test.mjs tests/frontend/prediction-renderer.test.mjs tests/frontend/result-view-preferences-controller.test.mjs
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m compileall -q src tests scripts
.\.venv\Scripts\python.exe -m ruff check --no-cache src tests scripts
.\.venv\Scripts\python.exe -m pyright src tests scripts
curl.exe --max-time 5 -sS -D ... http://127.0.0.1:8766/demo
```

## Constraints verified in source scope

- No MobileNetV2, preprocessing, class order, probability algorithm, history/patient metadata contract, offline assistant, or PDF workflow was changed.
- No external AI, API key, CDN, package, framework, database change, or direct frontend retrieval was added.
- No unsafe `innerHTML` was added for results; chart labels, legend, table cells, and runtime messages use safe DOM text assignment.
- The current assistant remains offline-only and continues to consume the shared AppStore prediction state.

## Remaining release blockers

1. Real-browser validation is not evidenced: the available browser runtime returned an empty browser list. Execute the manual checklist with screenshots at all required viewports.
2. Confirm live Network behavior in a browser: post-result toggles must produce no analysis request/history write, and a new image must clear only current result data while preserving preferences.
3. Resolve or explicitly accept the unrelated Ruff/Pyright baseline findings before any broader release quality gate.
4. Review the provided ZIP in a clean staging copy before applying. It is a scoped patch artifact, not a stable release replacement.

## Screenshots still required

- Initial desktop workspace.
- Desktop success with all four views visible.
- Desktop donut/legend close view.
- Mobile 430 px and 360 px success state with assistant launcher visible but not covering actions.
- Keyboard focus on a result-view checkbox card and the last-selection validation message.
- Reset state after a prior successful analysis.
