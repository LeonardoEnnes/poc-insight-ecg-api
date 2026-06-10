from fastapi import APIRouter
from app.services.ecg_service import EcgService
from app.schemas.fhir_schema import EcgResponse

router = APIRouter(prefix="/api/v1/ecg", tags=["ECG Pipeline"])

@router.post("/proccess", response_model=EcgResponse)
async def process_ecg_signal (payload: dict):
    """
    Endpoint que recebe o JSON FHIR, processa e prepara para a IA.
    """
    resultado = EcgService.process_data_for_ai(payload)
    return resultado