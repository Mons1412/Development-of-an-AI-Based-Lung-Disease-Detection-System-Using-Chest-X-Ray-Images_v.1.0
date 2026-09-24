from io import BytesIO

from PIL import Image

from lung_xray_api.infrastructure.ml.image_preprocessor import (
    image_preprocessor,
)
from lung_xray_api.infrastructure.ml.runtime_manager import (
    runtime_manager,
)
from lung_xray_api.infrastructure.persistence.database import (
    SessionLocal,
)
from lung_xray_api.infrastructure.persistence.orm import (
    AIModel,
)


def main() -> None:

    db = SessionLocal()

    try:
        model_record = (
            db.query(AIModel)
            .filter_by(
                is_default=True,
                is_active=True,
            )
            .first()
        )

        if model_record is None:
            raise RuntimeError(
                "Default AI model not found."
            )

        print(
            "Model:",
            model_record.model_key,
            model_record.version,
        )

        buffer = BytesIO()

        Image.new(
            "L",
            (512, 512),
            128,
        ).save(
            buffer,
            format="PNG",
        )

        batch = (
            image_preprocessor.preprocess(
                buffer.getvalue()
            )
        )

        print(
            "Input shape:",
            batch.shape,
        )

        print(
            "Input range:",
            float(batch.min()),
            float(batch.max()),
        )

        runtime = (
            runtime_manager.get_runtime(
                model_record
            )
        )

        prediction = runtime.predict(
            batch
        )

        print(
            "Predicted class:",
            prediction.predicted_class,
        )

        print(
            "Confidence:",
            prediction.confidence,
        )

        print(
            "Probabilities:",
            prediction.probabilities,
        )

        print(
            "Probability sum:",
            sum(
                prediction.probabilities.values()
            ),
        )

        print(
            "Loaded runtimes:",
            runtime_manager.loaded_models(),
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()