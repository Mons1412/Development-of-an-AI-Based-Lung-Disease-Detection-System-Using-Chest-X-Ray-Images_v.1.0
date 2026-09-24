import json
from pathlib import Path

import tensorflow as tf


PROJECT_ROOT = Path(
    __file__
).resolve().parents[2]

DATASET_ROOT = (
    PROJECT_ROOT
    / "data"
    / "chest_xray_validator"
)

ARTIFACT_ROOT = (
    PROJECT_ROOT
    / "app"
    / "artifacts"
    / "validators"
    / "chest_xray"
    / "1.0.0"
)

IMAGE_SIZE = (
    224,
    224,
)

BATCH_SIZE = 32

SEED = 1412

CLASS_NAMES = [
    "NOT_CHEST_XRAY",
    "CHEST_XRAY",
]


def load_dataset(
    split: str,
    *,
    shuffle: bool,
):

    return (
        tf.keras.utils
        .image_dataset_from_directory(
            DATASET_ROOT / split,
            labels="inferred",
            label_mode="binary",
            class_names=CLASS_NAMES,
            image_size=IMAGE_SIZE,
            batch_size=BATCH_SIZE,
            shuffle=shuffle,
            seed=SEED,
        )
    )


def build_model():

    augmentation = (
        tf.keras.Sequential(
            [
                tf.keras.layers.RandomRotation(
                    0.03
                ),
                tf.keras.layers.RandomZoom(
                    0.05
                ),
                tf.keras.layers.RandomTranslation(
                    0.03,
                    0.03,
                ),
            ],
            name="augmentation",
        )
    )

    inputs = tf.keras.Input(
        shape=(
            224,
            224,
            3,
        )
    )

    x = augmentation(
        inputs
    )

    x = tf.keras.layers.Rescaling(
        scale=1.0 / 127.5,
        offset=-1.0,
        name="rescaling",
    )(x)

    backbone = (
        tf.keras.applications.MobileNetV2(
            include_top=False,
            weights="imagenet",
            input_shape=(
                224,
                224,
                3,
            ),
        )
    )

    backbone.trainable = False

    x = backbone(
        x,
        training=False,
    )

    x = (
        tf.keras.layers
        .GlobalAveragePooling2D()
        (x)
    )

    x = tf.keras.layers.Dropout(
        0.3
    )(x)

    outputs = tf.keras.layers.Dense(
        1,
        activation="sigmoid",
        dtype="float32",
        name="chest_xray_probability",
    )(x)

    return tf.keras.Model(
        inputs,
        outputs,
        name="chest_xray_validator",
    )


def main() -> None:

    ARTIFACT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    train_ds = load_dataset(
        "train",
        shuffle=True,
    )

    validation_ds = load_dataset(
        "validation",
        shuffle=False,
    )

    test_ds = load_dataset(
        "test",
        shuffle=False,
    )

    train_ds = train_ds.prefetch(
        tf.data.AUTOTUNE
    )

    validation_ds = (
        validation_ds.prefetch(
            tf.data.AUTOTUNE
        )
    )

    test_ds = test_ds.prefetch(
        tf.data.AUTOTUNE
    )

    model = build_model()

    model.compile(
        optimizer=tf.keras.optimizers.Adam(
            learning_rate=1e-3
        ),
        loss="binary_crossentropy",
        metrics=[
            "accuracy",
            tf.keras.metrics.Precision(
                name="precision"
            ),
            tf.keras.metrics.Recall(
                name="recall"
            ),
            tf.keras.metrics.AUC(
                name="auc"
            ),
        ],
    )

    checkpoint_path = (
        ARTIFACT_ROOT
        / "chest_xray_validator.keras"
    )

    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(
            checkpoint_path,
            monitor="val_auc",
            mode="max",
            save_best_only=True,
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_auc",
            mode="max",
            patience=4,
            restore_best_weights=True,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            patience=2,
            factor=0.3,
            min_lr=1e-6,
        ),
    ]

    model.fit(
        train_ds,
        validation_data=validation_ds,
        epochs=20,
        callbacks=callbacks,
    )

    best_model = (
        tf.keras.models.load_model(
            checkpoint_path,
            compile=False,
            safe_mode=True,
        )
    )

    best_model.compile(
        loss="binary_crossentropy",
        metrics=[
            "accuracy",
            tf.keras.metrics.Precision(
                name="precision"
            ),
            tf.keras.metrics.Recall(
                name="recall"
            ),
            tf.keras.metrics.AUC(
                name="auc"
            ),
        ],
    )

    results = best_model.evaluate(
        test_ds,
        return_dict=True,
    )

    metrics = {
        key: float(value)
        for key, value
        in results.items()
    }

    (
        ARTIFACT_ROOT
        / "metrics.json"
    ).write_text(
        json.dumps(
            metrics,
            indent=2,
        ),
        encoding="utf-8",
    )

    contract = {
        "model_type":
            "chest_xray_validator",
        "version":
            "1.0.0",
        "input_shape": [
            224,
            224,
            3,
        ],
        "input_dtype":
            "float32",
        "external_normalization":
            False,
        "embedded_rescaling": {
            "scale":
                1.0 / 127.5,
            "offset":
                -1.0,
        },
        "output": {
            "type":
                "sigmoid",
            "positive_class":
                "CHEST_XRAY",
            "negative_class":
                "NOT_CHEST_XRAY",
        },
    }

    (
        ARTIFACT_ROOT
        / "inference_contract.json"
    ).write_text(
        json.dumps(
            contract,
            indent=2,
        ),
        encoding="utf-8",
    )

    class_indices = {
        "NOT_CHEST_XRAY": 0,
        "CHEST_XRAY": 1,
    }

    (
        ARTIFACT_ROOT
        / "class_indices.json"
    ).write_text(
        json.dumps(
            class_indices,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        "Test metrics:",
        metrics,
    )

    print(
        "Artifact:",
        checkpoint_path,
    )


if __name__ == "__main__":
    main()