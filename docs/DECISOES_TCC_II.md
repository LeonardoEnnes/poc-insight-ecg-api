# Decisões Arquiteturais e Achados — TCC2

> Este documento registra as decisões técnicas, correções e achados empíricos da segunda etapa do projeto (TCC2). Complementa [`ARQUITETURA.md`](/docs/ARQUITETURA.md) (decisões do TCC1) sem substituí-lo.

## 1. Motivação

Na avaliação do TCC1 (MoCITeC, nota 9,25), os avaliadores convergiram numa mesma crítica: ausência de dados quantitativos comprovando a eficiência do sistema. Esta etapa responde diretamente a essa lacuna, através de uma correção arquitetural central e sua validação empírica.

## 2. Decisão: Extração determinística de sinal (DSP) antes do LLM

**Problema identificado**: o pipeline original enviava o sinal bruto de ECG (até 30.000 pontos) diretamente ao LLM, pedindo que ele interpretasse ritmo e frequência cardíaca. LLMs são modelos de linguagem, não mecanismos de processamento de sinal digital — a abordagem é estruturalmente suscetível a alucinação numérica.

**Decisão**: introduzida uma camada de Processamento Digital de Sinal (`SignalProcessor` / `NeuroKitSignalProcessor`, via `neurokit2`), responsável por extrair frequência cardíaca (HR) e variabilidade RR (SDNN) de forma determinística, antes de qualquer chamada ao LLM.

**Bugs corrigidos durante a implementação**:
- Conversão de unidade do sinal (`factor`/`origin` do FHIR `SampledData`) nunca era aplicada antes do processamento — corrigido em `fhir_schema.py`.
- `nk.ecg_process()` completo gerava `ZeroDivisionError` em sinal flatline — corrigido separando limpeza (`ecg_clean`), detecção de picos (`ecg_peaks`) e cálculo de frequência (`ecg_rate`) em etapas distintas, com tratamento explícito de qualidade insuficiente.

**Validação**: testes automatizados confirmam, entre outros, que a variabilidade RR (SDNN) do caso AFIB é maior que a do caso Normal — o marcador clínico central da fibrilação atrial, capturado por matemática pura, sem IA.

## 3. Achado: vazamento de rótulo invalidando teste cego

Na primeira rodada de testes reais, o campo `device.display` do payload continha o nome da categoria clínica (ex: "...Fibrilação Atrial (AFIB)"), e a IA citou essa informação como parte de sua justificativa — invalidando o teste como avaliação cega. Corrigido padronizando o campo com um valor genérico em todos os testes de validação.

## 4. Achado: padrão de erro sistemático na decisão de risco do LLM

Com o vazamento corrigido, testes com N=4 (um caso por categoria) revelaram que a IA, mesmo recebendo métricas corretas do DSP, decidia risco de forma livre e incorreta em 50% dos casos (2/4) — especificamente quando a anomalia só se manifestava na variabilidade RR (SDNN), não na frequência cardíaca. Frequência cardíaca é conceito amplamente difundido em texto médico geral; variabilidade RR em janela curta (10s) não possui a mesma base de conhecimento consolidada acessível ao LLM.

**Conclusão**: decisão de risco clínico não deve ficar a cargo do julgamento livre do LLM.

## 5. Decisão: Classificador de Risco determinístico

Implementado `RiskClassifier` (porta) / `ThresholdRiskClassifier` (adapter), que decide o campo `risco` (BAIXO/MEDIO/ALTO) a partir de regras de limiar sobre as métricas do DSP — independente do LLM.

**Trava de segurança**: no `EcgService`, o campo `risco` da resposta final é sempre sobrescrito pelo valor do classificador determinístico, mesmo que o LLM eventualmente sugira outro valor no texto gerado. Defesa em profundidade: prompt + validação de schema + override determinístico.

**Calibração dos limiares** (histórico):
- N=4 (1 por categoria): limiar inicial de SDNN em 90ms, definido empiricamente.
- N=16 (4 por categoria): esse limiar gerou 0% de acurácia em APB — sinal de generalização precipitada. Recalibrado para 40ms (ponto médio entre o maior valor observado em Normal e o menor valor observado em APB). Resultado: 100% de acurácia em N=16.
- N=52 (13 por categoria, majoritariamente dados não usados na calibração): 47/52 (90%) de acurácia geral — Normal 100%, APB 100%, AFIB 92%, AFL 69%.

**Decisão de escopo fechada**: a consequência da recalibração é que APB e AFIB passam a compartilhar classificação MEDIO. Essa equivalência é uma decisão técnica (separabilidade estatística dos dados disponíveis), não uma afirmação de gravidade clínica equivalente entre as duas condições. A hierarquização clínica formal entre elas é responsabilidade do profissional médico e fica registrada como extensão de trabalho futuro, não bloqueante para o escopo desta PoC.

