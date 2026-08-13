# GEMINI ASSISTANT STABILITY REPORT

**Ngày xác minh:** 2026-07-28  
**Phạm vi:** ổn định trợ lý Gemini online và fallback offline; không đóng gói Task 09  
**Trạng thái:** `READY_FOR_USER_ASSISTANT_TESTING`

## 1. Mục tiêu và giới hạn

Thay đổi này ổn định luồng trợ lý thông tin X-quang phổi ở chế độ hybrid:

- Gemini được dùng khi cấu hình hợp lệ và request vượt qua các cổng privacy/safety.
- Knowledge Base production và prediction context đã chuẩn hóa được resolve trước khi gọi provider.
- Offline assistant tiếp tục là fallback kiểm soát được khi online bị tắt, lỗi hoặc circuit đang mở.
- Không gửi ảnh, tên/mã bệnh nhân, đường dẫn file hoặc toàn bộ record phân tích tới Gemini.
- Không thay đổi model MobileNetV2, preprocessing, SQLite history, PDF hoặc luồng prediction.
- Không tuyên bố chẩn đoán hay clinical validation.

## 2. Root cause đã xác nhận

1. Runtime trước đây coi việc provider object tồn tại là bằng chứng “online”, dù chưa probe thành công.
2. Hybrid service tạo câu trả lời offline hoàn chỉnh trước khi gọi Gemini, làm sai thứ tự resolve và khiến online phụ thuộc vào text đã render.
3. Intent router không ưu tiên prediction context cho các câu như “ảnh tôi vừa upload ấy”, nên có thể rơi vào `upload_help`.
4. Provider thiếu taxonomy lỗi, retry có giới hạn, probe, circuit breaker và log an toàn theo request.
5. Frontend giữ nhiều biến prediction không đồng nhất, chưa chống response cũ ghi đè response mới và badge chưa phản ánh đúng trạng thái xác minh.
6. Bộ lọc output online dùng marker quá rộng, có thể từ chối cả câu disclaimer phủ định an toàn.
7. PowerShell có thể làm sai Unicode nếu truyền trực tiếp tiếng Việt qua stdin theo code page mặc định; live smoke cuối dùng ASCII source với Unicode escape.

## 3. Luồng sau khi ổn định

```text
AssistantQuery
  -> validate stage + prediction context
  -> safety/privacy guard
  -> resolve intent
  -> retrieve production Knowledge Base
  -> build canonical structured request
  -> circuit/provider availability check
  -> Gemini generate (retry tối đa 1 lần cho lỗi transient)
  -> validate online output
  -> online response
     hoặc render offline từ cùng AssistantResolution khi fallback
```

Không có bước render offline answer trước Gemini. Online và offline dùng cùng intent, prediction context và source mapping đã resolve.

## 4. Kiến trúc và contract đã triển khai

### 4.1 Configuration

- `GEMINI_API_KEY` được nạp vào `SecretStr | None`.
- Provider chuẩn hóa qua `AI_PRIMARY_PROVIDER=gemini`.
- `ONLINE_AI_TIMEOUT_SECONDS` mặc định 30 giây.
- `ONLINE_AI_TEMPERATURE` là tùy chọn; giá trị trống không được gửi tới provider.
- `AI_OFFLINE_FALLBACK_ENABLED` điều khiển fallback.
- `safe_online_ai_summary()` chỉ công bố boolean `key_configured`, không trả key.
- `.env.example` và PowerShell setup script không chứa key thật.

Safe configuration summary tại thời điểm kiểm tra:

```text
online_enabled=True
provider=gemini
key_configured=True
model=gemini-3.5-flash
timeout_seconds=30.0
offline_fallback_enabled=True
```

### 4.2 Provider lifecycle và reliability

- Một Gemini client được tạo trong FastAPI lifespan và đóng khi shutdown.
- Provider contract gồm `generate()`, `probe()` và `close()`.
- Error categories: authentication, permission, invalid model, quota/rate limit, timeout, service unavailable, network và invalid response.
- Chỉ retry tối đa một lần với lỗi transient; không retry lỗi 400/401/403/404.
- Circuit breaker mở sau chuỗi lỗi được cấu hình và có cooldown.
- Probe chạy background, có TTL cache; status endpoint không chặn để chờ network và không gọi provider ở mọi lần poll.
- Log online chỉ gồm request ID, provider, model, attempt, latency, category và fallback state; không log API key hoặc raw user message.

### 4.3 Runtime state

State machine công khai:

