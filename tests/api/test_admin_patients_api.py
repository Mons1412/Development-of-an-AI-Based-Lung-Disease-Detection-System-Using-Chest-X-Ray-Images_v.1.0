import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from lung_xray_api.api.v1.admin_patients import router
from lung_xray_api.api.dependencies.auth import get_current_user
from lung_xray_api.infrastructure.persistence.database import get_db
from lung_xray_api.infrastructure.persistence.orm import UserModel, PatientProfileModel, MedicalHistoryModel, PatientProfileHistoryModel
from lung_xray_api.infrastructure.persistence.orm import AIModel, AnalysisModel, PredictionModel, ReportModel, MedicalAdviceModel
from lung_xray_api.infrastructure.persistence.orm.base import Base


@pytest.fixture
def patient_app():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        users = []
        for number, role in enumerate(['ADMIN', 'USER', 'USER'], 1):
            user = UserModel(username=f'account{number}', email=f'person{number}@example.com',
                             phone=f'090000000{number}', password_hash='unchanged', role=role)
            user.patient_profile = PatientProfileModel(patient_code=f'PX{number}',
                full_name=['Administrator', 'Nguyễn Văn An', 'Tran Binh'][number-1],
                address=['Private admin', '12 Le Loi, Quan 1', '45 Nguyen Hue'][number-1],
                phone=user.phone)
            db.add(user); users.append(user)
        db.commit()
        patient_id = users[1].patient_profile.id
        db.add(MedicalHistoryModel(patient_id=patient_id))
        db.add(PatientProfileHistoryModel(patient_id=patient_id))
        db.commit()
        app = FastAPI(); app.include_router(router, prefix='/api/v1/admin')
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: users[0]
        with TestClient(app) as client:
            yield client, db, app, users
    engine.dispose()


@pytest.mark.parametrize('query', ['Văn An', '0900000002', '+84 900 000 002', 'Le Loi'])
def test_search_by_name_phone_address(patient_app, query):
    client, _, _, _ = patient_app
    response = client.get('/api/v1/admin/patients', params={'q':query})
    assert response.status_code == 200
    data = response.json()
    assert data['total'] == 1 and data['items'][0]['patient_code'] == 'PX2'
    assert 'password_hash' not in data['items'][0]


def test_pagination_and_literal_wildcard(patient_app):
    client, _, _, _ = patient_app
    first = client.get('/api/v1/admin/patients', params={'limit':1}).json()
    second = client.get('/api/v1/admin/patients', params={'limit':1,'page':2}).json()
    assert first['total'] == 2
    assert first['items'][0]['user_id'] != second['items'][0]['user_id']
    assert client.get('/api/v1/admin/patients', params={'q':'%'}).json()['total'] == 0


def payload(**changes):
    return dict(full_name='Updated Patient', phone='+84 900 123 456', email='updated@example.com',
                address='New address', date_of_birth='2000-01-01', sex='MALE', is_active=False, **changes)


def test_update_synchronizes_account_and_profile(patient_app):
    client, db, _, users = patient_app
    response = client.put(f'/api/v1/admin/patients/{users[1].id}', json=payload())
    assert response.status_code == 200
    db.refresh(users[1])
    assert users[1].phone == users[1].patient_profile.phone == '0900123456'
    assert users[1].email == 'updated@example.com'
    assert users[1].patient_profile.birth_year == 2000
    assert users[1].password_hash == 'unchanged'
    assert users[1].is_active is False


def test_duplicate_phone_rolls_back_profile_changes(patient_app):
    client, db, _, users = patient_app
    data = payload(); data['phone'] = users[2].phone
    assert client.put(f'/api/v1/admin/patients/{users[1].id}', json=data).status_code == 409
    db.refresh(users[1])
    assert users[1].patient_profile.full_name == 'Nguyễn Văn An'


@pytest.mark.parametrize('field,value', [('full_name','  '), ('phone','abcdefghij'),
    ('date_of_birth','2999-01-01'), ('role','ADMIN')])
def test_invalid_updates_rejected(patient_app, field, value):
    client, _, _, users = patient_app
    data = payload(); data[field] = value
    assert client.put(f'/api/v1/admin/patients/{users[1].id}', json=data).status_code == 422


