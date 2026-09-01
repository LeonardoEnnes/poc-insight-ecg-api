from typing import Literal, Optional
from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel
from app.infrastructure.ia.base import LLMProvider
from app.core.prompts import get_ecg_analysis_prompt
from app.core.exceptions import AIIntegrationException
import json
import logging

logger = logging.getLogger(__name__)

# schema de resposta para travar a resposta, previnindo alucinação
class LaudoIA(BaseModel):
    ritmo: str
    anomalias_detectadas: bool
    descricao_tecnica: str
    risco: Literal["BAIXO", "MEDIO", "ALTO", "INDETERMINADO"]
    recomendacao: str


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model_name: str):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    async def analisar_ecg(self, metadados: dict) -> dict:
        prompt = get_ecg_analysis_prompt(metadados)

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=LaudoIA,
                    response_logprobs=True,
                    logprobs=1,
                ),
            )
            laudo = json.loads(response.text)

            # Confiança via logprobs (segunda camada, complementar à
            # confiança derivada do sinal/DSP) - best-effort: nem todo
            # modelo/versão do Gemini suporta essa funcionalidade, então
            # a ausência não deve derrubar a resposta principal.
            confianca_llm = self._extrair_confianca_media(response)
            if confianca_llm is not None:
                laudo["confianca_llm"] = confianca_llm

            return laudo

        except APIError as e:
            raise AIIntegrationException(f"Erro na API do Google: {e.message}")
        except json.JSONDecodeError:
            raise AIIntegrationException("A IA não retornou um JSON válido.")
        except Exception as e:
            raise AIIntegrationException(f"Falha inesperada de comunicação: {str(e)}")

    def _extrair_confianca_media(self, response) -> Optional[float]:
        """
        Extrai a probabilidade média (em escala 0-1) dos tokens gerados,
        a partir do avgLogprobs retornado pela API, quando disponível.

        avgLogprobs é a média das log-probabilidades dos tokens escolhidos
        na resposta - próximo de 0 (ex: -0.05) indica alta confiança;
        valores mais negativos (ex: -2.0) indicam maior incerteza do modelo.
        Convertido aqui para probabilidade média via exp(), numa escala
        mais intuitiva (0 a 1).

        Retorna None silenciosamente se o modelo/versão não suportar
        logprobs - não deve derrubar a resposta principal por causa disso.
        """
        try:
            import math
            candidate = response.candidates[0]
            avg_logprob = getattr(candidate, "avg_logprobs", None)
            if avg_logprob is None:
                return None
            return round(math.exp(avg_logprob), 4)
        except Exception as e:
            logger.debug(f"Logprobs indisponível para este modelo/resposta: {e}")
            return None