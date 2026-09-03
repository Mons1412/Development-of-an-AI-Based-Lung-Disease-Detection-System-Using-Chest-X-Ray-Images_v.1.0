from decimal import Decimal

from sqlalchemy.orm import Session

from lung_xray_api.infrastructure.persistence.orm import (
    PredictionModel,
    PredictionProbabilityModel,
)


class PredictionRepository:

    def stage_prediction(
        self,
        db: Session,
        *,
        analysis_id: int,
        predicted_class: str,
        confidence: float,
        probabilities: dict[str, float],
    ) -> PredictionModel:

        prediction = PredictionModel(
            analysis_id=analysis_id,
            predicted_class=predicted_class,
            confidence=Decimal(
                str(confidence)
            ),
        )

        db.add(prediction)

        db.flush()

        probability_rows = [
            PredictionProbabilityModel(
                prediction_id=prediction.id,
                class_name=class_name,
                probability=Decimal(
                    str(probability)
                ),
            )
            for class_name, probability
            in probabilities.items()
        ]

        db.add_all(
            probability_rows
        )

        return prediction