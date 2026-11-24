"""
Teste unitário do OpenAIProvider - verifica a lógica de extração de
confiança via logprobs de forma isolada, sem chamar a API real
(evita custo/latência em testes automatizados de CI).
"""
import math
from unittest.mock import MagicMock
from app.infrastructure.ia.openai_provider import OpenAIProvider


def test_extrai_confianca_media_com_logprobs_validos():
    """Confere o cálculo correto da média de probabilidade a partir de logprobs simulados."""
    provider = OpenAIProvider(api_key="dummy", model_name="gpt-4o-mini")

    token1 = MagicMock(logprob=-0.1)
    token2 = MagicMock(logprob=-0.2)
    token3 = MagicMock(logprob=-0.3)

    response = MagicMock()
    response.choices = [MagicMock(logprobs=MagicMock(content=[token1, token2, token3]))]

    resultado = provider._extrair_confianca_media(response)

    media_esperada = round(math.exp((-0.1 + -0.2 + -0.3) / 3), 4)
    assert resultado == media_esperada


def test_extrai_confianca_media_retorna_none_sem_logprobs():
    """Se a resposta não trouxer logprobs (ex: parâmetro não passado), retorna None sem quebrar."""
    provider = OpenAIProvider(api_key="dummy", model_name="gpt-4o-mini")

    response = MagicMock()
    response.choices = [MagicMock(logprobs=MagicMock(content=None))]

    resultado = provider._extrair_confianca_media(response)

    assert resultado is None


def test_extrai_confianca_media_retorna_none_em_erro_inesperado():
    """Qualquer erro inesperado na extração deve ser absorvido, não propagado."""
    provider = OpenAIProvider(api_key="dummy", model_name="gpt-4o-mini")

    response = MagicMock()
    response.choices = []  # índice [0] vai estourar IndexError

    resultado = provider._extrair_confianca_media(response)

    assert resultado is None