def test_delete_account_and_linked_records(patient_app):
    client, db, _, users = patient_app
    model = AIModel(model_key='test', display_name='Test', architecture='test', version='1',
                    artifact_path='unused', class_names=['normal'])
    db.add(model); db.flush()
    analysis = AnalysisModel(analysis_code='AXTEST', patient_id=users[1].patient_profile.id,
                             model_id=model.id, original_filename='test.png', stored_image_path='test.png')
    db.add(analysis); db.flush()
    db.add(PredictionModel(analysis_id=analysis.id, predicted_class='normal', confidence=0.9))
    db.add(ReportModel(analysis_id=analysis.id, report_code='RTEST', file_path='test.pdf'))
    db.add(MedicalAdviceModel(analysis_id=analysis.id, provider='test', advice_text='test'))
    db.commit()
    user_id = users[1].id
    assert client.delete(f'/api/v1/admin/patients/{user_id}').status_code == 204
    assert db.scalar(select(UserModel).where(UserModel.id == user_id)) is None
    assert db.scalar(select(MedicalHistoryModel)) is None
    assert db.scalar(select(PatientProfileHistoryModel)) is None
    for model_class in [AnalysisModel, PredictionModel, ReportModel, MedicalAdviceModel]:
        assert db.scalar(select(model_class)) is None
    assert db.scalar(select(AIModel)) is not None
    assert client.get('/api/v1/admin/patients').json()['total'] == 1
    assert client.delete(f'/api/v1/admin/patients/{user_id}').status_code == 404


def test_admin_cannot_be_edited_or_deleted_here(patient_app):
    client, _, _, users = patient_app
    assert client.put(f'/api/v1/admin/patients/{users[0].id}', json=payload()).status_code == 404
    assert client.delete(f'/api/v1/admin/patients/{users[0].id}').status_code == 404


def test_user_cannot_access_patient_management(patient_app):
    client, _, app, users = patient_app
    app.dependency_overrides[get_current_user] = lambda: users[1]
    assert client.get('/api/v1/admin/patients').status_code == 403
    assert client.put('/api/v1/admin/patients/3', json=payload()).status_code == 403
    assert client.delete('/api/v1/admin/patients/3').status_code == 403


def test_guest_cannot_access_patient_management(patient_app):
    client, _, app, _ = patient_app
    app.dependency_overrides.pop(get_current_user)
    assert client.get('/api/v1/admin/patients').status_code == 401



def test_admin_can_view_patient_profile_and_analysis_history(
    patient_app,
):
    client, db, _, users = patient_app

    patient = users[1].patient_profile

    model = AIModel(
        model_key="mobilenetv2",
        display_name="MobileNetV2",
        architecture="MobileNetV2",
        version="1.1.0",
        artifact_path="unused.keras",
        class_names=[
            "normal",
            "pneumonia",
            "tuberculosis",
        ],
    )

    db.add(model)
    db.flush()

    older = AnalysisModel(
        analysis_code="ADMINDETAIL001",
        patient_id=patient.id,
        model_id=model.id,
        input_source="UPLOAD",
        original_filename="older.png",
        stored_image_path="private/older.png",
        status="COMPLETED",
    )

    newer = AnalysisModel(
        analysis_code="ADMINDETAIL002",
        patient_id=patient.id,
        model_id=model.id,
        input_source="UPLOAD",
        original_filename="newer.png",
        stored_image_path="private/newer.png",
        status="COMPLETED",
    )

    db.add_all([
        older,
        newer,
    ])

    db.flush()

    db.add(
        PredictionModel(
            analysis_id=older.id,
            predicted_class="normal",
            confidence=0.91,
        )
    )

    db.add(
        PredictionModel(
            analysis_id=newer.id,
            predicted_class="pneumonia",
            confidence=0.82,
        )
    )

    db.commit()

    response = client.get(
        f"/api/v1/admin/patients/{users[1].id}/details"
    )

    assert response.status_code == 200

    data = response.json()

    profile = data["patient_profile"]

    assert profile["user_id"] == users[1].id
    assert profile["patient_id"] == patient.id
    assert profile["patient_code"] == patient.patient_code
    assert profile["full_name"] == patient.full_name
    assert profile["username"] == users[1].username
    assert profile["email"] == users[1].email

    history = data["analysis_history"]

    assert len(history) == 2

    assert history[0]["analysis_code"] == "ADMINDETAIL002"
    assert history[0]["predicted_class"] == "pneumonia"
    assert history[0]["confidence"] == pytest.approx(
        0.82,
        abs=1e-6,
    )

    assert history[1]["analysis_code"] == "ADMINDETAIL001"
    assert history[1]["predicted_class"] == "normal"

    assert history[0]["model_key"] == "mobilenetv2"
    assert history[0]["model_name"] == "MobileNetV2"
    assert history[0]["model_version"] == "1.1.0"

    serialized = response.text

    assert "password_hash" not in serialized
    assert "stored_image_path" not in serialized
    assert "error_message" not in serialized


