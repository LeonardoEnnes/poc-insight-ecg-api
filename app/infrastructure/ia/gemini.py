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
    padrao_sugerido: str
    risco: Literal["BAIXO", "MEDIO", "ALTO", "INDETERMINADO"]
    recomendacao: str


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model_name: str):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    async def analisar_ecg(self, metadados: dict) -> dict:
        prompt = get_ecg_analysis_prompt(metadados)

        try:
            response = await self._gerar_com_fallback_logprobs(prompt)
            laudo = json.loads(response.text)

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

    async def _gerar_com_fallback_logprobs(self, prompt: str):
        """
        Tenta gerar a resposta com logprobs habilitado (para a camada extra
        de confiança). Se o modelo configurado não suportar essa
        funcionalidade (ex: "Logprobs is not enabled for this model"),
        refaz a chamada sem logprobs - a funcionalidade opcional NUNCA deve
        derrubar a geração do laudo principal.
        """
        try:
            return await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=LaudoIA,
                    response_logprobs=True,
                    logprobs=1,
                ),
            )
        except APIError as e:
            if "logprobs" in str(e.message).lower():
                logger.warning(
                    f"Modelo '{self.model_name}' não suporta logprobs "
                    f"('{e.message}') - refazendo chamada sem essa opção. "
                    f"Campo 'confianca_llm' não estará disponível nesta resposta."
                )
                return await self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=LaudoIA,
                    ),
                )
            raise

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
        logprobs, ou se a chamada foi refeita sem essa opção - não deve
        derrubar a resposta principal por causa disso.
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