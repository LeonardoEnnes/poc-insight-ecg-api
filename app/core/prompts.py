def get_ecg_analysis_prompt(sinal_contexto: str, metadados: dict) -> str:
    """Gera o contexto clínico padronizado para análise da IA."""
    return f"""
    Retorne ok se conseguir ler os sinais e me retorne um laudo simplificado so para verificar se 
    voce consegue ler os dados, faça isso nesse formato:
    
    contexto:
    - Aparelho: {metadados.get('dispositivo')}
    - Período de amostragem: {metadados.get('periodo_ms')} ms
    - Total de pontos analisados: {metadados.get('total_pontos')}
    
    DADOS BRUTOS DO SINAL (Amplitude):
    [{sinal_contexto}]
    """