def test_admin_patient_detail_handles_patient_without_analyses(
    patient_app,
):
    client, _, _, users = patient_app

    response = client.get(
        f"/api/v1/admin/patients/{users[2].id}/details"
    )

    assert response.status_code == 200

    data = response.json()

    assert (
        data["patient_profile"]["patient_code"]
        == users[2].patient_profile.patient_code
    )

    assert data["analysis_history"] == []


def test_admin_patient_detail_returns_404_for_unknown_user(
    patient_app,
):
    client, _, _, _ = patient_app

    response = client.get(
        "/api/v1/admin/patients/999999/details"
    )

    assert response.status_code == 404


def test_user_cannot_view_admin_patient_detail(
    patient_app,
):
    client, _, app, users = patient_app

    app.dependency_overrides[
        get_current_user
    ] = lambda: users[1]

    response = client.get(
        f"/api/v1/admin/patients/{users[2].id}/details"
    )

    assert response.status_code == 403



def test_admin_patient_detail_includes_medical_history(
    patient_app,
):
    client, db, _, users = patient_app

    patient = users[1].patient_profile

    existing = db.scalars(
        select(MedicalHistoryModel)
        .where(
            MedicalHistoryModel.patient_id
            == patient.id
        )
    ).all()

    for item in existing:
        db.delete(item)

    db.flush()

    older = MedicalHistoryModel(
        patient_id=patient.id,
        current_complaint_hpi="Older complaint",
        past_medical_history="Older medical history",
        past_medication_history="Older medication history",
        allergy_history="Older allergy history",
        diet="Regular diet",
        appetite="Normal",
        sleep="7 hours",
        exercise="Walking",
        bowel_bladder="Normal",
        habits="None",
        family_history="None reported",
        diseases=["Hypertension"],
        medications=["Medication A"],
        allergies=["Penicillin"],
        smoking_status="Never",
        alcohol_status="None",
        occupational_exposure="None",
        notes="Older note",
    )

    newer = MedicalHistoryModel(
        patient_id=patient.id,
        current_complaint_hpi="Newer complaint",
        past_medical_history="Newer medical history",
        past_medication_history="Newer medication history",
        allergy_history="Newer allergy history",
        diet="Soft diet",
        appetite="Reduced",
        sleep="6 hours",
        exercise="Light activity",
        bowel_bladder="No change",
        habits="No smoking",
        family_history="No TB history",
        diseases=["Asthma"],
        medications=["Medication B"],
        allergies=["Dust"],
        smoking_status="Never",
        alcohol_status="Occasional",
        occupational_exposure="Office",
        notes="Newer note",
    )

    db.add(older)
    db.flush()

    from datetime import datetime, timedelta

    older.recorded_at = (
        datetime.now()
        - timedelta(days=1)
    )

    db.add(newer)
    db.flush()

    newer.recorded_at = datetime.now()

    db.commit()

    response = client.get(
        f"/api/v1/admin/patients/"
        f"{users[1].id}/details"
    )

    assert response.status_code == 200

    data = response.json()

    history = data["medical_history"]

    assert len(history) == 2

    assert (
        history[0]["current_complaint_hpi"]
        == "Newer complaint"
    )

    assert (
        history[1]["current_complaint_hpi"]
        == "Older complaint"
    )

    assert history[0]["diseases"] == ["Asthma"]
    assert history[0]["medications"] == ["Medication B"]
    assert history[0]["allergies"] == ["Dust"]

    assert history[0]["smoking_status"] == "Never"
    assert history[0]["alcohol_status"] == "Occasional"

    serialized = response.text

    assert "password_hash" not in serialized
    assert "stored_image_path" not in serialized


def test_admin_patient_detail_empty_medical_history(
    patient_app,
):
    client, _, _, users = patient_app

    response = client.get(
        f"/api/v1/admin/patients/"
        f"{users[2].id}/details"
    )

    assert response.status_code == 200

    assert (
        response.json()["medical_history"]
        == []
    )



