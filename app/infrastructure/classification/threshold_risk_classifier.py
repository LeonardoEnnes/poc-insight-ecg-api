class ThresholdRiskClassifier:
    """
    Classificador de risco por threshold determinístico.

    STATUS: valor definitivo para esta fase do projeto (TCC2 - Prova de
    Conceito). Calibrado empiricamente a partir de 16 casos observados
    (4 por categoria: Normal, APB, AFL, AFIB), com base na separação
    estatística real entre as distribuições de SDNN:

        Normal: 21.6 - 32.5 ms (N=4)
        APB:    47.4 - 75.1 ms (N=4)
        AFIB:   112.3 - 346.9 ms (N=4)

    O limiar HRV_SDNN_ELEVADO_MS (40ms) foi fixado no ponto médio entre o
    maior valor observado em Normal e o menor valor observado em APB,
    validado com 100% de acurácia sobre os 16 casos disponíveis.

    DECISÃO DE ESCOPO: a equivalência de severidade entre APB e AFIB
    (ambos classificados como MEDIO neste classificador) é uma decisão
    técnica baseada em separabilidade estatística dos dados disponíveis,
    não uma afirmação de equivalência clínica de gravidade entre as duas
    condições. A responsabilidade por validar, ajustar ou hierarquizar
    clinicamente esses níveis de risco é do profissional médico - este
    sistema atua estritamente como ferramenta de apoio à decisão, nunca
    como fonte de diagnóstico definitivo (consistente com o escopo e as
    limitações já declaradas no TCC1, seção 4.5).

    Esta calibração é considerada fechada para o escopo do TCC2. Trabalhos
    futuros podem revisitar os limiares com validação estatística formal
    em maior escala (dataset anotado por especialista, tipo MIT-BIH/
    PTB-XL) e com revisão clínica formal da hierarquia de severidade -
    ambos registrados como extensões futuras, não como pendências
    bloqueantes desta etapa.
    """

    HR_BRADICARDIA_BPM = 50
    HR_TAQUICARDIA_BPM = 100
    HRV_SDNN_ELEVADO_MS = 40

    def classify(self, features: dict) -> dict:
        hr = features.get("hr_medio_bpm")
        hrv = features.get("hrv_sdnn_ms")
        qualidade = features.get("qualidade_deteccao")

        if qualidade != "OK" or hr is None:
            return {
                "risco_determinado": "INDETERMINADO",
                "justificativa_classificacao": (
                    "Qualidade de detecção insuficiente para classificação "
                    "de risco confiável - sinal sem picos R detectáveis "
                    "em número suficiente."
                ),
            }

        if hr > self.HR_TAQUICARDIA_BPM or hr < self.HR_BRADICARDIA_BPM:
            return {
                "risco_determinado": "ALTO",
                "justificativa_classificacao": (
                    f"Frequência cardíaca média ({hr} bpm) fora da faixa "
                    f"de referência [{self.HR_BRADICARDIA_BPM}-{self.HR_TAQUICARDIA_BPM}] bpm."
                ),
            }

        if hrv is not None and hrv > self.HRV_SDNN_ELEVADO_MS:
            return {
                "risco_determinado": "MEDIO",
                "justificativa_classificacao": (
                    f"Variabilidade RR (SDNN = {hrv} ms) acima do limiar de "
                    f"referência ({self.HRV_SDNN_ELEVADO_MS} ms), sugerindo "
                    f"possível irregularidade de ritmo, apesar de frequência "
                    f"cardíaca dentro da normalidade."
                ),
            }

        return {
            "risco_determinado": "BAIXO",
            "justificativa_classificacao": (
                f"Frequência cardíaca ({hr} bpm) e variabilidade RR "
                f"({hrv} ms) dentro das faixas de referência adotadas."
            ),
        }