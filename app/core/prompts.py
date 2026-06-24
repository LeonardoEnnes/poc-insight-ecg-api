def get_ecg_analysis_prompt(sinal_contexto: str, metadados: dict) -> str:
    """Gera o contexto clínico padronizado e com guardrails éticos para análise do LLM."""

    device = metadados.get("device", "Desconhecido")
    period_ms = metadados.get("period_ms", "Desconhecido")
    total_pontos = metadados.get("total_pontos_analisados", "Desconhecido")
    tipo_analise = metadados.get("tipo_analise", "COMPLETA")

    return f"""Você atua como um sistema de suporte à decisão clínica
para apoio à interpretação de exames de eletrocardiograma (ECG).

Sua tarefa é analisar uma série temporal de ECG extraída em formato FHIR
e gerar uma síntese técnica preliminar notificando o medico.

O objetivo é auxiliar a triagem e destacar padrões potencialmente relevantes.
O diagnóstico definitivo permanece sob responsabilidade do profissional médico.

CONTEXTO TÉCNICO DO EXAME:
- Aparelho de Origem: {device}
- Taxa de Amostragem: {period_ms} ms
- Total de Pontos Analisados: {total_pontos}
- Cobertura da Análise: {tipo_analise}

DIRETRIZES DE ANÁLISE (GUARDRAILS):

1. Avaliação do Fatiamento
Considere a cobertura da análise.
Caso seja PARCIAL, interprete como uma janela temporal
e não conclua ausência de atividade cardíaca.

2. Interpretação Temporal
Utilize a taxa de amostragem para auxiliar
na estimativa de frequência cardíaca
e observação de padrões morfológicos.

3. Restrição de Inferência
Baseie a resposta apenas nos dados fornecidos.
Caso exista ruído excessivo, informe isso explicitamente.

4. Limitação Clínica
Apresente resultados como hipóteses preliminares
e reforce a necessidade de correlação clínica, Sua tarefa é notificar.

5. Classificação de Risco
O campo "risco" deve conter apenas:
BAIXO, MEDIO ou ALTO.

DADOS BRUTOS DO SINAL:
[{sinal_contexto}]
"""