def test_admin_patient_detail_includes_latest_report_metadata(
    patient_app,
):
    client, db, _, users = patient_app

    patient = users[1].patient_profile

    model = AIModel(
        model_key="admin-report-model",
        display_name="Admin Report Model",
        architecture="Test",
        version="1.0.0",
        artifact_path="unused.keras",
        class_names=[
            "normal",
            "pneumonia",
            "tuberculosis",
        ],
    )

    db.add(model)
    db.flush()

    analysis = AnalysisModel(
        analysis_code="ADMINREPORTMETA001",
        patient_id=patient.id,
        model_id=model.id,
        input_source="UPLOAD",
        original_filename="report-meta.png",
        stored_image_path="private/report-meta.png",
        status="COMPLETED",
    )

    db.add(analysis)
    db.flush()

    older = ReportModel(
        analysis_id=analysis.id,
        report_code="ADMIN-RP-OLD",
        language="en",
        file_path="private/old.pdf",
    )

    newer = ReportModel(
        analysis_id=analysis.id,
        report_code="ADMIN-RP-NEW",
        language="vi",
        file_path="private/new.pdf",
    )

    db.add(older)
    db.flush()

    from datetime import datetime, timedelta

    older.created_at = (
        datetime.now()
        - timedelta(days=1)
    )

    db.add(newer)
    db.flush()

    newer.created_at = datetime.now()

    db.commit()

    response = client.get(
        f"/api/v1/admin/patients/"
        f"{users[1].id}/details"
    )

    assert response.status_code == 200

    item = next(
        row
        for row
        in response.json()["analysis_history"]
        if row["analysis_code"]
        == "ADMINREPORTMETA001"
    )

    assert item["has_image"] is True
    assert item["report_id"] == newer.id
    assert item["report_code"] == "ADMIN-RP-NEW"
    assert item["report_language"] == "vi"
    assert item["report_created_at"] is not None

    assert "file_path" not in response.text
    assert "stored_image_path" not in response.text


def test_admin_can_view_patient_analysis_image(
    patient_app,
    tmp_path,
):
    client, db, _, users = patient_app

    patient = users[1].patient_profile

    model = AIModel(
        model_key="admin-image-model",
        display_name="Admin Image Model",
        architecture="Test",
        version="1.0.0",
        artifact_path="unused.keras",
        class_names=[
            "normal",
            "pneumonia",
            "tuberculosis",
        ],
    )

    db.add(model)
    db.flush()

    image_path = (
        tmp_path
        / "admin-analysis.jpg"
    )

    image_bytes = (
        b"\xff\xd8\xff\xe0"
        b"ADMIN-IMAGE"
        b"\xff\xd9"
    )

    image_path.write_bytes(
        image_bytes
    )

    analysis = AnalysisModel(
        analysis_code="ADMINIMAGE001",
        patient_id=patient.id,
        model_id=model.id,
        input_source="UPLOAD",
        original_filename="admin-analysis.jpg",
        stored_image_path=str(image_path),
        status="COMPLETED",
    )

    db.add(analysis)
    db.commit()

    response = client.get(
        f"/api/v1/admin/patients/"
        f"{users[1].id}/analyses/"
        f"{analysis.id}/image"
    )

    assert response.status_code == 200

    assert response.headers[
        "content-type"
    ].startswith(
        "image/jpeg"
    )

    assert response.content == image_bytes


def test_admin_analysis_image_must_belong_to_selected_patient(
    patient_app,
    tmp_path,
):
    client, db, _, users = patient_app

    patient = users[1].patient_profile

    model = AIModel(
        model_key="admin-image-owner-model",
        display_name="Admin Image Owner Model",
        architecture="Test",
        version="1.0.0",
        artifact_path="unused.keras",
        class_names=[
            "normal",
            "pneumonia",
            "tuberculosis",
        ],
    )

    db.add(model)
    db.flush()

    image_path = (
        tmp_path
        / "owner-check.jpg"
    )

    image_path.write_bytes(
        b"\xff\xd8OWNER\xff\xd9"
    )

    analysis = AnalysisModel(
        analysis_code="ADMINIMAGEOWNER001",
        patient_id=patient.id,
        model_id=model.id,
        input_source="UPLOAD",
        original_filename="owner-check.jpg",
        stored_image_path=str(image_path),
        status="COMPLETED",
    )

    db.add(analysis)
    db.commit()

    response = client.get(
        f"/api/v1/admin/patients/"
        f"{users[2].id}/analyses/"
        f"{analysis.id}/image"
    )

    assert response.status_code == 404


def test_user_cannot_access_admin_analysis_image(
    patient_app,
):
    client, _, app, users = patient_app

    app.dependency_overrides[
        get_current_user
    ] = lambda: users[1]

    response = client.get(
        f"/api/v1/admin/patients/"
        f"{users[1].id}/analyses/999999/image"
    )

    assert response.status_code == 403