**Achado sobre os erros remanescentes (N=52)**: os 5 casos de erro não são ruído aleatório — revelam uma limitação de escopo do classificador sequencial (frequência cardíaca avaliada antes de variabilidade RR) em apresentações mistas: 1 caso de AFIB com frequência >100bpm (compatível com "fibrilação atrial com resposta ventricular rápida") e 4 casos de AFL com frequência <100bpm mas variabilidade elevada (compatível com "flutter atrial com bloqueio AV variável"). Registrado como limitação conhecida.

## 6. Achado: ruído interpretado como sinal cardíaco válido (teste adversarial)

Um sinal de ruído puro de baixa amplitude (simulando eletrodo desconectado, 10s de gravação) era, na implementação original, aceito com `qualidade_deteccao: OK`, retornando métricas fisiologicamente implausíveis (HR=23.6bpm, SDNN=708.7ms a partir de 4 picos espúrios). Isso poderia gerar um alerta de risco ALTO a partir de ruído puro.

**Correção**: adicionada checagem de plausibilidade fisiológica — número mínimo de picos esperados calculado em função da duração do sinal e de um piso de frequência plausível (25bpm), substituindo o piso absoluto anterior de "menos de 2 picos". Validado sem regressão: ruído é corretamente rejeitado, bradicardia real de fronteira (35bpm, 5 picos em 10s) continua aceita.

## 7. Suíte de testes adversariais

Implementados 9 testes cobrindo: flatline, saturação do ADC, ruído de alta intensidade, eletrodo solto (achado da seção 6), taquicardia e bradicardia extremas (sinais sintéticos via `neurokit2.ecg_simulate`), dados malformados (NaN, infinito) e buffer tecnicamente insuficiente.

## 8. Rate Limiting

Adicionado `SlowAPI` (10 requisições/minuto por IP em todas as rotas que chamam a IA), protegendo contra custo financeiro direto de chamadas de LLM em endpoints sem essa proteção. Handler de exceção (`RateLimitExceeded` → HTTP 429) integrado ao padrão já existente de Exception Handlers globais.

## 9. Testes de qualidade textual (DeepEval)

Adicionados testes complementares aos estruturais: `HallucinationMetric` (fidelidade do laudo às métricas fornecidas) e `GEval` customizado (ausência de morfologia de onda inventada — onda P/QRS/T/segmento ST, nunca disponíveis nas métricas do DSP).

**Achados metodológicos durante a implementação**:
- **Instabilidade de semântica de biblioteca**: a documentação oficial do DeepEval e o comportamento da versão instalada (`4.2.0`) divergiam quanto à direção da métrica de alucinação (menor=melhor vs. maior=melhor) no mesmo período. Resolvido fixando a versão exata testada e reescrevendo o teste para medir e imprimir score/razão manualmente, em vez de confiar cegamente na interpretação automática — tornando o resultado auditável independente da versão.
- **Falso positivo por contexto de teste incompleto**: uma primeira versão do teste fornecia ao avaliador (LLM-as-judge) apenas as métricas numéricas como contexto, omitindo outros dados que o LLM de produção realmente recebe (cobertura da análise, total de pontos). Isso gerava falsos positivos de "alucinação" para informação que na verdade era legítima. Corrigido replicando o contexto completo real no teste.
- **Critério de avaliação calibrado incorretamente**: um critério de G-Eval formulado como "basear-se EXCLUSIVAMENTE nas métricas" penalizava interpretação categórica esperada do LLM (ex: classificar uma frequência como "normal"). Refinado para focar especificamente no guardrail real (invenção de morfologia de onda), sem penalizar narrativa legítima.
- **Descontinuação de modelo sem aviso**: o modelo inicialmente usado como avaliador (`gemini-2.0-flash-001`) foi descontinuado pela Google durante o desenvolvimento, retornando erro 404. A própria API indicou o modelo de substituição na mensagem de erro.
- **Restrição operacional de cota**: a API gratuita do Gemini permite poucas requisições diárias por modelo — rodar a suíte de qualidade junto com o restante dos testes pode facilmente estourar a cota (erro 429). Por isso, os testes de `tests/quality/` são executados isoladamente, não em todo push de CI (ver README).

## 10. Limitações conhecidas e trabalho futuro (consolidado)

- Validação estatística formal (sensibilidade/especificidade com significância) contra dataset anotado em maior escala (MIT-BIH/PTB-XL) permanece pendente.
- Hierarquização clínica formal de severidade entre condições (particularmente APB vs. AFIB) depende de revisão por profissional médico.
- Refinamento do classificador de risco para capturar apresentações mistas de frequência e variabilidade (achado da seção 5) é candidato a evolução futura (ex: classificador multivariado).
- Validação com conjunto de dados totalmente independente do conjunto de calibração ainda não foi realizada em escala.