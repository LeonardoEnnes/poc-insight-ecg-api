import os
import pytest
from deepeval import assert_test
from deepeval.metrics import HallucinationMetric, GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams
from gemini_judge_model import GeminiJudgeModel

API_KEY = os.getenv("AI_API_KEY", os.getenv("GEMINI_API_KEY", ""))

judge_model = GeminiJudgeModel(api_key=API_KEY)

# ---------------------------------------------------------------------------
# Casos reais já validados no projeto (rodada final de regressão, N=4,
# API real do Gemini) - reaproveitados aqui como corpus de avaliação de
# qualidade textual, complementando a validação estrutural já feita.
# ---------------------------------------------------------------------------

CASOS_REAIS = [
    {
        "nome": "normal",
        "metricas_dsp": (
            "Aparelho de Origem: Monitor ECG genérico. Total de Pontos Analisados: 3600. "
            "Cobertura da Análise: COMPLETA. "
            "Frequência cardíaca média: 82.3 bpm. "
            "Variabilidade RR (SDNN): 25.1 ms. "
            "Picos R detectados: 14. Qualidade da detecção: OK. "
            "Risco determinado: BAIXO - dentro das faixas de referência adotadas."
        ),
        "laudo_gerado": (
            "O exame apresenta uma cobertura completa com análise de 3600 pontos "
            "e qualidade de detecção OK. A frequência cardíaca média de 82.3 bpm "
            "e a variabilidade RR (SDNN) de 25.1 ms situam-se dentro dos parâmetros "
            "de normalidade esperados para o repouso. Não foram identificadas "
            "irregularidades significativas nos picos R detectados durante o "
            "período de monitoramento."
        ),
    },
    {
        "nome": "apb",
        "metricas_dsp": (
            "Aparelho de Origem: Monitor ECG genérico. Total de Pontos Analisados: 3600. "
            "Cobertura da Análise: COMPLETA. "
            "Frequência cardíaca média: 75.7 bpm. "
            "Variabilidade RR (SDNN): 66.8 ms. "
            "Picos R detectados: 12. Qualidade da detecção: OK. "
            "Risco determinado: MEDIO - SDNN acima do limiar de referência (40ms)."
        ),
        "laudo_gerado": (
            "O exame, realizado com cobertura completa e qualidade de detecção OK, "
            "apresentou frequência cardíaca média de 75.7 bpm. A métrica SDNN de "
            "66.8 ms foi identificada como superior ao limiar de referência de 40 ms, "
            "o que indica uma variabilidade do intervalo RR elevada. Embora a "
            "frequência cardíaca esteja dentro da faixa de normalidade, a "
            "instabilidade na variabilidade sinaliza potencial irregularidade no ritmo."
        ),
    },
    {
        "nome": "afl",
        "metricas_dsp": (
            "Aparelho de Origem: Monitor ECG genérico. Total de Pontos Analisados: 3600. "
            "Cobertura da Análise: COMPLETA. "
            "Frequência cardíaca média: 129.4 bpm. "
            "Variabilidade RR (SDNN): 15.3 ms. "
            "Picos R detectados: 21. Qualidade da detecção: OK. "
            "Risco determinado: ALTO - frequência cardíaca fora da faixa de "
            "referência [50-100] bpm."
        ),
        "laudo_gerado": (
            "O exame apresenta uma frequência cardíaca média de 129.4 bpm, valor "
            "que excede a faixa de referência fisiológica padrão de 50-100 bpm. "
            "A variabilidade RR (SDNN) foi de 15.3 ms com 21 picos R detectados "
            "em uma cobertura completa de 3600 pontos. A qualidade da detecção "
            "foi considerada satisfatória, permitindo a identificação da "
            "taquicardia como achado principal."
        ),
    },
    {
        "nome": "afib",
        "metricas_dsp": (
            "Aparelho de Origem: Monitor ECG genérico. Total de Pontos Analisados: 3600. "
            "Cobertura da Análise: COMPLETA. "
            "Frequência cardíaca média: 93.2 bpm. "
            "Variabilidade RR (SDNN): 112.3 ms. "
            "Picos R detectados: 15. Qualidade da detecção: OK. "
            "Risco determinado: MEDIO - SDNN acima do limiar de referência (40ms)."
        ),
        "laudo_gerado": (
            "O exame, realizado com cobertura completa e qualidade de detecção OK, "
            "apresentou uma frequência cardíaca média de 93.2 bpm. A análise da "
            "variabilidade RR revelou um desvio padrão (SDNN) de 112.3 ms, valor "
            "que excede o limiar de referência de 40 ms, indicando uma irregularidade "
            "nos intervalos entre os batimentos, apesar da frequência cardíaca "
            "estar dentro da faixa de normalidade."
        ),
    },
]


def build_test_case(caso: dict) -> LLMTestCase:
    return LLMTestCase(
        input=f"Gere um laudo técnico a partir destas métricas: {caso['metricas_dsp']}",
        actual_output=caso["laudo_gerado"],
        context=[caso["metricas_dsp"]],
    )


@pytest.mark.parametrize("caso", CASOS_REAIS, ids=[c["nome"] for c in CASOS_REAIS])
def test_laudo_nao_alucina_alem_das_metricas_fornecidas(caso):
    """
    HallucinationMetric: verifica se o laudo gerado contradiz ou extrapola
    além do que está sustentado pelas métricas do DSP (context/ground truth).
    """
    test_case = build_test_case(caso)
    metric = HallucinationMetric(threshold=0.7, model=judge_model)

    metric.measure(test_case)
    print(f"\n[{caso['nome']}] score={metric.score:.3f} | reason={metric.reason}")

    assert metric.is_successful(), (
        f"Caso '{caso['nome']}' falhou na verificação de alucinação. "
        f"Score={metric.score:.3f}, razão: {metric.reason}"
    )


@pytest.mark.parametrize("caso", CASOS_REAIS, ids=[c["nome"] for c in CASOS_REAIS])
def test_laudo_nao_inventa_morfologia_de_onda(caso):
    """
    G-Eval customizado: penaliza especificamente a invenção de morfologia
    de onda (P, QRS, T, segmento ST)
    """
    test_case = build_test_case(caso)
    metric = GEval(
        name="Ausência de morfologia de onda inventada",
        criteria=(
            "O texto de saída (actual_output) NÃO deve mencionar ou descrever "
            "morfologia de onda específica (onda P, complexo QRS, onda T, "
            "segmento ST, amplitude ou duração dessas ondas) - essa informação "
            "nunca está disponível nas métricas fornecidas (apenas frequência "
            "cardíaca, variabilidade RR/SDNN, contagem de picos R e qualidade "
            "de detecção), então qualquer menção a essas ondas específicas "
            "seria invenção. Interpretação categórica das métricas fornecidas "
            "(ex: classificar frequência como normal/elevada, ou variabilidade "
            "como elevada) É esperada e não deve ser penalizada - o critério "
            "é APENAS sobre morfologia de onda específica não fornecida."
        ),
        evaluation_params=[
            SingleTurnParams.INPUT,
            SingleTurnParams.ACTUAL_OUTPUT,
            SingleTurnParams.CONTEXT,
        ],
        threshold=0.7,
        model=judge_model,
    )
    assert_test(test_case, [metric])