- `disabled`
- `misconfigured`
- `configured_unverified`
- `online_verified`
- `degraded_offline`

Status response giữ các field tương thích cũ (`online_available`, `active_mode`) nhưng chỉ báo online sau khi probe/generate thành công. Response cũng có `configured`, `verified`, timestamps, failure count, error category, provider và model.

### 4.4 Context, privacy và safety

Prediction context gửi cho assistant chỉ có:

- `predicted_label`
- `probabilities`
- `model_version`

`processing_time_ms`, ảnh, filename, patient/case metadata và internal path không thuộc assistant contract. Pydantic dùng `extra="forbid"` để từ chối field ngoài contract.

Raw free-text không được chuyển thẳng sang Gemini. Provider nhận canonical question theo intent cùng approved Knowledge Base chunks, source IDs, prediction context và safety instructions. Câu chứa dấu hiệu patient identity được xử lý offline với `privacy_guard`.

Safety refusal vẫn xảy ra trước provider đối với diagnosis, medication, dosage và treatment-change requests. Output online có dấu hiệu khẳng định chẩn đoán hoặc hướng dẫn thuốc bị loại và fallback offline. Disclaimer phủ định hợp lệ không còn bị false positive.

### 4.5 Intent hiện tại

Các biến thể tiếng Việt sau được resolve thành `explain_current_prediction` khi stage là `after_analysis` và prediction context hợp lệ:

- “ảnh tôi vừa upload ấy”
- “kết quả ảnh vừa phân tích”
- “giải thích kết quả hiện tại”
- các spelling/normalization variation tương đương trong test.

Renderer offline dùng wording phi chẩn đoán, nêu predicted class và đủ ba xác suất đầu ra.

### 4.6 Frontend

- Source of truth là `currentPrediction`, chỉ chứa ba field assistant được phép dùng.
- `currentPrediction` được set sau prediction thành công và xóa khi chọn ảnh mới, prediction bắt đầu/lỗi, reset hoặc quay về initial state.
- Assistant request dùng `AbortController`, request sequence ID và stale-response guard.
- Send button bị disable trong lúc request đang chạy.
- Badge phân biệt cấu hình chưa xác minh, online đã xác minh, degraded/misconfigured và offline.
- UI không tự thực hiện retrieval và chỉ gọi assistant API.
- Assistant API responses dùng `Cache-Control: no-store`.

## 5. Files chính đã thay đổi

Backend/configuration:

- `.env.example`
- `README.md`
- `PRIVACY_NOTES.md`
- `scripts/SET_GEMINI_KEY.ps1`
- `scripts/test_gemini_connection.py`
- `src/lung_xray_api/core/config.py`
- `src/lung_xray_api/core/lifespan.py`
- `src/lung_xray_api/main.py`
- `src/lung_xray_api/schemas/assistant.py`
- `src/lung_xray_api/assistant/gemini_prompt.py`
- `src/lung_xray_api/assistant/gemini_provider.py`
- `src/lung_xray_api/assistant/hybrid_service.py`
- `src/lung_xray_api/assistant/intent_router.py`
- `src/lung_xray_api/assistant/online_provider.py`
- `src/lung_xray_api/assistant/response_renderer.py`
- `src/lung_xray_api/assistant/service.py`

Frontend:

- `src/lung_xray_api/web/assets.py`
- `src/lung_xray_api/web/static/css/assistant.css`
- `src/lung_xray_api/web/static/js/app.js`
- `src/lung_xray_api/web/static/js/core/app-store.js`
- `src/lung_xray_api/web/static/js/assistant/assistant-controller.js`
- `src/lung_xray_api/web/static/js/prediction/prediction-controller.js`
- `src/lung_xray_api/web/static/js/prediction/result-view-preferences-controller.js`

Tests:

- `tests/conftest.py`
- `tests/frontend/assistant-controller.test.mjs`
- `tests/frontend/result-view-preferences-controller.test.mjs`
- `tests/integration/test_assistant_api.py`
- `tests/integration/test_assistant_api_hardening.py`
- `tests/unit/test_assistant_service.py`
- `tests/unit/test_config_dotenv.py`
- `tests/unit/test_gemini_provider.py`
- `tests/unit/test_hybrid_assistant_service.py`
- `tests/unit/test_online_assistant_runtime.py`
- các type-only test adjustments cần thiết để full Pyright pass.

## 6. Verification evidence

