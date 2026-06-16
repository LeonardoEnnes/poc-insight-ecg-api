import pytest
from app.services.ecg_service import EcgService
from app.core.exceptions import SignalTooLongException, CorruptedSignalException, InvalidSignalValueException

#o ideal e testar de formas diferentes, esse e apenas um exemplo de retorno, poderia no futuro testar outros tipos
@pytest.fixture
def base_fhir_payload():
    return {
        "resourceType": "Observation",
        "status": "final",
        "device": {
            "display": "Dispositivo de Teste Unitario"
        },
        "component": [
            {
                "valueSampledData": {
                    "origin": {"value": 2048},
                    "period": 2.5,
                    "factor": 1.0,
                    "lowerLimit": 800,
                    "upperLimit": 1600,
                    "dimensions": 1,
                    "data": "100.0 101.0 102.0" # Apenas 3 pontos
                }
            }
        ]
    } 

def test_if_can_process_valid_ecg(base_fhir_payload):
    result = EcgService.process_data_for_ai(base_fhir_payload)
    
    assert result["status"] == "validação_concluida"
    assert result["total_pontos"] == 3
    assert result["dispositivo"] == "Dispositivo de Teste Unitario"

def test_deve_bloquear_sinal_acima_do_limite(base_fhir_payload):
    base_fhir_payload["component"][0]["valueSampledData"]["data"] = "100.0 " * 5001
    
    with pytest.raises(SignalTooLongException) as exc_info:
        EcgService.process_data_for_ai(base_fhir_payload)
        
    assert "5001/5000 pontos" in exc_info.value.message

def test_deve_bloquear_sinal_vazio(base_fhir_payload):
    base_fhir_payload["component"][0]["valueSampledData"]["data"] = "   "
    
    with pytest.raises(CorruptedSignalException):
        EcgService.process_data_for_ai(base_fhir_payload)