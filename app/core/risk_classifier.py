from typing import Protocol


class RiskClassifier(Protocol):
    """
    Porta para classificação determinística de risco clínico.

    Responsável por decidir o campo 'risco' a partir de métricas já
    calculadas pelo DSP (SignalProcessor) - NUNCA a partir de texto
    livre ou julgamento do LLM. O LLM consome o resultado desta
    classificação apenas para narrar/contextualizar, não para decidir.
    """

    def classify(self, features: dict) -> dict:
        """
        Recebe o dicionário de features já extraídas pelo SignalProcessor
        (hr_medio_bpm, hrv_sdnn_ms, n_picos_detectados, qualidade_deteccao)
        e retorna a decisão de risco com a justificativa que a originou.
        """
        ...