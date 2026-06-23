import pytest
from fastapi.testclient import TestClient
from app.main import app 
from app.infrastructure.ia.factory import AIFactory
from app.infrastructure.ia.base import LLMProvider
from app.core.exceptions import AIIntegrationException

client = TestClient(app)

class MockSuccessIA(LLMProvider):
    async def analisar_ecg(self, sinal_contexto: str, metadados: dict) -> dict:
        return {
            "ritmo": "Sinusal",
            "anomalias_detectadas": False,
            "descricao_tecnica": "Integração HTTP OK",
            "risco": "BAIXO",
            "recomendacao": "Teste de Rota"
        }

class MockFailIA(LLMProvider):
    async def analisar_ecg(self, sinal_contexto: str, metadados: dict) -> dict:
        raise AIIntegrationException("Timeout na API do Gemini")

@pytest.fixture
def valid_payload():
    return {
        "resourceType": "Observation",
        "status": "final",
        "device": {"display": "Monitor IF-Cloud"},
        "component": [{
            "valueSampledData": {
                "origin": {"value": 0},
                "period": 2.5,
                "factor": 1.0,
                "lowerLimit": -1000,
                "upperLimit": 1000,
                "dimensions": 1,
                "data": "1.0 2.0 3.0"
            }
        }]
    }

@pytest.fixture
def override_ia_success():
    """Injeta o mock de sucesso e limpa após o teste, não importa o que aconteça."""
    app.dependency_overrides[AIFactory.get_provider] = lambda: MockSuccessIA()
    yield
    app.dependency_overrides.clear()

@pytest.fixture
def override_ia_fail():
    """Injeta o mock de falha e limpa após o teste."""
    app.dependency_overrides[AIFactory.get_provider] = lambda: MockFailIA()
    yield
    app.dependency_overrides.clear()

def test_if_can_process_ecg_successfully(valid_payload, override_ia_success):
    """Garante que a API devolve 200 OK quando tudo funciona."""
    response = client.post("/api/v1/ecg/process", json=valid_payload)
    
    assert response.status_code == 200
    assert response.json()["risco"] == "BAIXO"


def test_if_can_return_502_when_ia_fails(valid_payload, override_ia_fail):
    """Garante que o Exception Handler captura falhas do Google e devolve 502 Bad Gateway."""
    response = client.post("/api/v1/ecg/process", json=valid_payload)
    
    assert response.status_code == 502
    assert response.json()["error"] == "Falha no Serviço de IA"
    assert "Timeout" in response.json()["detail"]


def test_if_can_block_invalid_fhir_schema():
    """Garante que o Pydantic (FHIR Schema) barra lixo antes de chegar ao serviço (Erro 422)."""
    invalid_payload = {
        "resourceType": "Observation",
        "device": {"display": "Monitor Quebrado"},
        "component": [] 
    }
    
    response = client.post("/api/v1/ecg/process", json=invalid_payload)
    
    assert response.status_code == 422
    assert "detail" in response.json()