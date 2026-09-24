"""Primary/fallback composition for Dr.AI advice providers."""

from __future__ import annotations

from lung_xray_api.application.services.drai_context_builder import (
    DrAIContext,
)
from lung_xray_api.application.services.medical_advice_provider import (
    MedicalAdviceProvider,
    MedicalAdviceProviderConfigurationError,
    MedicalAdviceProviderError,
    MedicalAdviceProviderResult,
)


class FallbackMedicalAdviceProvider:
    """Use a primary provider and fall back only for provider failures."""

    def __init__(
        self,
        *,
        primary: MedicalAdviceProvider,
        fallback: MedicalAdviceProvider,
    ) -> None:
        self.primary = primary
        self.fallback = fallback

    def generate(
        self,
        *,
        context: DrAIContext,
        language: str,
    ) -> MedicalAdviceProviderResult:
        try:
            return self.primary.generate(
                context=context,
                language=language,
            )

        except (
            MedicalAdviceProviderConfigurationError,
            MedicalAdviceProviderError,
        ):
            return self.fallback.generate(
                context=context,
                language=language,
            )