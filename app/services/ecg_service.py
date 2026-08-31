from app.core.signal_processor import SignalProcessor
from app.core.exceptions import CorruptedSignalException
from app.infrastructure.ia.base import LLMProvider
from app.schemas.fhir_schema import FHIRObservation

class EcgService:
    MAX_SIGNAL_POINTS = 30000

    @classmethod
    async def process_data_for_ai(
        cls, payload: dict, ia_provider: LLMProvider, signal_processor: SignalProcessor
    ) -> dict:
        observation = FHIRObservation(**payload)
        clean_data = observation.get_clean_signal()
        total_original = len(clean_data)

        if total_original == 0:
            raise CorruptedSignalException()

        tipo_analise = "COMPLETA"
        if total_original > cls.MAX_SIGNAL_POINTS:
            clean_data = clean_data[:cls.MAX_SIGNAL_POINTS]
            tipo_analise = f"PARCIAL (Trecho inicial de {cls.MAX_SIGNAL_POINTS} pontos. Total original: {total_original})"

        sampling_rate = 1000 / observation.get_period_ms()  # period em ms -> Hz
        features = signal_processor.extract_features(clean_data, sampling_rate)

        metadados = {
            "device": observation.device.display,
            "period_ms": observation.get_period_ms(),
            "total_pontos_analisados": len(clean_data),
            "tipo_analise": tipo_analise,
            **features,
        }

        return await ia_provider.analisar_ecg(metadados=metadados)