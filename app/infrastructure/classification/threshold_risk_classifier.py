class ThresholdRiskClassifier:
    """
    Classificador de risco por threshold determinístico.

    STATUS: valor definitivo para esta fase do projeto (TCC2 - Prova de
    Conceito). Calibrado empiricamente a partir de 52 casos observados
    (13 por categoria: Normal, APB, AFL, AFIB), com base na separação
    estatística real entre as distribuições de SDNN:

        Normal: 21.6 - 38.2 ms  (N=13)
        APB:    47.4 - 156.4 ms (N=13)
        AFIB:   98.0 - 346.9 ms (N=13)

    O limiar HRV_SDNN_ELEVADO_MS (40ms) separa corretamente Normal de
    APB/AFIB (100% e 100% de acurácia respectivamente). AFL é decidido
    primariamente pela frequência cardíaca.

    DECISÃO DE ESCOPO: a equivalência de severidade entre APB e AFIB
    (ambos classificados como MEDIO) é uma decisão técnica baseada em
    separabilidade estatística, não uma afirmação de equivalência
    clínica de gravidade. A responsabilidade por validar, ajustar ou
    hierarquizar clinicamente esses níveis de risco é do profissional
    médico - este sistema atua estritamente como ferramenta de apoio à
    decisão, nunca como fonte de diagnóstico definitivo.
    """

    HR_BRADICARDIA_BPM = 50
    HR_TAQUICARDIA_BPM = 100
    HRV_SDNN_ELEVADO_MS = 40

    # Limiar acima do qual a variabilidade é tão elevada que, nos dados
    # observados, torna-se mais provável (ainda que não exclusiva) de
    # fibrilação atrial do que de extrassístole isolada. NÃO é um limiar
    # de separação limpa - ver ressalva em _sugerir_padrao().
    HRV_SDNN_MUITO_ELEVADO_MS = 150

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
                "padrao_sugerido": "Não é possível sugerir padrão - qualidade de sinal insuficiente.",
            }

        if hr > self.HR_TAQUICARDIA_BPM or hr < self.HR_BRADICARDIA_BPM:
            return {
                "risco_determinado": "ALTO",
                "justificativa_classificacao": (
                    f"Frequência cardíaca média ({hr} bpm) fora da faixa "
                    f"de referência [{self.HR_BRADICARDIA_BPM}-{self.HR_TAQUICARDIA_BPM}] bpm."
                ),
                "padrao_sugerido": self._sugerir_padrao(hr, hrv),
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
                "padrao_sugerido": self._sugerir_padrao(hr, hrv),
            }

        return {
            "risco_determinado": "BAIXO",
            "justificativa_classificacao": (
                f"Frequência cardíaca ({hr} bpm) e variabilidade RR "
                f"({hrv} ms) dentro das faixas de referência adotadas."
            ),
            "padrao_sugerido": "Ritmo sinusal, sem padrão anômalo sugestivo identificado.",
        }

    def _sugerir_padrao(self, hr: float, hrv: float | None) -> str:
        """
        Sugere, de forma determinística, o padrão clínico mais compatível
        com as métricas observadas - NUNCA um diagnóstico definitivo.

        RESSALVA METODOLÓGICA IMPORTANTE: análise da distribuição real de
        SDNN em N=52 mostrou sobreposição significativa entre APB e AFIB
        (2/13 casos de APB acima de 100ms; 7/13 casos de AFIB abaixo de
        150ms) - portanto, distinguir essas duas condições apenas por um
        segundo limiar de SDNN criaria falsa precisão não sustentada pelos
        dados. Nos casos de sobreposição, o sistema nomeia ambas as
        possibilidades, em vez de escolher uma arbitrariamente.
        """
        if hr > self.HR_TAQUICARDIA_BPM:
            return (
                "Padrão sugestivo de flutter atrial ou taquicardia sustentada "
                "(frequência cardíaca elevada)."
            )
        if hr < self.HR_BRADICARDIA_BPM:
            return "Padrão sugestivo de bradicardia significativa."

        if hrv is not None and hrv > self.HRV_SDNN_MUITO_ELEVADO_MS:
            return (
                "Padrão mais compatível com fibrilação atrial (variabilidade "
                "RR acentuadamente elevada), sem excluir extrassístole atrial."
            )
        if hrv is not None and hrv > self.HRV_SDNN_ELEVADO_MS:
            return (
                "Padrão compatível com extrassístole atrial ou fibrilação "
                "atrial (variabilidade RR elevada) - distinção entre as duas "
                "não é sustentada apenas pelas métricas de frequência e "
                "variabilidade disponíveis nesta análise."
            )
        return "Sem padrão anômalo sugestivo identificado."