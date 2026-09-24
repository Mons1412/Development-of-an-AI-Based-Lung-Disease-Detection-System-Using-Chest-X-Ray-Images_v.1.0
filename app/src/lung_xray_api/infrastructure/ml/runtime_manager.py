from threading import Lock

from lung_xray_api.infrastructure.ml.model_runtime import (
    ModelRuntime,
)
from lung_xray_api.infrastructure.persistence.orm import (
    AIModel,
)


class RuntimeManager:

    def __init__(self) -> None:
        self._runtimes: dict[
            tuple[str, str],
            ModelRuntime,
        ] = {}

        self._lock = Lock()

    def get_runtime(
        self,
        model_record: AIModel,
    ) -> ModelRuntime:

        key = (
            model_record.model_key,
            model_record.version,
        )

        runtime = self._runtimes.get(
            key
        )

        if runtime is not None:
            return runtime

        with self._lock:

            runtime = self._runtimes.get(
                key
            )

            if runtime is None:
                runtime = ModelRuntime(
                    artifact_path=(
                        model_record.artifact_path
                    ),
                    class_names=(
                        model_record.class_names
                    ),
                )

                self._runtimes[key] = (
                    runtime
                )

        return runtime

    def loaded_models(
        self,
    ) -> list[tuple[str, str]]:

        return list(
            self._runtimes.keys()
        )


runtime_manager = RuntimeManager()