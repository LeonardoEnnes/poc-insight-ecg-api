# Registro de Resultado — Comparação Gemini vs. OpenAI (Mesmo Sinal)

> Complementa `docs/DECISOES_TCC2.md` (seção 12 — Segundo provedor de LLM). Primeira comparação válida "mesmo estímulo, dois provedores", após correção de confusão inicial de arquivos entre testes.

## Contexto

Ambos os provedores foram testados com o **mesmo payload exato** — sinal real da categoria AFIB do conjunto de referência do IF4Health, `device.display` genérico (sem vazamento de rótulo), métricas do DSP idênticas em ambos os testes (confirmando que o mesmo sinal de entrada foi usado):

| Métrica (DSP, ground truth) | Valor |
|---|---|
| Frequência cardíaca média (HR) | 85,3 bpm |
| Variabilidade RR (SDNN) | 98,0 ms |
| Risco determinado (`ThresholdRiskClassifier`) | MEDIO |
| Padrão sugerido (`ThresholdRiskClassifier`) | "Padrão compatível com extrassístole atrial ou fibrilação atrial (variabilidade RR elevada) - distinção entre as duas não é sustentada apenas pelas métricas de frequência e variabilidade disponíveis nesta análise." |

## Laudos gerados

### Gemini (`gemini-3.5-flash`)

```json
{
  "ritmo": "Irregular",
  "anomalias_detectadas": true,
  "descricao_tecnica": "A análise realizada sobre 3600 pontos com cobertura completa demonstrou uma frequência cardíaca média de 85.3 bpm. A variabilidade RR (SDNN) calculada em 98.0 ms encontra-se significativamente acima do limiar de referência clínico de 40 ms, o que indica instabilidade no intervalo entre os batimentos, mesmo com a frequência cardíaca dentro da faixa de normalidade.",
  "padrao_sugerido": "Padrão compatível com extrassístole atrial ou fibrilação atrial (variabilidade RR elevada) - distinção entre as duas não é sustentada apenas pelas métricas de frequência e variabilidade disponíveis nesta análise.",
  "risco": "MEDIO",
  "recomendacao": "A classificação de risco médio é atribuída devido à elevada variabilidade RR detectada. Recomenda-se a correlação clínica imediata por um profissional médico, incluindo a possibilidade de realização de ECG de 12 derivações para análise morfológica e confirmação diagnóstica."
}
```

*(campo `confianca_llm` ausente — Gemini API pública não suporta logprobs, ver `DECISOES_TCC2.md`, seção 11)*

### OpenAI (`gpt-4o-mini`)

```json
{
  "ritmo": "Irregular",
  "anomalias_detectadas": true,
  "descricao_tecnica": "O exame de eletrocardiograma foi realizado com uma cobertura completa, utilizando um aparelho de 12 canais e uma taxa de amostragem de 2.7778 ms. Foram analisados 3600 pontos, resultando em uma frequência cardíaca média de 85.3 bpm e uma variabilidade RR (SDNN) de 98.0 ms. A qualidade da detecção foi considerada satisfatória, evidenciando uma análise confiável dos dados obtidos. A variabilidade RR foi acima do limiar de referência, o que sugere a possibilidade de irregularidades no ritmo cardíaco, embora a frequência cardíaca permaneça dentro dos limites normais.",
  "padrao_sugerido": "Padrão compatível com extrassístole atrial ou fibrilação atrial (variabilidade RR elevada) - distinção entre as duas não é sustentada apenas pelas métricas de frequência e variabilidade disponíveis nesta análise.",
  "risco": "MEDIO",
  "recomendacao": "Recomenda-se que um médico especialista realize a correlação clínica dos achados com a história do paciente e outros dados clínicos, a fim de determinar a necessidade de investigações adicionais ou intervenções.",
  "confianca_llm": 0.7094
}
```

## Análise comparativa

| Critério | Gemini | OpenAI | Observação |
|---|---|---|---|
| Fidelidade numérica (HR/SDNN) | ✅ Exata | ✅ Exata | Ambos fiéis ao DSP, sem alucinação |
| Consistência `ritmo` × `anomalias_detectadas` × `risco` | ✅ Consistente | ✅ Consistente | Guardrail 7 respeitado por ambos nesta rodada |
| Padrão sugerido preservando incerteza | ✅ Reproduzido quase literalmente | ✅ Reproduzido quase literalmente | Guardrail 4 respeitado por ambos |
| Nível de detalhe técnico da descrição | Menor extensão, foco direto no limiar ultrapassado | Maior extensão, menciona explicitamente "qualidade da detecção satisfatória" (informação disponível no contexto, mas não obrigatória) | Diferença estilística, não de precisão |
| Tom da recomendação | Sugere ECG de 12 derivações especificamente | Recomendação mais genérica ("investigações adicionais") | Gemini foi mais específico tecnicamente nesta instância |
| Confiança via logprobs (`confianca_llm`) | Indisponível (limitação de plataforma) | 0,7094 | Diferencial funcional real da OpenAI nesta arquitetura |

## Achado adicional (de rodada anterior, não reproduzido nesta comparação direta)

Em um teste anterior com um arquivo diferente (não o mesmo estímulo desta comparação), a OpenAI retornou `anomalias_detectadas: false` simultaneamente com `ritmo: "Irregular"` e `risco: MEDIO` — uma inconsistência interna semelhante à corrigida anteriormente pelo guardrail 7, mas manifestada em um campo diferente (`anomalias_detectadas` em vez de `ritmo`). Nesta comparação de mesmo estímulo, ambos os provedores mantiveram consistência total. **Isso sugere que a inconsistência anterior pode ser variabilidade pontual do modelo, não uma falha sistemática do guardrail** — avaliação mais conclusiva requer N maior por provedor, registrada como próxima etapa da comparação sistemática (rodar os mesmos N casos de validação em ambos os provedores).

## Conclusão preliminar

Com N=1 estímulo idêntico, ambos os provedores produziram laudos clinicamente equivalentes em conteúdo, fiéis às métricas determinísticas e obedientes aos guardrails de risco e padrão sugerido. A OpenAI apresenta uma vantagem funcional concreta nesta arquitetura: suporte nativo a logprobs, habilitando a camada de confiança que permanece inativa no Gemini por limitação de plataforma (não de modelo). Conclusões sobre qual provedor é mais confiável em escala exigem repetir esta comparação sobre o conjunto de validação completo (N=52), não apenas um caso — registrado como próximo passo da comparação sistemática entre provedores.