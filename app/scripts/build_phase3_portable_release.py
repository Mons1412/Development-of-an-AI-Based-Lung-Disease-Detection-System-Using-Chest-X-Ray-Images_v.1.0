"""Build a clean Windows portable handoff without copying local secrets or data."""

from __future__ import annotations

import hashlib
from importlib import metadata
from pathlib import Path
import re
import shutil
import site
import subprocess
import sys
import zipfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASE_PORTABLE = (
    PROJECT_ROOT.parent
    / "dist"
    / "Lung_Xray_FastAPI_Portable_Windows_x64_v1.0.0_model1.1.0_20260723"
)
RELEASE_ROOT = PROJECT_ROOT / "release"
PACKAGE_NAME = "Lung_Xray_FastAPI_Portable_Windows_x64_v1.2.0_model1.1.0_20260728"

RUNTIME_DISTRIBUTIONS_TO_OVERLAY = (
    "cffi",
    "cryptography",
    "distro",
    "google-auth",
    "google-genai",
    "pyasn1",
    "pyasn1-modules",
    "pycparser",
    "reportlab",
    "sniffio",
    "tenacity",
)

APP_DIRECTORIES = (
    "artifacts",
    "docs",
    "handoff",
    "scripts",
    "src",
    "tests",
)
APP_FILES = (
    ".env.example",
    ".gitignore",
    "DEMO_UI_INTEGRATION.md",
    "PRIVACY_NOTES.md",
    "README.md",
    "README_FIRST.md",
    "SECURITY_NOTICE.md",
    "pyproject.toml",
    "pyrightconfig.json",
    "requirements-lock.txt",
)
EXCLUDED_NAMES = {
    ".env",
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}
SECRET_PATTERNS = (
    re.compile(rb"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(rb"AQ\.[0-9A-Za-z_-]{20,}"),
)


def _ignore_generated(_directory: str, names: list[str]) -> set[str]:
    ignored = {name for name in names if name in EXCLUDED_NAMES}
    ignored.update(name for name in names if name.endswith((".pyc", ".pyo")))
    return ignored


def _copy_application(target_app: Path) -> None:
    for directory_name in APP_DIRECTORIES:
        source = PROJECT_ROOT / directory_name
        if source.is_dir():
            shutil.copytree(
                source,
                target_app / directory_name,
                ignore=_ignore_generated,
            )

    for file_name in APP_FILES:
        source = PROJECT_ROOT / file_name
        if source.is_file():
            destination = target_app / file_name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    production_kb = (
        PROJECT_ROOT
        / "knowledge_base"
        / "compiled"
        / "knowledge_base.production.vi.json"
    )
    destination_kb = (
        target_app
        / "knowledge_base"
        / "compiled"
        / "knowledge_base.production.vi.json"
    )
    destination_kb.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(production_kb, destination_kb)

    governance_changelog = PROJECT_ROOT / "knowledge_base" / "governance" / "changelog.md"
    if governance_changelog.is_file():
        destination = target_app / "knowledge_base" / "governance" / "changelog.md"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(governance_changelog, destination)

    validation_source = PROJECT_ROOT / "PHASE3_IMPLEMENTATION_WORKSPACE" / "12_VALIDATION"
    validation_target = target_app / "PHASE3_IMPLEMENTATION_WORKSPACE" / "12_VALIDATION"
    for source in validation_source.glob("*.md"):
        validation_target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, validation_target / source.name)


def _overlay_runtime_distributions(target_runtime: Path) -> None:
    source_site_packages = next(
        path
        for path in (Path(value).resolve() for value in site.getsitepackages())
        if path.name.casefold() == "site-packages"
    )
    target_site_packages = target_runtime / "Lib" / "site-packages"

    for distribution_name in RUNTIME_DISTRIBUTIONS_TO_OVERLAY:
        distribution = metadata.distribution(distribution_name)
        files = distribution.files
        if files is None:
            raise RuntimeError(f"Distribution has no file manifest: {distribution_name}")

        copied = 0
        for distribution_file in files:
            source = Path(distribution.locate_file(distribution_file)).resolve()
            if not source.is_file():
                continue
            try:
                relative = source.relative_to(source_site_packages)
            except ValueError:
                continue
            destination = target_site_packages / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            copied += 1
        if copied == 0:
            raise RuntimeError(f"No site-packages files copied for: {distribution_name}")

    for cache_directory in target_runtime.rglob("__pycache__"):
        shutil.rmtree(cache_directory)
    for bytecode_file in target_runtime.rglob("*.pyc"):
        bytecode_file.unlink()