| Command/check | Result |
|---|---|
| Targeted assistant/API pytest | PASS — 60 tests |
| `.\.venv\Scripts\python.exe -m pytest -q` | PASS — 355 tests, 1 deprecation warning |
| `.\.venv\Scripts\python.exe -m compileall -q src tests scripts` | PASS |
| `.\.venv\Scripts\python.exe -m ruff check src tests scripts` | PASS |
| `.\.venv\Scripts\pyright.exe` | PASS — 0 errors, 0 warnings |
| `node --test tests/frontend/*.test.mjs` | PASS — 11 tests |
| `node --check` trên toàn bộ `src/.../static/js` và `tests/frontend` | PASS — 33 modules |
| `.\.venv\Scripts\python.exe -m pip check` | PASS — no broken requirements |
| Secret-shaped pattern scan, loại `.env`, `.venv`, `.git`, artifacts và runtime data | PASS — no matches |
| Live FastAPI application smoke với Gemini | PASS |
| `git diff --check` | FAIL — trailing spaces có sẵn trong Markdown, chi tiết ở mục 8 |

Execution notes:

- Live smoke attempt đầu tiên dừng ở `SyntaxError` do PowerShell làm biến đổi quoting của `python -c`; chưa chạy application/network. Lệnh được đổi sang ASCII stdin với Unicode escape và lần chạy chính thức PASS.
- JavaScript syntax attempt đầu tiên trỏ nhầm tên file `result-preference-controller.js` nên báo `MODULE_NOT_FOUND`; sau khi lấy danh sách file thật từ repository, kiểm tra lại toàn bộ 33 module PASS.

Pytest warning duy nhất:

- `StarletteDeprecationWarning`: `fastapi.testclient` đang dùng integration `httpx` cũ; không làm test fail và không được xử lý bằng dependency upgrade ngoài scope.

## 7. Live application smoke

Smoke dùng `create_app(load_model=False)` để kiểm tra riêng assistant lifespan/API, không tải hay thay đổi model. Request dùng prediction context giả lập hợp lệ, không có ảnh hoặc patient identity.

Kết quả:

```text
HTTP status: 200
before state: configured_unverified
response mode: online
response intent: explain_current_prediction
fallback used: false
after state: online_verified
request_id present: true
source count: 1
```

Gemini trả HTTP 200. Log không hiển thị API key hoặc raw question.

Default automated tests ép `ONLINE_AI_ENABLED=false` và key rỗng trong fixture để không vô tình gọi network. Live test là bước opt-in riêng.

## 8. Rủi ro và phần chưa xác minh

1. Chưa thực hiện manual browser acceptance trên tất cả desktop/tablet/mobile; cần người dùng kiểm tra badge, typing/loading, reset và nhiều lượt hội thoại thực tế.
2. Background probe và request chính có thể cùng được schedule khi ứng dụng vừa mở; provider lock bảo vệ client nhưng lần đầu có thể phát sinh hai request nối tiếp.
3. UI hiện chỉ follow-up status một lần sau trạng thái `configured_unverified`; nếu probe chậm hơn khoảng đó, badge sẽ cập nhật ở request assistant thành công tiếp theo.
4. Shutdown có thể chờ background probe kết thúc trong giới hạn provider timeout.
5. `PredictionContext` cố ý từ chối `processing_time_ms`; client assistant cũ gửi field này sẽ nhận HTTP 422 và cần theo contract mới.
6. `git diff --check` còn báo trailing whitespace tại:
   - `README.md` dòng 3–6 và 64;
   - `../SUBMISSION_CHECKLIST.md` dòng 4.
   Đây là hygiene issue trong worktree nhiều thay đổi có sẵn, không ảnh hưởng runtime assistant và không được tự sửa ngoài phạm vi task.
7. Chưa đóng gói hoặc kiểm thử clean-machine/portable release; Task 09 vẫn bị khóa.

## 9. Rollback

Rollback an toàn là hoàn nguyên riêng nhóm file Gemini/hybrid/frontend assistant nêu ở mục 5 về revision đã review trước đó. Không xóa `.env`, SQLite history, thumbnails, model artifact hoặc Knowledge Base. Không dùng `git reset --hard` trên worktree hiện tại.

## 10. Kết luận

Các lỗi định tuyến, trạng thái online giả, thứ tự hybrid, retry/circuit, privacy boundary, output safety false positive và stale frontend request đã có sửa đổi cùng regression evidence. Live application smoke xác nhận Gemini hoạt động qua endpoint thật và state chuyển sang `online_verified`.

**Final status: `READY_FOR_USER_ASSISTANT_TESTING`**
