import pytest
from app.services.ecg_service import EcgService
from app.core.exceptions import CorruptedSignalException
from app.infrastructure.ia.base import LLMProvider

class MockIAProvider(LLMProvider):
    """
    mock da IA. Em vez de bater no Google, ele salva o que o EcgService 
    enviou e retorna um laudo falso 
    """
    async def analisar_ecg(self, sinal_contexto: str, metadados: dict) -> dict:
        self.sinal_recebido = sinal_contexto
        self.metadados_recebidos = metadados
        return {
            "ritmo": "Sinusal",
            "anomalias_detectadas": False,
            "descricao_tecnica": "Laudo gerado pelo Mock",
            "risco": "BAIXO",
            "recomendacao": "Nenhuma recomendação"
        }

@pytest.fixture
def mock_provider():
    return MockIAProvider()

@pytest.fixture
def base_fhir_payload():
    return {
        "resourceType": "Observation",
        "status": "final",
        "device": {"display": "Dispositivo Teste"},
        "component": [{
            "valueSampledData": {
                "origin": {"value": 2048},
                "period": 2.5,
                "factor": 1.0,
                "lowerLimit": 800,
                "upperLimit": 1600,
                "dimensions": 1,
                "data": "100.0 101.0 102.0" # Apenas 3 pontos
            }
        }]
    }

@pytest.mark.asyncio
async def test_if_can_proccess_ecg(base_fhir_payload, mock_provider):
    """Garante que um exame normal passe direto e consuma a IA."""
    
    result = await EcgService.process_data_for_ai(base_fhir_payload, mock_provider)
    
    assert result["risco"] == "BAIXO"
    assert result["descricao_tecnica"] == "Laudo gerado pelo Mock"
    
    assert mock_provider.metadados_recebidos["total_pontos_analisados"] == 3
    assert mock_provider.metadados_recebidos["tipo_analise"] == "COMPLETA"


@pytest.mark.asyncio
async def test_if_can_slice_signal_above_limit(base_fhir_payload, mock_provider):
    """Garante que a trava de segurança corte o array sem estourar excao."""
    
    base_fhir_payload["component"][0]["valueSampledData"]["data"] = "100.0 " * 6000 # simula ecg giante de 60000
    
    result = await EcgService.process_data_for_ai(base_fhir_payload, mock_provider)
    
    assert mock_provider.metadados_recebidos["total_pontos_analisados"] == 5000
    assert "PARCIAL" in mock_provider.metadados_recebidos["tipo_analise"]
    
    # Garante que a IA processou a fatia e retornou o laudo
    assert result["risco"] == "BAIXO"


@pytest.mark.asyncio
async def test_if_can_block_empty_signals(base_fhir_payload, mock_provider):
    base_fhir_payload["component"][0]["valueSampledData"]["data"] = "   "
    
    with pytest.raises(CorruptedSignalException):
        await EcgService.process_data_for_ai(base_fhir_payload, mock_provider)