def _write_launchers(package_root: Path) -> None:
    (package_root / "START_API.cmd").write_text(
        r"""@echo off
setlocal
set "PACKAGE_ROOT=%~dp0"
set "APP_ROOT=%PACKAGE_ROOT%app"
set "PYTHON_EXE=%PACKAGE_ROOT%runtime\python.exe"

if not exist "%PYTHON_EXE%" (
  echo [ERROR] Missing portable Python. Extract the complete ZIP first.
  pause
  exit /b 1
)

if not exist "%APP_ROOT%\artifacts\lung_classifier\1.1.0\lung_classifier_v1.keras" (
  echo [ERROR] Missing model artifact. Extract the complete ZIP first.
  pause
  exit /b 1
)

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONPATH=%APP_ROOT%\src"
set "ARTIFACT_DIR=%APP_ROOT%\artifacts\lung_classifier\1.1.0"
set "HOST=127.0.0.1"
set "PORT=8000"
if not "%~1"=="" set "PORT=%~1"

cd /d "%APP_ROOT%"
echo Demo UI : http://127.0.0.1:%PORT%/demo
echo API docs: http://127.0.0.1:%PORT%/docs
echo Stop     : Press Ctrl+C
echo.
"%PYTHON_EXE%" -m lung_xray_api
exit /b %ERRORLEVEL%
""",
        encoding="utf-8",
    )
    (package_root / "SET_GEMINI_KEY.cmd").write_text(
        r"""@echo off
setlocal
set "PACKAGE_ROOT=%~dp0"
set "APP_ROOT=%PACKAGE_ROOT%app"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%APP_ROOT%\scripts\SET_GEMINI_KEY.ps1" -ProjectRoot "%APP_ROOT%"
if errorlevel 1 (
  echo [ERROR] Gemini key setup failed.
  pause
  exit /b 1
)
echo.
echo Run TEST_GEMINI_CONNECTION.cmd to verify the online provider.
pause
""",
        encoding="utf-8",
    )
    (package_root / "TEST_GEMINI_CONNECTION.cmd").write_text(
        r"""@echo off
setlocal
set "PACKAGE_ROOT=%~dp0"
set "APP_ROOT=%PACKAGE_ROOT%app"
set "PYTHON_EXE=%PACKAGE_ROOT%runtime\python.exe"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONPATH=%APP_ROOT%\src"
cd /d "%APP_ROOT%"
"%PYTHON_EXE%" "%APP_ROOT%\scripts\test_gemini_connection.py"
pause
exit /b %ERRORLEVEL%
""",
        encoding="utf-8",
    )
    (package_root / "VERIFY_PACKAGE.cmd").write_text(
        r"""@echo off
setlocal
set "PACKAGE_ROOT=%~dp0"
set "APP_ROOT=%PACKAGE_ROOT%app"
set "PYTHON_EXE=%PACKAGE_ROOT%runtime\python.exe"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONPATH=%APP_ROOT%\src"
set "ARTIFACT_DIR=%APP_ROOT%\artifacts\lung_classifier\1.1.0"
set "ONLINE_AI_ENABLED=false"
cd /d "%APP_ROOT%"

echo [1/5] Portable Python and required imports...
"%PYTHON_EXE%" -c "import google.genai, reportlab, tensorflow; print('runtime_imports=PASS')"
if errorlevel 1 goto :failed
echo [2/5] Model artifact checksums...
"%PYTHON_EXE%" "%APP_ROOT%\scripts\verify_artifacts.py"
if errorlevel 1 goto :failed
echo [3/5] Model load and warm-up...
"%PYTHON_EXE%" "%APP_ROOT%\scripts\verify_portable_runtime.py"
if errorlevel 1 goto :failed
echo [4/5] FastAPI health routes...
"%PYTHON_EXE%" "%APP_ROOT%\scripts\smoke_api.py"
if errorlevel 1 goto :failed
echo [5/5] Offline test suite...
"%PYTHON_EXE%" -m pytest -q
if errorlevel 1 goto :failed
echo [PASS] Portable package verification passed.
pause
exit /b 0

:failed
echo [FAIL] Package verification failed.
pause
exit /b 1
""",
        encoding="utf-8",
    )


