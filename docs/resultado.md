# Registro de Resultado — Teste de Integração: Nomeação de Padrão Clínico (Caso AFIB)

> Documento de registro pontual, para incorporação futura ao texto do TCC2 (seção de Resultados ou Apêndice de evidências). Complementa `docs/DECISOES_TCC2.md` (seção 10 — Decisão: Nomeação de padrão clínico sugerido).

## Contexto do teste

Este registro documenta o primeiro teste de integração completo (ponta a ponta, via API real do Gemini) da funcionalidade de nomeação determinística de padrão clínico, implementada como extensão do `RiskClassifier`. O objetivo do teste foi confirmar que:

1. A funcionalidade opera corretamente no pipeline completo (DSP → RiskClassifier → prompt → LLM), não apenas em testes unitários isolados;
2. A instrução de preservação de incerteza (guardrail 4 do prompt) é respeitada pelo LLM ao narrar um caso de sobreposição estatística conhecida (ver `docs/DECISOES_TCC2.md`, seção 10);
3. A correção de consistência interna do campo `ritmo` (guardrail 7) permanece estável.

## Payload utilizado

Sinal real da categoria AFIB, do conjunto de referência do IF4Health (arquivo correspondente à mesma amostra documentada na seção 5 de `DECISOES_TCC2.md`), com `device.display` genérico (sem vazamento de rótulo), 3.600 pontos, período de amostragem de 2,7778 ms (360 Hz), `factor=1.0` e `origin=0.0`.

## Métricas de referência (calculadas pelo DSP, ground truth determinístico)

| Métrica | Valor |
|---|---|
| Frequência cardíaca média (HR) | 85,3 bpm |
| Variabilidade RR (SDNN) | 98,0 ms |
| Picos R detectados | — (não registrado nesta rodada, ver CSV de validação em lote para o caso completo) |
| Qualidade de detecção | OK |
| Risco determinado (`ThresholdRiskClassifier`) | MEDIO |
| Padrão sugerido (`ThresholdRiskClassifier`) | "Padrão compatível com extrassístole atrial ou fibrilação atrial (variabilidade RR elevada) - distinção entre as duas não é sustentada apenas pelas métricas de frequência e variabilidade disponíveis nesta análise." |

**Nota metodológica**: o SDNN de 98,0 ms está na faixa de sobreposição estatística entre APB e AFIB identificada em N=52 (ver `DECISOES_TCC2.md`, seções 5 e 10) — este caso foi, portanto, um teste deliberadamente desafiador para a funcionalidade, não um caso trivial.

## Laudo gerado pela IA (Gemini, resposta real via API)

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

## Verificação ponto a ponto

| Critério verificado | Esperado | Obtido | Conformidade |
|---|---|---|---|
| Frequência cardíaca citada | 85,3 bpm (idêntica ao DSP) | 85,3 bpm | ✅ Fidelidade numérica total |
| Variabilidade RR citada | 98,0 ms (idêntica ao DSP) | 98,0 ms | ✅ Fidelidade numérica total |
| Classificação de risco | MEDIO (decisão do `RiskClassifier`) | MEDIO | ✅ Trava de segurança respeitada |
| Consistência do campo `ritmo` | Deve refletir anomalia (guardrail 7) | "Irregular" | ✅ Sem recorrência do bug de inconsistência identificado anteriormente (laudo anterior chegou a retornar "Regular" em caso análogo) |
| Preservação da incerteza no padrão sugerido | Deve manter a ressalva de não-distinção entre APB/AFIB | Texto reproduzido de forma praticamente literal, incluindo a ressalva | ✅ Guardrail 4 respeitado com fidelidade |
| Ausência de invenção de morfologia de onda | Não deve mencionar onda P/QRS/T/segmento ST | Nenhuma menção | ✅ |
| Recomendação clínica apropriada | Deve reforçar necessidade de avaliação médica, sem afirmação diagnóstica definitiva | "Recomenda-se a correlação clínica imediata... para... confirmação diagnóstica" | ✅ Diagnóstico apresentado como pendente de confirmação profissional |

## Conclusão do registro

Este teste demonstra que a funcionalidade de nomeação de padrão clínico opera corretamente mesmo no cenário mais desafiador identificado na validação estatística (sobreposição APB/AFIB) — o sistema comunica explicitamente a incerteza estatística real, em vez de arbitrar uma escolha não sustentada pelos dados. Este comportamento é consistente com o princípio de design central do projeto: o LLM narra decisões e limitações já determinadas por processamento matemático, nunca substituindo o julgamento clínico do profissional responsável.

**Status**: primeiro teste de integração bem-sucedido da funcionalidade. Recomenda-se repetir este registro para os demais casos (Normal, APB, AFL) antes da consolidação final da seção de Resultados do TCC2, de forma a compor um conjunto completo de evidências qualitativas por categoria.