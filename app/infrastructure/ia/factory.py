from app.core.config import settings
from app.infrastructure.ia.base import LLMProvider
from app.infrastructure.ia.gemini import GeminiProvider

class AIFactory:
    """
    Responsavel por instaciar o provider da ia com base na variavel de ambiente
    """
    
    @staticmethod
    def get_provider() -> LLMProvider:
        provider_name = settings.AI_PROVIDER.lower()
        
        if provider_name == "gemini":
            return GeminiProvider(api_key=settings.AI_API_KEY)
            
        elif provider_name == "openai": # dps ver como orquestrar isso, talvez seja melhor criar um provider separado e importar aqui
            raise NotImplementedError("Integração com OpenAI .")
        else:
            raise ValueError(f"Provedor de IA desconhecido: {provider_name}")