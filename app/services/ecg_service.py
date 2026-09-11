import time

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
        inicio = time.perf_counter()

        observation = FHIRObservation(**payload)
        clean_data = observation.get_clean_signal()
        total_original = len(clean_data)

        if total_original == 0:
            raise CorruptedSignalException()

        tipo_analise = "COMPLETA"
        if total_original > cls.MAX_SIGNAL_POINTS:
            clean_data = clean_data[:cls.MAX_SIGNAL_POINTS]
            tipo_analise = f"PARCIAL (Trecho inicial de {cls.MAX_SIGNAL_POINTS} pontos. Total original: {total_original})"

        sampling_rate = 1000 / observation.get_period_ms()
        features = signal_processor.extract_features(clean_data, sampling_rate)

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

        # travas de segurança: os campos determinísticos sempre prevalecem
        # sobre o que o LLM eventualmente tenha sugerido no texto gerado
        resultado_ia["risco"] = classificacao["risco_determinado"]
        resultado_ia["padrao_sugerido"] = classificacao.get(
            "padrao_sugerido", resultado_ia.get("padrao_sugerido")
        )

        # Tempo de processamento total do exame (DSP + classificação + IA),
        # medido de ponta a ponta dentro do serviço. Métrica solicitada
        # pelos avaliadores da MoCITeC (ver docs/DECISOES_TCC2.md).
        tempo_processamento_ms = round((time.perf_counter() - inicio) * 1000, 1)
        resultado_ia["tempo_processamento_ms"] = tempo_processamento_ms

        return resultado_ia