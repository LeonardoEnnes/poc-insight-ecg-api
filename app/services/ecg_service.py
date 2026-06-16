from app.core.exceptions import CorruptedSignalException, SignalTooLongException
from app.infrastructure.ia.factory import AIFactory
from app.schemas.fhir_schema import FHIRObservation
from app.infrastructure.ia.base import LLMProvider

class EcgService:
    """
        Servico responsavel por oequestrar logica de negocio, limpa e prepara os dados para o envio as LLMs
    """
    
    MAX_SIGNAL_POINTS = 5000 

    @classmethod
    async def process_data_for_ai(cls, payload: dict, ia_provider: LLMProvider) -> dict:
        """Recebe o payload bruto, valida o contrato e extrai o contexto do sinal"""

        observation = FHIRObservation(**payload)
        clean_data = observation.get_clean_signal()
        total = len(clean_data)
        
        
        # tem que ver essa validações depois, talvez seja melhor criar uma classe de validação separada, ou até mesmo usar pydantic para isso, mas por enquanto vamos deixar aqui mesmo
        if total > cls.MAX_SIGNAL_POINTS:
            raise SignalTooLongException(total, cls.MAX_SIGNAL_POINTS)
        
        if total == 0:
            raise CorruptedSignalException()
        
        signal_context = " " .join(map(str, clean_data))
        
        metadados = {
            "device": observation.device.display,
            "period_ms": observation.get_period_ms(),
            "total_pontos": total
        }
        
        laudo = await ia_provider.analisar_ecg(sinal_contexto=signal_context, metadados=metadados)
        
        return laudo