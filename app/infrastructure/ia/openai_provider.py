from typing import Literal, Optional
import json
import logging
import math

from openai import AsyncOpenAI
from openai import APIError as OpenAIAPIError
from pydantic import BaseModel

from app.infrastructure.ia.base import LLMProvider
from app.core.prompts import get_ecg_analysis_prompt
from app.core.exceptions import AIIntegrationException

logger = logging.getLogger(__name__)


# Mesmo schema usado pelo GeminiProvider - o contrato de saída (LaudoIA)
# é compartilhado entre providers, garantindo que o restante do sistema
# (EcgService, rota, schema de resposta) seja agnóstico a qual LLM gerou
# o laudo - essa é a validação prática do Strategy Pattern já defendido
# desde o TCC1.
class LaudoIA(BaseModel):
    ritmo: str
    anomalias_detectadas: bool
    descricao_tecnica: str
    padrao_sugerido: str
    risco: Literal["BAIXO", "MEDIO", "ALTO", "INDETERMINADO"]
    recomendacao: str


class OpenAIProvider(LLMProvider):
    """
    Segundo provedor de LLM, implementado seguindo o mesmo contrato do
    GeminiProvider (LLMProvider). Objetivos: (1) validar empiricamente o
    desacoplamento arquitetural via Strategy Pattern; (2) habilitar
    comparação de comportamento entre provedores sobre o mesmo conjunto
    de dados de validação; (3) obter a camada de confiança via logprobs,
    nativamente suportada por esta API (diferente da Gemini API pública -
    ver docs/DECISOES_TCC2.md, seção 11).
    """

    def __init__(self, api_key: str, model_name: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model_name = model_name

    async def analisar_ecg(self, metadados: dict) -> dict:
        prompt = get_ecg_analysis_prompt(metadados)

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "LaudoIA",
                        "schema": self._schema_strict(),
                        "strict": True,
                    },
                },
                logprobs=True,
                top_logprobs=1,
            )

            laudo = json.loads(response.choices[0].message.content)

            confianca_llm = self._extrair_confianca_media(response)
            if confianca_llm is not None:
                laudo["confianca_llm"] = confianca_llm

            return laudo

        except OpenAIAPIError as e:
            raise AIIntegrationException(f"Erro na API da OpenAI: {str(e)}")
        except json.JSONDecodeError:
            raise AIIntegrationException("A IA não retornou um JSON válido.")
        except Exception as e:
            raise AIIntegrationException(f"Falha inesperada de comunicação: {str(e)}")

    def _schema_strict(self) -> dict:
        """
        O modo 'strict' da OpenAI exige explicitamente que o JSON Schema
        contenha 'additionalProperties: false' - diferente do Gemini
        (response_schema), que aceita o schema puro do Pydantic sem esse
        ajuste. O model_json_schema() do Pydantic não inclui esse campo
        por padrão, então é injetado aqui antes do envio.
        """
        schema = LaudoIA.model_json_schema()
        schema["additionalProperties"] = False
        return schema

    def _extrair_confianca_media(self, response) -> Optional[float]:
        """
        Extrai a probabilidade média (0-1) a partir dos logprobs de cada
        token gerado, nativamente suportados por esta API. Diferente do
        GeminiProvider (que usa avg_logprobs pronto), aqui calculamos a
        média manualmente a partir da lista de logprobs por token,
        já que a OpenAI expõe o detalhe token a token, não um resumo.
        """
        try:
            token_logprobs = response.choices[0].logprobs.content
            if not token_logprobs:
                return None
            media_logprob = sum(t.logprob for t in token_logprobs) / len(token_logprobs)
            return round(math.exp(media_logprob), 4)
        except Exception as e:
            logger.debug(f"Logprobs indisponível para este modelo/resposta: {e}")
            return None