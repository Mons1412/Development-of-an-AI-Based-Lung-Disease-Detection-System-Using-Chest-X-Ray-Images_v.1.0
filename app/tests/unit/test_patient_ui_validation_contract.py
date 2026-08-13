from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATIC = PROJECT_ROOT / "src/lung_xray_api/web/static/js"
TEMPLATES = PROJECT_ROOT / "src/lung_xray_api/web/templates/partials"


def test_patient_ui_blocks_invalid_codes_before_submit() -> None:
    validation = (STATIC / "patient/patient-validation.js").read_text(encoding="utf-8")
    controller = (STATIC / "patient/patient-controller.js").read_text(encoding="utf-8")
    prediction = (STATIC / "prediction/prediction-controller.js").read_text(encoding="utf-8")

    assert "validatePatientCode" in validation
    assert "Mã ca chỉ gồm chữ, số và dấu gạch ngang" in validation
    assert "validatePatientDraft" in controller
    assert "applyServerErrors" in controller
    assert "patientController.applyServerErrors" in prediction


def test_patient_form_explains_optional_code_contract() -> None:
    template = (TEMPLATES / "patient_form.html").read_text(encoding="utf-8")

    assert "không nhập tên bệnh nhân vào ô này" in template.casefold()
    assert 'id="patient-confirmation-error"' in template
    assert 'aria-invalid="false"' in template
