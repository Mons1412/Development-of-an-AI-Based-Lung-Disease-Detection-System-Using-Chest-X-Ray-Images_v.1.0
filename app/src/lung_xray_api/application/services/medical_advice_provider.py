from dataclasses import dataclass
from typing import Protocol

from lung_xray_api.application.services.drai_context_builder import (
    DrAIContext,
)


@dataclass(
    frozen=True,
    slots=True,
)
class MedicalAdviceProviderResult:
    provider: str
    model_name: str
    advice_text: str


class MedicalAdviceProviderConfigurationError(
    RuntimeError
):
    pass


class MedicalAdviceProviderError(
    RuntimeError
):
    pass


class MedicalAdviceProvider(Protocol):

    def generate(
        self,
        *,
        context: DrAIContext,
        language: str,
    ) -> MedicalAdviceProviderResult:
        ...
