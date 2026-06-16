from fastapi import APIRouter
from app.services.ecg_service import EcgService

router = APIRouter(prefix="/api/v1/ecg", tags=["ECG Pipeline"])

@router.post("/process")
async def process_ecg_signal(payload: dict, ia_provider = EcgService.process_data_for_ai):
    """
    Endpoint que recebe o JSON FHIR, processa e retorna o laudo da IA.
    """
    resultado = await EcgService.process_data_for_ai(payload, ia_provider)
    return resultado