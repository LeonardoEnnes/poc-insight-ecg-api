from abc import ABC, abstractmethod

class LLMProvider(ABC):
    """
    Interface base para provedores de ia Generativa.
    Vai garantir que qualquer modelo integrado siga o mesmo contrato de metodo e retorno
    """
    
    @abstractmethod
    async def analisar_ecg(self, sinal_contexto: str, metadados: dict) -> dict:
        pass