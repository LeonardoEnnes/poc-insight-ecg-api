import json
from deepeval.models.base_model import DeepEvalBaseLLM
from google import genai


class GeminiJudgeModel(DeepEvalBaseLLM):
    """
    Wrapper do Gemini como modelo avaliador (LLM-as-judge) do DeepEval.
    Usa um modelo mais barato/rápido para julgamento, já que a tarefa de
    avaliar é mais simples que a de gerar o laudo original.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-3.6-flash"):
        self.model_name = model_name
        self.client = genai.Client(api_key=api_key)

    def load_model(self):
        return self.client

    def generate(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )
        return response.text

    async def a_generate(self, prompt: str) -> str:
        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )
        return response.text

    def get_model_name(self) -> str:
        return f"Gemini Judge ({self.model_name})"