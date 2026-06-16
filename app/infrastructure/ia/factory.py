from app.core.config import settings
from app.infrastructure.ia.base import LLMProvider
from app.infrastructure.ia.gemini import GeminiProvider
from app.core.exceptions import UnsupportedAIProviderException

class AIFactory:
    """
    Responsavel por instaciar o provider da ia com base na variavel de ambiente
    """
    
    @staticmethod
    def get_provider() -> LLMProvider:
        provider_name = settings.AI_PROVIDER.lower()
        
        if provider_name == "gemini":
            return GeminiProvider(
                api_key=settings.AI_API_KEY, 
                model_name=settings.AI_MODEL_NAME
            )
        
        # dps ver como orquestrar isso, talvez seja melhor criar um provider separado e importar aqui -> vai servir para trocar de provider sem quebrar o sistema
        # se gemini falhar ele deve trocar para outra 
        elif provider_name == "openai": # # deixei como exemplo, mas a integracao com a openai vai ser mais complexa, então por enquanto vou deixar só o gemini mesmo
            raise UnsupportedAIProviderException(provider_name)
        else:
            raise UnsupportedAIProviderException(provider_name)