def test_admin_updates_only_latest_medical_history(
    patient_app,
):
    client, db, _, users = patient_app

    patient = users[1].patient_profile

    existing = db.scalars(
        select(MedicalHistoryModel)
        .where(
            MedicalHistoryModel.patient_id
            == patient.id
        )
    ).all()

    for item in existing:
        db.delete(item)

    db.flush()

    from datetime import datetime, timedelta

    older = MedicalHistoryModel(
        patient_id=patient.id,
        current_complaint_hpi="Older complaint",
        diseases=["Old disease"],
        medications=["Old medicine"],
        notes="Older note",
        recorded_at=(
            datetime.now()
            - timedelta(days=1)
        ),
    )

    newer = MedicalHistoryModel(
        patient_id=patient.id,
        current_complaint_hpi="Newest complaint",
        diseases=["Asthma"],
        medications=["Medicine A"],
        allergies=["Dust"],
        smoking_status="Never",
        alcohol_status="None",
        occupational_exposure="Office",
        notes="Newest note",
        recorded_at=datetime.now(),
    )

    db.add_all([
        older,
        newer,
    ])

    db.commit()

    data = payload()

    data["latest_medical_history"] = {
        "id": newer.id,
        "current_complaint_hpi":
            "Updated latest complaint",
        "past_medical_history":
            "Updated medical history",
        "past_medication_history":
            "Updated medication history",
        "allergy_history":
            "Updated allergy history",
        "diet":
            "Balanced diet",
        "appetite":
            "Normal",
        "sleep":
            "7 hours",
        "exercise":
            "Walking",
        "bowel_bladder":
            "Normal",
        "habits":
            "No smoking",
        "family_history":
            "No relevant family history",
        "diseases": [
            "Asthma",
            "Hypertension",
        ],
        "medications": [
            "Medicine B",
        ],
        "allergies": [
            "Penicillin",
        ],
        "smoking_status":
            "Never",
        "alcohol_status":
            "Occasional",
        "occupational_exposure":
            "Office environment",
        "notes":
            "Updated by admin",
    }

    response = client.put(
        f"/api/v1/admin/patients/"
        f"{users[1].id}",
        json=data,
    )

    assert response.status_code == 200

    db.refresh(older)
    db.refresh(newer)

    assert (
        newer.current_complaint_hpi
        == "Updated latest complaint"
    )

    assert newer.diseases == [
        "Asthma",
        "Hypertension",
    ]

    assert newer.medications == [
        "Medicine B",
    ]

    assert newer.allergies == [
        "Penicillin",
    ]

    assert (
        newer.notes
        == "Updated by admin"
    )

    assert (
        older.current_complaint_hpi
        == "Older complaint"
    )

    assert older.diseases == [
        "Old disease"
    ]

    assert (
        older.notes
        == "Older note"
    )


def test_admin_rejects_stale_medical_history_id(
    patient_app,
):
    client, db, _, users = patient_app

    patient = users[1].patient_profile

    existing = db.scalars(
        select(MedicalHistoryModel)
        .where(
            MedicalHistoryModel.patient_id
            == patient.id
        )
    ).all()

    for item in existing:
        db.delete(item)

    db.flush()

    from datetime import datetime, timedelta

    older = MedicalHistoryModel(
        patient_id=patient.id,
        current_complaint_hpi="Older",
        recorded_at=(
            datetime.now()
            - timedelta(days=1)
        ),
    )

    newer = MedicalHistoryModel(
        patient_id=patient.id,
        current_complaint_hpi="Newer",
        recorded_at=datetime.now(),
    )

    db.add_all([
        older,
        newer,
    ])

    db.commit()

    data = payload()

    data["latest_medical_history"] = {
        "id": older.id,
        "current_complaint_hpi":
            "Should not be saved",
    }

    response = client.put(
        f"/api/v1/admin/patients/"
        f"{users[1].id}",
        json=data,
    )

    assert response.status_code == 409

    db.refresh(older)
    db.refresh(newer)

    assert (
        older.current_complaint_hpi
        == "Older"
    )

    assert (
        newer.current_complaint_hpi
        == "Newer"
    )


def test_admin_cannot_update_missing_medical_history(
    patient_app,
):
    client, db, _, users = patient_app

    patient = users[2].patient_profile

    histories = db.scalars(
        select(MedicalHistoryModel)
        .where(
            MedicalHistoryModel.patient_id
            == patient.id
        )
    ).all()

    for item in histories:
        db.delete(item)

    db.commit()

    data = payload()

    data["phone"] = "0900999999"
    data["email"] = "missing-history@example.com"

    data["latest_medical_history"] = {
        "id": 999999,
        "current_complaint_hpi":
            "Should fail",
    }

    response = client.put(
        f"/api/v1/admin/patients/"
        f"{users[2].id}",
        json=data,
    )

    assert response.status_code == 404
