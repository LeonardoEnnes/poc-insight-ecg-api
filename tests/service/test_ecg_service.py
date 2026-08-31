from app.core.risk_classifier import RiskClassifier
import pytest
from app.services.ecg_service import EcgService
from app.core.exceptions import CorruptedSignalException
from app.infrastructure.ia.base import LLMProvider
from app.core.signal_processor import SignalProcessor


class MockIAProvider(LLMProvider):
    """
    Mock da IA. Em vez de bater no Google, salva os metadados que o
    EcgService enviou (agora sem sinal bruto) e retorna um laudo falso.
    """
    async def analisar_ecg(self, metadados: dict) -> dict:
        self.metadados_recebidos = metadados
        return {
            "ritmo": "Sinusal",
            "anomalias_detectadas": False,
            "descricao_tecnica": "Laudo gerado pelo Mock",
            "risco": "BAIXO",
            "recomendacao": "Nenhuma recomendação"
        }


class MockSignalProcessor(SignalProcessor):
    """
    Mock do DSP
    """
    def extract_features(self, signal: list[float], sampling_rate: float) -> dict:
        self.signal_recebido = signal
        self.sampling_rate_recebido = sampling_rate
        return {
            "hr_medio_bpm": 75.0,
            "hrv_sdnn_ms": 40.0,
            "n_picos_detectados": 10,
            "qualidade_deteccao": "OK",
        }

class MockRiskClassifier(RiskClassifier):
    def classify(self, features: dict) -> dict:
        return {
            "risco_determinado": "BAIXO",
            "justificativa_classificacao": "Mock - dentro dos parâmetros.",
        }
@pytest.fixture
def mock_provider():
    return MockIAProvider()

@pytest.fixture
def mock_risk_classifier():
    return MockRiskClassifier()


@pytest.fixture
def mock_signal_processor():
    return MockSignalProcessor()


@pytest.fixture
def base_fhir_payload():
    return {
        "resourceType": "Observation",
        "status": "final",
        "device": {"display": "Dispositivo Teste"},
        "component": [{
            "valueSampledData": {
                "origin": {"value": 0},
                "period": 2.5,
                "factor": 1.0,
                "lowerLimit": 800,
                "upperLimit": 1600,
                "dimensions": 1,
                "data": "100.0 101.0 102.0"  # Apenas 3 pontos
            }
        }]
    }


@pytest.mark.asyncio
async def test_if_can_process_ecg(base_fhir_payload, mock_provider, mock_signal_processor, mock_risk_classifier):
    """Garante que um exame normal passe pelo DSP e pela IA corretamente."""

    result = await EcgService.process_data_for_ai(
        base_fhir_payload, mock_provider, mock_signal_processor, mock_risk_classifier
    )

    assert result["risco"] == "BAIXO"
    assert result["descricao_tecnica"] == "Laudo gerado pelo Mock"

    # Confere que os metadados enviados pra IA já incluem as features do DSP
    assert mock_provider.metadados_recebidos["total_pontos_analisados"] == 3
    assert mock_provider.metadados_recebidos["tipo_analise"] == "COMPLETA"
    assert mock_provider.metadados_recebidos["hr_medio_bpm"] == 75.0
    assert mock_provider.metadados_recebidos["qualidade_deteccao"] == "OK"

    # Confere que o DSP recebeu o sinal já convertido (factor/origin aplicados)
    assert mock_signal_processor.signal_recebido == [100.0, 101.0, 102.0]


@pytest.mark.asyncio
async def test_if_applies_factor_and_origin_before_dsp(mock_provider, mock_signal_processor, mock_risk_classifier):
    """
    Garante que a conversão de unidade (factor/origin) é aplicada
    ANTES do sinal chegar no DSP - regressão do bug identificado.
    """
    payload = {
        "resourceType": "Observation",
        "status": "final",
        "device": {"display": "Dispositivo Teste"},
        "component": [{
            "valueSampledData": {
                "origin": {"value": 10.0},
                "period": 2.5,
                "factor": 2.0,
                "lowerLimit": 0,
                "upperLimit": 5000,
                "dimensions": 1,
                "data": "1.0 2.0 3.0"
            }
        }]
    }

    await EcgService.process_data_for_ai(payload, mock_provider, mock_signal_processor, mock_risk_classifier)

    # esperado: (v * factor) + origin -> [1*2+10, 2*2+10, 3*2+10] = [12, 14, 16]
    assert mock_signal_processor.signal_recebido == [12.0, 14.0, 16.0]


@pytest.mark.asyncio
async def test_if_can_slice_signal_above_limit(base_fhir_payload, mock_provider, mock_signal_processor, mock_risk_classifier):
    """Garante que a trava de segurança corte o array sem estourar exceção."""

    base_fhir_payload["component"][0]["valueSampledData"]["data"] = "100.0 " * 60000

    result = await EcgService.process_data_for_ai(
        base_fhir_payload, mock_provider, mock_signal_processor, mock_risk_classifier
    )

    assert mock_provider.metadados_recebidos["total_pontos_analisados"] == 30000
    assert "PARCIAL" in mock_provider.metadados_recebidos["tipo_analise"]
    assert len(mock_signal_processor.signal_recebido) == 30000
    assert result["risco"] == "BAIXO"


@pytest.mark.asyncio
async def test_if_can_block_empty_signals(base_fhir_payload, mock_provider, mock_signal_processor, mock_risk_classifier):
    base_fhir_payload["component"][0]["valueSampledData"]["data"] = "   "

    with pytest.raises(CorruptedSignalException):
        await EcgService.process_data_for_ai(base_fhir_payload, mock_provider, mock_signal_processor, mock_risk_classifier)


@pytest.mark.asyncio
async def test_if_does_not_slice_signal_exactly_at_limit(base_fhir_payload, mock_provider, mock_signal_processor, mock_risk_classifier):
    """Garante que um sinal com exatamente 30.000 pontos seja processado como completo."""

    base_fhir_payload["component"][0]["valueSampledData"]["data"] = "100.0 " * EcgService.MAX_SIGNAL_POINTS

    result = await EcgService.process_data_for_ai(
        base_fhir_payload, mock_provider, mock_signal_processor, mock_risk_classifier
    )

    assert mock_provider.metadados_recebidos["total_pontos_analisados"] == EcgService.MAX_SIGNAL_POINTS
    assert mock_provider.metadados_recebidos["tipo_analise"] == "COMPLETA"


@pytest.mark.asyncio
async def test_if_flags_insufficient_signal_quality(base_fhir_payload, mock_provider, mock_risk_classifier):
    """
    Garante que quando o DSP não consegue detectar picos suficientes,
    o metadado de qualidade INSUFICIENTE chega até a IA (não é silenciado).
    """
    class LowQualitySignalProcessor(SignalProcessor):
        def extract_features(self, signal, sampling_rate):
            return {
                "hr_medio_bpm": None,
                "hrv_sdnn_ms": None,
                "n_picos_detectados": 1,
                "qualidade_deteccao": "INSUFICIENTE",
            }

    result = await EcgService.process_data_for_ai(
        base_fhir_payload, mock_provider, LowQualitySignalProcessor(), mock_risk_classifier
    )

    assert mock_provider.metadados_recebidos["qualidade_deteccao"] == "INSUFICIENTE"
    # o mock sempre devolve BAIXO, mas o ponto do teste é garantir que o dado
    # de baixa qualidade FOI enviado - o comportamento real da IA é testado à parte