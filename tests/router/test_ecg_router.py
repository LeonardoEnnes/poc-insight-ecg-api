import pytest
from fastapi.testclient import TestClient
from app.main import app 
from app.infrastructure.ia.factory import AIFactory
from app.infrastructure.ia.base import LLMProvider
from app.core.exceptions import AIIntegrationException

client = TestClient(app)

# mocks para as rotas
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
        # Simulamos uma queda do servidor do Google no meio da requisição (de exemplo)
        raise AIIntegrationException("Timeout na API do Gemini")

# Fixture com um payload válido
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

def test_if_can_process_ecg_successfully(valid_payload):
    """Garante que a API devolve 200 OK quando tudo funciona."""
    
    app.dependency_overrides[AIFactory.get_provider] = lambda: MockSuccessIA()
    
    response = client.post("/api/v1/ecg/process", json=valid_payload)
    
    assert response.status_code == 200
    assert response.json()["risco"] == "BAIXO"
    
    app.dependency_overrides.clear()


def test_if_can_return_502_when_ia_fails(valid_payload):
    """Garante que o Exception Handler captura falhas do Google e devolve 502 Bad Gateway."""
    
    app.dependency_overrides[AIFactory.get_provider] = lambda: MockFailIA()
    
    response = client.post("/api/v1/ecg/process", json=valid_payload)
    
    assert response.status_code == 502
    assert response.json()["error"] == "Falha no Serviço de IA"
    assert "Timeout" in response.json()["detail"]
    
    app.dependency_overrides.clear()


def test_if_can_block_invalid_fhir_schema():
    """Garante que o Pydantic (FHIR Schema) barra lixo antes de chegar ao serviço (Erro 422)."""
    
    invalid_payload = {
        "resourceType": "Observation",
        # Falta a chave 'status' obrigatória no contrato
        "device": {"display": "Monitor Quebrado"},
        "component": [] 
    }
    
    response = client.post("/api/v1/ecg/process", json=invalid_payload)
    
    assert response.status_code == 422
    assert "detail" in response.json()