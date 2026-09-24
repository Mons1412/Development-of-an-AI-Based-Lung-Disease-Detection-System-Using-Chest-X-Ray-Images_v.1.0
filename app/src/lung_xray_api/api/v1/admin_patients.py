import mimetypes

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from lung_xray_api.api.dependencies.auth import require_admin
from lung_xray_api.application.services.admin_patient_service import admin_patient_service, PatientConflictError
from lung_xray_api.infrastructure.persistence.database import get_db
from lung_xray_api.schemas.admin_patient import (
    AdminPatientDetailResponse,
    AdminPatientPage,
    AdminPatientResponse,
    AdminPatientUpdate,
)

router = APIRouter(prefix="/patients", dependencies=[Depends(require_admin)])


@router.get("", response_model=AdminPatientPage)
def search_patients(
    q: Annotated[str, Query(max_length=500)] = "",
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    db: Session = Depends(get_db),
):
    return admin_patient_service.search(db, query=q, page=page, limit=limit)




@router.get(
    "/{user_id}/details",
    response_model=AdminPatientDetailResponse,
)
def get_patient_details(
    user_id: int,
    db: Session = Depends(get_db),
):
    try:
        return admin_patient_service.detail(
            db,
            user_id,
        )
    except LookupError as exc:
        raise HTTPException(
            404,
            str(exc),
        ) from exc




@router.get(
    "/{user_id}/analyses/{analysis_id}/image"
)
def get_patient_analysis_image(
    user_id: int,
    analysis_id: int,
    db: Session = Depends(get_db),
):
    try:
        file_path = (
            admin_patient_service
            .resolve_analysis_image(
                db,
                user_id=user_id,
                analysis_id=analysis_id,
            )
        )

    except (
        LookupError,
        FileNotFoundError,
    ) as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    media_type = (
        mimetypes.guess_type(
            file_path.name
        )[0]
        or "application/octet-stream"
    )

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        headers={
            "Cache-Control":
                "private, max-age=300",
        },
    )


@router.put("/{user_id}", response_model=AdminPatientResponse)
def update_patient(user_id: int, payload: AdminPatientUpdate, db: Session = Depends(get_db)):
    try:
        return admin_patient_service.update(db, user_id, payload)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except PatientConflictError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.delete("/{user_id}", status_code=204)
def delete_patient(user_id: int, db: Session = Depends(get_db)):
    try:
        admin_patient_service.delete(db, user_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except PatientConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    return Response(status_code=204)
