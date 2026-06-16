from google import genai
from google.genai import types
from pydantic import BaseModel
from app.infrastructure.ia.base import LLMProvider
from app.core.prompts import get_ecg_analysis_prompt
import json

# schema de resposta para travar a resposta, previnindo alucinação
class LaudoIA(BaseModel):
    ritmo: str
    anomalias_detectadas: bool
    descricao_tecnica: str
    risco: str
    recomendacao: str

class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model_name: str):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    async def analisar_ecg(self, sinal_contexto: str, metadados: dict) -> dict:
        prompt = get_ecg_analysis_prompt(sinal_contexto, metadados)
        
        try:
            response = await self.client.aio.models.generate_content( 
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=LaudoIA,
                ),
            )
            return json.loads(response.text)
            
        except Exception as e:
            raise RuntimeError(f"Falha na IA: {str(e)}")