def _git_revision() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _write_release_docs(package_root: Path) -> None:
    (package_root / "README_FIRST.md").write_text(
        """# Lung X-ray AI Portable Windows x64 v1.2.0

Gói này chứa Python 3.12 portable, dependencies, source FastAPI hiện tại,
model 1.1.0 và production Knowledge Base. Không cần cài Python hoặc tạo `.venv`.

## Chạy ngay

1. Giải nén toàn bộ ZIP.
2. Chạy `START_API.cmd`.
3. Mở `http://127.0.0.1:8000/demo`.
4. Dừng bằng `Ctrl+C`.

Ứng dụng hoạt động offline ngay cả khi chưa cấu hình Gemini.

## Bật Gemini online an toàn

API key thật không nằm trong ZIP. Trên máy đích:

1. Chạy `SET_GEMINI_KEY.cmd`.
2. Dán key khi PowerShell hỏi; ký tự không hiển thị.
3. Chạy `TEST_GEMINI_CONNECTION.cmd`.
4. Khởi động lại bằng `START_API.cmd`.

Key chỉ được lưu ở `app/.env` trên máy đích. Không gửi lại ZIP sau khi file này
đã được tạo.

## Chạy đúng dạng Python module

`START_API.cmd` thực thi chính xác:

```text
runtime\\python.exe -m lung_xray_api
```

Launcher tự đặt `PYTHONPATH`, model path, UTF-8, host và port. Nếu cổng 8000 bận:

```text
START_API.cmd 8080
```

## Tự kiểm tra

Chạy `VERIFY_PACKAGE.cmd`. Lần warm-up TensorFlow đầu tiên có thể mất vài phút.

## Dữ liệu và giới hạn

- Không kèm `.env`, API key, lịch sử SQLite, thumbnail, ảnh upload hoặc PDF tạm.
- Lịch sử mới được tạo cục bộ trong `app/var/data/`.
- Ảnh gốc không được lưu mặc định.
- Kết quả chỉ phục vụ mục đích học thuật, không thay thế chẩn đoán của bác sĩ.
- Gemini cần Internet; offline assistant và prediction vẫn hoạt động khi mất mạng.
""",
        encoding="utf-8",
    )
    (package_root / "PACKAGE_INFO.txt").write_text(
        "\n".join(
            (
                "Package: Lung X-ray FastAPI Portable",
                "Package version: 1.2.0",
                "Model version: 1.1.0",
                "Knowledge Base: production only",
                "Python: 3.12 Windows x64 portable",
                "Default host: 127.0.0.1",
                "Default port: 8000",
                "Gemini API key included: No",
                "Offline startup requires Internet: No",
                "Gemini online mode requires Internet: Yes",
                f"Source commit: {_git_revision()}",
                "Source state: current working-tree snapshot",
                "",
            )
        ),
        encoding="utf-8",
    )
    shutil.copy2(
        PROJECT_ROOT / "handoff" / "portable_windows" / "THIRD_PARTY_NOTICES.md",
        package_root / "THIRD_PARTY_NOTICES.md",
    )


