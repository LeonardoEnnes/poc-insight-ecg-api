from app.core.exceptions import CorruptedSignalException, SignalTooLongException
from app.schemas.fhir_schema import FHIRObservation
from fastapi import HTTPException, status

class EcgService:
    """
        Servico responsavel por oequestrar logica de negocio, limpa e prepara os dados para o envio as LLMs
    """
    
    MAX_SIGNAL_POINTS = 5000 # limite seguro para n estourar a mem e os tokens (analisar o impacto e a necessidade)

    @classmethod
    def process_data_for_ai(cls, payload: dict) -> dict:
        """Recebe o payload bruto, valida o contrato e extrai o contexto do sinal

        Args:
            payload (dict): _description_

        Raises:
            SignalToLongException: _description_
            CorruptedSignalException: _description_

        Returns:
            dict: _description_
        """
        observation = FHIRObservation(**payload)
        
        clean_data = observation.get_clean_signal()
        total = len(clean_data)
        
        
        if total > cls.MAX_SIGNAL_POINTS:
            raise SignalTooLongException(total, cls.MAX_SIGNAL_POINTS)
        
        if total == 0:
            raise CorruptedSignalException()
        
        signal_context = " " .join(map(str, clean_data)) # converte a lista de floats de volta para strin
        
        return {
            "status": "validação_concluida",
            "dispositivo": observation.device.display,
            "periodo_ms": observation.get_period_ms(),
            "total_pontos": total,
            "tamanho_string_prompt": len(signal_context)
        }