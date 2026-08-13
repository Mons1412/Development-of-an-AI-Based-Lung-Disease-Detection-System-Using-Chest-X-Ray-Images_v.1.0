"""Model runtime quản lý vòng đời TensorFlow/Keras model.

Model được load một lần tại lifespan với `compile=False` vì Phase 02 chỉ
inference. Warm-up bằng batch zeros giúp giảm latency request đầu tiên. Module
này import TensorFlow lazy để artifact/unit tests không cần load framework nặng.
"""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Protocol, cast

import numpy as np

from lung_xray_api.core.exceptions import ModelRuntimeError
from lung_xray_api.infrastructure.ml.artifact_bundle import ArtifactBundle


@dataclass(frozen=True)
class ModelLoadStats:
    load_time_ms: int
    warmup_time_ms: int


class LoadedModelProtocol(Protocol):
    def __call__(self, batch: np.ndarray, training: bool = False) -> object:
        """Keras model callable dùng cho inference batch đơn."""
        ...


class ModelRuntime:
    def __init__(self, bundle: ArtifactBundle) -> None:
        self.bundle = bundle
        self.model: LoadedModelProtocol | None = None
        self.load_stats: ModelLoadStats | None = None

    @property
    def ready(self) -> bool:
        return self.model is not None

    def load(self, warm_up: bool = True) -> ModelLoadStats:
        if self.model is not None:
            return self.load_stats or ModelLoadStats(load_time_ms=0, warmup_time_ms=0)

        try:
            import keras
        except ImportError as error:
            raise ModelRuntimeError("Keras/TensorFlow chưa được cài trong môi trường hiện tại") from error

        start = perf_counter()
        try:
            loaded_model = keras.models.load_model(self.bundle.model_path, compile=False, safe_mode=True)
        except TypeError:
            loaded_model = keras.models.load_model(self.bundle.model_path, compile=False)
        self.model = cast(LoadedModelProtocol, loaded_model)
        load_time_ms = int((perf_counter() - start) * 1000)

        warmup_time_ms = 0
        if warm_up:
            batch = np.zeros((1, 224, 224, 3), dtype=np.float32)
            start = perf_counter()
            self.predict_batch(batch)
            warmup_time_ms = int((perf_counter() - start) * 1000)

        self.load_stats = ModelLoadStats(load_time_ms=load_time_ms, warmup_time_ms=warmup_time_ms)
        return self.load_stats

    def predict_batch(self, batch: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise ModelRuntimeError("Model chưa được load")

        # Gọi trực tiếp model với training=False để tránh overhead của predict cho batch đơn.
        output = self.model(batch, training=False)
        return np.asarray(output, dtype=np.float32)

    def close(self) -> None:
        self.model = None
