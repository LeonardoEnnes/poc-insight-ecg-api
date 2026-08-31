from app.core.risk_classifier import RiskClassifier
from app.core.signal_processor import SignalProcessor
from app.infrastructure.classification.threshold_risk_classifier import ThresholdRiskClassifier
from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.infrastructure.ia.base import LLMProvider
from app.infrastructure.ia.factory import AIFactory
from app.services.ecg_service import EcgService
from app.infrastructure.if_cloud_client import IFCloudClient, IFCloudIntegrationError
from app.infrastructure.signal.neurokit_processor import NeuroKitSignalProcessor

router = APIRouter(prefix="/api/v1/ecg", tags=["ECG Pipeline"])
security = HTTPBearer(description="Token de acesso do IF-Cloud")

def get_signal_processor() -> SignalProcessor:
    return NeuroKitSignalProcessor()

def get_risk_classifier() -> RiskClassifier:
    return ThresholdRiskClassifier()

@router.post("/process")
async def process_ecg_signal(
    payload: dict,
    ia_provider: LLMProvider = Depends(AIFactory.get_provider),
    signal_processor: SignalProcessor = Depends(get_signal_processor),
    risk_classifier: RiskClassifier = Depends(get_risk_classifier),
):
    """
        Endpoint que recebe o JSON FHIR manualmente, processa e retorna o laudo da IA.
    """
    return await EcgService.process_data_for_ai(payload, ia_provider, signal_processor, risk_classifier)

@router.post("/process")
async def process_ecg_signal(
    payload: dict,
    ia_provider: LLMProvider = Depends(AIFactory.get_provider),
    signal_processor: SignalProcessor = Depends(get_signal_processor),
    risk_classifier: RiskClassifier = Depends(get_risk_classifier),
):
    return await EcgService.process_data_for_ai(payload, ia_provider, signal_processor, risk_classifier)

@router.get("/process/if-cloud/{observation_id}")
async def process_from_if_cloud(
    observation_id: str,
    minute: int = Query(0, description="Minuto específico do ECG a ser extraído e analisado"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    ia_provider: LLMProvider = Depends(AIFactory.get_provider),
    signal_processor: SignalProcessor = Depends(get_signal_processor),
    risk_classifier: RiskClassifier = Depends(get_risk_classifier),
):
    """
    Busca o recurso do IF-Cloud e processa o sinal do minuto especificado.
    """
    token = credentials.credentials
    client = IFCloudClient()
    fhir_payload = await client.get_observation(observation_id, token, minute=minute)
    return await EcgService.process_data_for_ai(fhir_payload, ia_provider, signal_processor, risk_classifier)

@router.get("/process/if-cloud/{observation_id}/range")
async def process_from_if_cloud_range(
    observation_id: str,
    start: int = Query(..., description="Ponto inicial"),
    end: int = Query(..., description="Ponto final"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    ia_provider: LLMProvider = Depends(AIFactory.get_provider),
    signal_processor: SignalProcessor = Depends(get_signal_processor),
    risk_classifier: RiskClassifier = Depends(get_risk_classifier),
):
    """
    Processa um intervalo específico do sinal.
    """
    token = credentials.credentials
    client = IFCloudClient()
    fhir_payload = await client.get_observation_range(observation_id, token, start, end)
    return await EcgService.process_data_for_ai(fhir_payload, ia_provider, signal_processor, risk_classifier)

@router.get("/process/if-cloud/{observation_id}/full")
async def process_from_if_cloud_full(
    observation_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    ia_provider: LLMProvider = Depends(AIFactory.get_provider),
    signal_processor: SignalProcessor = Depends(get_signal_processor),
    risk_classifier: RiskClassifier = Depends(get_risk_classifier),
):
    """
    Busca o recurso completo e processa o sinal (sujeito ao limite de pontos do EcgService).
    """
    token = credentials.credentials
    client = IFCloudClient()
    fhir_payload = await client.get_observation_resource(observation_id, token)
    return await EcgService.process_data_for_ai(fhir_payload, ia_provider, signal_processor, risk_classifier)