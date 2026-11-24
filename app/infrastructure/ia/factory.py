from app.core.config import settings
from app.infrastructure.ia.base import LLMProvider
from app.infrastructure.ia.gemini import GeminiProvider
from app.infrastructure.ia.openai_provider import OpenAIProvider
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

        elif provider_name == "openai":
            return OpenAIProvider(
                api_key=settings.OPENAI_API_KEY,
                model_name=settings.OPENAI_MODEL_NAME
            )
        else:
            raise UnsupportedAIProviderException(provider_name)