import re

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from lung_xray_api.infrastructure.persistence.orm import PatientProfileModel, UserModel


class AdminPatientRepository:
    def search(self, db: Session, *, query: str, page: int, limit: int):
        statement = select(UserModel, PatientProfileModel).join(
            PatientProfileModel, PatientProfileModel.user_id == UserModel.id
        ).where(UserModel.role == "USER")
        if query:
            filters = [PatientProfileModel.full_name.icontains(query, autoescape=True),
                       PatientProfileModel.address.icontains(query, autoescape=True),
                       UserModel.phone.contains(query, autoescape=True),
                       PatientProfileModel.phone.contains(query, autoescape=True)]
            if re.fullmatch(r"\+?[0-9\s().-]+", query):
                phone = re.sub(r"[^0-9]", "", query)
                if phone.startswith("84") and (query.startswith("+84") or len(phone) == 11):
                    phone = "0" + phone[2:]
                if phone:
                    filters.extend([UserModel.phone.contains(phone, autoescape=True),
                                    PatientProfileModel.phone.contains(phone, autoescape=True)])
            statement = statement.where(or_(*filters))
        total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
        rows = db.execute(statement.order_by(UserModel.id.desc())
                          .offset((page - 1) * limit).limit(limit)).all()
        return rows, total

    def get(self, db: Session, user_id: int):
        return db.execute(select(UserModel, PatientProfileModel).join(
            PatientProfileModel, PatientProfileModel.user_id == UserModel.id
        ).where(UserModel.id == user_id, UserModel.role == "USER")).first()
