from app.core.exceptions import CorruptedSignalException
from app.infrastructure.ia.factory import AIFactory
from app.schemas.fhir_schema import FHIRObservation
from app.infrastructure.ia.base import LLMProvider

class EcgService:
    """
        Servico responsavel por oequestrar logica de negocio, limpa e prepara os dados para o envio as LLMs
    """
    
    MAX_SIGNAL_POINTS = 5000 # Deixei 5000 setado por hora (futuramente analisar a possibilidade de aumentar)

    @classmethod
    async def process_data_for_ai(cls, payload: dict, ia_provider: LLMProvider) -> dict:
        """
        Recebe o payload FHIR, extrai os biossinais e prepara o contexto para a IA.
        
        DECISÃO ARQUITETURAL (ADR - Limite de Tokens):
        Para evitar o esgotamento da cota da API (Tokens) e prevenir a perda de contexto 
        da IA em exames contínuos (fenômeno 'Lost in the Middle'), foi aplicado um teto rigido 
        (MAX_SIGNAL_POINTS). Exames massivos (ex: Holter) sofrem 'crop' clínico, processando 
        apenas a primeira janela de observação viável
        """
        observation = FHIRObservation(**payload)
        clean_data = observation.get_clean_signal()
        total_original = len(clean_data)
        
        if total_original == 0:
            raise CorruptedSignalException()

        tipo_analise = "COMPLETA"
        
        # fatiamento para protecao de infraestrutura e performance
        if total_original > cls.MAX_SIGNAL_POINTS:
            clean_data = clean_data[:cls.MAX_SIGNAL_POINTS]
            tipo_analise = f"PARCIAL (Trecho inicial de {cls.MAX_SIGNAL_POINTS} pontos. Total original: {total_original})"

        total_processado = len(clean_data)
        signal_context = " ".join(map(str, clean_data))
        
        metadados = {
            "device": observation.device.display,
            "period_ms": observation.get_period_ms(),
            "total_pontos_analisados": total_processado,
            "tipo_analise": tipo_analise
        }
        
        return await ia_provider.analisar_ecg(sinal_contexto=signal_context, metadados=metadados)