def _run_packaged_python(package_root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = {
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": str(package_root / "app" / "src"),
        "ARTIFACT_DIR": str(
            package_root / "app" / "artifacts" / "lung_classifier" / "1.1.0"
        ),
        "ONLINE_AI_ENABLED": "false",
    }
    import os

    return subprocess.run(
        [str(package_root / "runtime" / "python.exe"), *arguments],
        cwd=package_root / "app",
        env={**os.environ, **environment},
        check=True,
        capture_output=True,
        text=True,
    )


def _verify_staging(package_root: Path) -> None:
    import_result = _run_packaged_python(
        package_root,
        "-c",
        (
            "import google.genai, reportlab, tensorflow; "
            "from lung_xray_api.core.config import load_settings; "
            "s=load_settings(); "
            "assert not s.online_ai_enabled; "
            "assert s.gemini_api_key is None; "
            "print('portable_import_and_secret_gate=PASS')"
        ),
    )
    print(import_result.stdout.strip())

    artifact_result = _run_packaged_python(
        package_root,
        str(package_root / "app" / "scripts" / "verify_artifacts.py"),
    )
    print(artifact_result.stdout.strip())

    for path in package_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {
            ".dll",
            ".exe",
            ".keras",
            ".pyd",
            ".pyc",
            ".png",
            ".zip",
        }:
            continue
        content = path.read_bytes()
        if any(pattern.search(content) for pattern in SECRET_PATTERNS):
            raise RuntimeError(f"Secret-shaped content found in package: {path}")


def _write_runtime_packages(package_root: Path) -> None:
    result = _run_packaged_python(package_root, "-m", "pip", "freeze", "--all")
    (package_root / "PORTABLE_RUNTIME_PACKAGES.txt").write_text(
        result.stdout,
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _write_manifest(package_root: Path) -> None:
    manifest_path = package_root / "PACKAGE_MANIFEST.txt"
    lines = ["SHA256|BYTES|RELATIVE_PATH"]
    files = sorted(
        path
        for path in package_root.rglob("*")
        if path.is_file() and path != manifest_path
    )
    for path in files:
        relative = path.relative_to(package_root).as_posix()
        lines.append(f"{_sha256(path)}|{path.stat().st_size}|{relative}")
    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_zip(package_root: Path) -> Path:
    zip_path = RELEASE_ROOT / f"{PACKAGE_NAME}.zip"
    if zip_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing archive: {zip_path}")

    with zipfile.ZipFile(
        zip_path,
        mode="x",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6,
        allowZip64=True,
    ) as archive:
        for path in sorted(package_root.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(RELEASE_ROOT))

    checksum = _sha256(zip_path)
    checksum_path = zip_path.with_suffix(".zip.sha256")
    checksum_path.write_text(f"{checksum}  {zip_path.name}\n", encoding="ascii")
    return zip_path


def main() -> int:
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("Build must run with the project Python 3.12 environment")
    if not BASE_PORTABLE.is_dir():
        raise FileNotFoundError(f"Base portable package not found: {BASE_PORTABLE}")

    package_root = RELEASE_ROOT / PACKAGE_NAME
    if package_root.exists():
        raise FileExistsError(f"Refusing to overwrite existing release: {package_root}")

    RELEASE_ROOT.mkdir(parents=True, exist_ok=True)
    print(f"[1/8] Copying stable portable runtime to {package_root}")
    shutil.copytree(BASE_PORTABLE / "runtime", package_root / "runtime")
    print("[2/8] Overlaying current Gemini/PDF runtime dependencies")
    _overlay_runtime_distributions(package_root / "runtime")
    print("[3/8] Copying current source, model, production KB, docs, and tests")
    _copy_application(package_root / "app")
    print("[4/8] Writing portable launchers and handoff documentation")
    _write_launchers(package_root)
    _write_release_docs(package_root)
    print("[5/8] Verifying imports, model checksums, and secret exclusion")
    _verify_staging(package_root)
    print("[6/8] Recording exact portable distributions")
    _write_runtime_packages(package_root)
    print("[7/8] Generating per-file SHA256 manifest")
    _write_manifest(package_root)
    print("[8/8] Creating ZIP and archive checksum")
    zip_path = _write_zip(package_root)
    print(f"release_directory={package_root}")
    print(f"release_zip={zip_path}")
    print(f"release_bytes={zip_path.stat().st_size}")
    print(f"release_sha256={_sha256(zip_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
