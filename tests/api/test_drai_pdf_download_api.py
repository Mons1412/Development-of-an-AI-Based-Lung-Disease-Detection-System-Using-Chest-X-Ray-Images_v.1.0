from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from lung_xray_api.api.dependencies.auth import get_current_user
from lung_xray_api.api.v1 import medical_advices as medical_advices_api
from lung_xray_api.application.services.medical_advice_service import (
    medical_advice_service,
)
from lung_xray_api.infrastructure.persistence.database import get_db
from lung_xray_api.main import app


SAMPLE_ADVICE_TEXT = """PHIẾU TƯ VẤN VÀ HƯỚNG DẪN Y TẾ SAU KHÁM
(Dùng cho bệnh nhân ngoại trú / Hỗ trợ chuyên môn bởi Dr.AI)

PHẦN I: THÔNG TIN HÀNH CHÍNH
Họ và tên: Nguyễn Văn A
Tuổi/Năm sinh: 22 / 2004

PHẦN II: TÓM TẮT TÌNH TRẠNG VÀ KẾT QUẢ KHÁM
Risk level: LOW
Summary conclusion: Kết quả AI có xu hướng bình thường.
Summary recommendation: Tiếp tục theo dõi sức khỏe.

1. Kết luận chính
Chưa ghi nhận dấu hiệu cảnh báo cấp tính trong dữ liệu được cung cấp.

2. Kết quả X-quang phổi - AI
Mô hình: MobileNetV2, 1.1.0
- Tuberculosis: 5.00%
- Normal: 90.00%
- Pneumonia: 5.00%

PHẦN III: HƯỚNG DẪN ĐIỀU TRỊ VÀ LƯU Ý DÙNG THUỐC
Không tự ý sử dụng thuốc kê đơn.

PHẦN IV: HƯỚNG DẪN CHẾ ĐỘ DINH DƯỠNG & SINH HOẠT
Duy trì chế độ ăn uống và nghỉ ngơi phù hợp.

PHẦN V: DẤU HIỆU CẦN TÁI KHÁM NGAY & LỊCH HẸN
Khám ngay nếu khó thở tăng, đau ngực dữ dội hoặc ho ra máu.

PHẦN VI: THÔNG TIN TRUY XUẤT KỸ THUẬT HỆ THỐNG
Mã bệnh nhân: PT0001
Mã báo cáo tư vấn: DATEST0001
Mã phân tích: AN000329

<!> ỨNG DỤNG CHỈ CÓ TÍNH CHẤT THAM KHẢO VÀ KHÔNG THAY THẾ CHẨN ĐOÁN HOẶC QUYẾT ĐỊNH ĐIỀU TRỊ CỦA CHUYÊN GIA Y TẾ.
"""


@pytest.fixture
def client():
    fake_db = object()

    fake_user = SimpleNamespace(
        id=2,
        role="ADMIN",
        is_active=True,
    )

    def override_db():
        return fake_db

    def override_current_user():
        return fake_user

    app.dependency_overrides[
        get_db
    ] = override_db

    app.dependency_overrides[
        get_current_user
    ] = override_current_user

    try:
        with TestClient(app) as test_client:
            yield (
                test_client,
                fake_db,
                fake_user,
            )
    finally:
        app.dependency_overrides.pop(
            get_db,
            None,
        )
        app.dependency_overrides.pop(
            get_current_user,
            None,
        )


def test_download_drai_pdf_returns_attachment(
    client,
    monkeypatch,
):
    test_client, fake_db, fake_user = client

    advice = SimpleNamespace(
        id=12,
        analysis_id=329,
        language="vi",
        advice_text=SAMPLE_ADVICE_TEXT,
    )

    def fake_get_advice(
        db,
        current_user,
        *,
        advice_id,
    ):
        assert db is fake_db
        assert current_user is fake_user
        assert advice_id == 12
        return advice

    monkeypatch.setattr(
        medical_advice_service,
        "get_advice",
        fake_get_advice,
    )

    analysis = SimpleNamespace(
        id=329,
        analysis_code="AN20260921222810ED962A6AA8",
        original_filename="tuberculosis-1067.jpg",
        stored_image_path="",
        created_at=datetime(
            2026,
            9,
            21,
            22,
            28,
            10,
        ),
        prediction=SimpleNamespace(
            probabilities=[
                SimpleNamespace(
                    class_name="tuberculosis",
                    probability=0.5115,
                ),
                SimpleNamespace(
                    class_name="normal",
                    probability=0.3242,
                ),
                SimpleNamespace(
                    class_name="pneumonia",
                    probability=0.1643,
                ),
            ]
        ),
    )

    def fake_get_analysis(
        db,
        analysis_id,
    ):
        assert db is fake_db
        assert analysis_id == 329
        return analysis

    monkeypatch.setattr(
        medical_advices_api.analysis_repository,
        "get_by_id",
        fake_get_analysis,
    )

    response = test_client.get(
        "/api/v1/medical-advices/12/download"
    )

    assert response.status_code == 200

    assert response.headers[
        "content-type"
    ].startswith(
        "application/pdf"
    )

    assert response.headers[
        "content-disposition"
    ] == (
        'attachment; filename="'
        'DrAI-analysis-329-advice-12-vi.pdf"'
    )

    assert response.headers[
        "cache-control"
    ] == "no-store"

    assert response.content.startswith(
        b"%PDF-"
    )


@pytest.mark.parametrize(
    (
        "exception",
        "expected_status",
    ),
    [
        (
            LookupError(
                "Medical advice not found."
            ),
            404,
        ),
        (
            PermissionError(
                "Unsupported user role."
            ),
            403,
        ),
        (
            ValueError(
                "Dr.AI advice text cannot be empty."
            ),
            400,
        ),
    ],
)
def test_download_drai_pdf_maps_domain_errors(
    client,
    monkeypatch,
    exception,
    expected_status,
):
    test_client, _, _ = client

    def fake_get_advice(
        db,
        current_user,
        *,
        advice_id,
    ):
        raise exception

    monkeypatch.setattr(
        medical_advice_service,
        "get_advice",
        fake_get_advice,
    )

    response = test_client.get(
        "/api/v1/medical-advices/12/download"
    )

    assert (
        response.status_code
        == expected_status
    )