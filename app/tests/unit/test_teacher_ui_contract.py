"""Static checks for teacher-facing UI requirements in the modular frontend."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_ROOT = PROJECT_ROOT / "src/lung_xray_api/web/templates"
STATIC = PROJECT_ROOT / "src/lung_xray_api/web/static"


def _templates_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in TEMPLATE_ROOT.rglob("*.html"))


def _styles_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in (STATIC / "css").rglob("*.css"))


def _scripts_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in (STATIC / "js").rglob("*.js"))


def test_reference_modal_keeps_the_clinical_review_gate_visible() -> None:
    templates = _templates_text()

    assert 'id="reference-info-button"' in templates
    assert 'id="reference-info-modal"' in templates
    assert "Nội dung chuyên môn đang chờ duyệt" in templates
    assert "MODEL_ARTIFACT_1_1_0" in templates
    assert "hướng dẫn dùng thuốc, liều lượng hoặc thay đổi điều trị" in templates


def test_teacher_ui_uses_accessible_native_dialog_controls() -> None:
    templates = _templates_text()
    scripts = _scripts_text()

    assert "<dialog" in templates
    assert 'aria-haspopup="dialog"' in templates
    assert "dialog.showModal()" in scripts
    assert "closeModal(dialog)" in scripts
    assert "focusOrigins" in scripts
    assert "focusOrigin.focus()" in scripts


def test_new_image_and_reset_clear_the_active_prediction_and_assistant_context() -> None:
    scripts = _scripts_text()

    assert "clearPrediction()" in scripts
    assert "store.reset()" in scripts
    assert "EVENTS.ANALYSIS_RESET" in scripts
    assert "analysisId: null" in scripts


def test_teacher_ui_has_responsive_focus_and_modal_styles() -> None:
    styles = _styles_text()

    assert ".teacher-modal" in styles
    assert "dialog::backdrop" in styles
    assert ":focus-visible" in styles
    assert "@media (max-width: 620px)" in styles
