from __future__ import annotations

from dataclasses import dataclass
import logging

from sqlalchemy.orm import Session

from lung_xray_api.application.services.analysis_service import (
    analysis_service,
)
from lung_xray_api.core.batch_limits import (
    MAX_BATCH_FILES,
    MAX_BATCH_TOTAL_BYTES,
)
from lung_xray_api.infrastructure.persistence.orm import (
    UserModel,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BatchImageInput:
    image_bytes: bytes
    original_filename: str
    content_type: str | None


class BatchAnalysisService:

    def analyze_images(
        self,
        db: Session,
        current_user: UserModel,
        *,
        images: list[BatchImageInput],
        model_id: int | None,
    ) -> dict:

        self._validate_batch(
            images
        )

        completed = 0
        rejected = 0
        failed = 0

        items: list[dict] = []

        for image in images:

            try:
                analysis = (
                    analysis_service
                    .analyze_image(
                        db,
                        current_user,
                        image_bytes=(
                            image.image_bytes
                        ),
                        original_filename=(
                            image.original_filename
                        ),
                        content_type=(
                            image.content_type
                        ),
                        model_id=model_id,
                    )
                )

            except ValueError as exc:
                db.rollback()

                rejected += 1

                items.append(
                    {
                        "filename":
                            image.original_filename,
                        "status":
                            "REJECTED",
                        "analysis":
                            None,
                        "error":
                            str(exc),
                    }
                )

                continue

            except LookupError:
                db.rollback()

                # Missing patient profile or another
                # request-wide resource should stop
                # the entire batch.
                raise

            except Exception:
                db.rollback()

                logger.exception(
                    "Unexpected batch analysis "
                    "failure for file %s",
                    image.original_filename,
                )

                failed += 1

                items.append(
                    {
                        "filename":
                            image.original_filename,
                        "status":
                            "FAILED",
                        "analysis":
                            None,
                        "error":
                            (
                                "Image analysis failed "
                                "due to an internal error."
                            ),
                    }
                )

                continue

            completed += 1

            items.append(
                {
                    "filename":
                        image.original_filename,
                    "status":
                        "COMPLETED",
                    "analysis":
                        analysis,
                    "error":
                        None,
                }
            )

        return {
            "total":
                len(images),
            "completed":
                completed,
            "rejected":
                rejected,
            "failed":
                failed,
            "items":
                items,
        }

    @staticmethod
    def _validate_batch(
        images: list[BatchImageInput],
    ) -> None:

        if not images:
            raise ValueError(
                "At least one image is required."
            )

        if len(images) > MAX_BATCH_FILES:
            raise ValueError(
                "Too many files in batch. "
                f"Maximum is {MAX_BATCH_FILES}."
            )

        total_bytes = sum(
            len(image.image_bytes)
            for image in images
        )

        if total_bytes > MAX_BATCH_TOTAL_BYTES:
            max_mb = (
                MAX_BATCH_TOTAL_BYTES
                // 1024
                // 1024
            )

            raise ValueError(
                "Batch size is too large. "
                f"Maximum total size is "
                f"{max_mb} MB."
            )


batch_analysis_service = (
    BatchAnalysisService()
)