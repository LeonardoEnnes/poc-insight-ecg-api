from app.core.exceptions import CorruptedSignalException
from app.infrastructure.ia.base import LLMProvider
from app.schemas.fhir_schema import FHIRObservation
from app.core.signal_processor import SignalProcessor
from app.core.risk_classifier import RiskClassifier

class EcgService:
    MAX_SIGNAL_POINTS = 30000

    @classmethod
    async def process_data_for_ai(
        cls,
        payload: dict,
        ia_provider: LLMProvider,
        signal_processor: SignalProcessor,
        risk_classifier: RiskClassifier,
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

        # decisão de risco é determinística - o LLM não decide, só narra
        classificacao = risk_classifier.classify(features)

        metadados = {
            "device": observation.device.display,
            "period_ms": observation.get_period_ms(),
            "total_pontos_analisados": len(clean_data),
            "tipo_analise": tipo_analise,
            **features,
            **classificacao,
        }

        resultado_ia = await ia_provider.analisar_ecg(metadados=metadados)

        # trava de segurança: o campo de risco final é SEMPRE o do classificador
        # determinístico, nunca o que o LLM eventualmente tenha sugerido
        resultado_ia["risco"] = classificacao["risco_determinado"]

        return resultado_ia