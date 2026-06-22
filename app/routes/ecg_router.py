from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.infrastructure.ia.base import LLMProvider
from app.infrastructure.ia.factory import AIFactory
from app.services.ecg_service import EcgService
from app.infrastructure.if_cloud_client import IFCloudClient, IFCloudIntegrationError

router = APIRouter(prefix="/api/v1/ecg", tags=["ECG Pipeline"])
security = HTTPBearer(description="Token de acesso do IF-Cloud")

@router.post("/process")
async def process_ecg_signal(payload: dict, ia_provider: LLMProvider = Depends(AIFactory.get_provider)):
    """
    Endpoint que recebe o JSON FHIR manualmente, processa e retorna o laudo da IA.
    """
    resultado = await EcgService.process_data_for_ai(payload, ia_provider)
    return resultado

@router.get("/process/if-cloud/{observation_id}")
async def process_from_if_cloud(
    observation_id: str,
    minute: int = Query(0, description="Minuto específico do ECG a ser extraído e analisado"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    ia_provider: LLMProvider = Depends(AIFactory.get_provider)
):
    """
    Endpoint que busca o ECG data de um Observation por ID e minuto e envia o sinal para a IA.
    """
    token = credentials.credentials
    
    client = IFCloudClient()
    fhir_payload = await client.get_observation(observation_id, token, minute=minute)
    
    resultado = await EcgService.process_data_for_ai(fhir_payload, ia_provider)
    
    return resultado