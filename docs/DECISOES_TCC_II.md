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

**Análise formal em Precision/Recall/F1**: reformulando a validação N=52 no vocabulário padrão de avaliação de classificadores (tratando o nível de risco como classe-alvo):

| Classe (risco) | Precisão | Recall | F1 |
|---|---|---|---|
| BAIXO | 1,000 | 1,000 | 1,000 |
| MEDIO | 0,862 | 0,962 | 0,909 |
| ALTO | 0,900 | 0,692 | 0,783 |
| **Acurácia geral / Macro F1** | | | **0,904 / 0,897** |

O recall mais baixo está na classe ALTO (0,692) — ou seja, o sistema erra mais por **subestimar** risco alto (falso negativo) do que por superestimá-lo. Esse viés é relevante clinicamente e está registrado como ponto de atenção para refinamento futuro.

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

## 10. Decisão: Nomeação de padrão clínico sugerido (sem afirmação diagnóstica)

**Motivação**: a versão inicial do laudo classificava risco (BAIXO/MEDIO/ALTO) sem nomear a condição clínica associada. Avaliou-se que nomear a suspeita, preservando a incerteza quando presente, agrega valor sem comprometer a segurança do guardrail de "nunca diagnosticar".

**Implementação**: o `ThresholdRiskClassifier` passou a retornar também um campo `padrao_sugerido`, determinístico, derivado das mesmas métricas (HR, SDNN) já usadas na decisão de risco. O LLM apenas narra esse padrão, com instrução explícita de preservar qualquer ressalva de incerteza nele contida.

**Achado da sobreposição APB/AFIB estendido à nomeação**: a mesma limitação de separabilidade estatística identificada na seção 5 se replica aqui — análise da distribuição real de SDNN em N=52 mostrou que 2/13 casos de APB ultrapassam 100ms e 7/13 casos de AFIB ficam abaixo de 150ms, uma sobreposição significativa. Um segundo limiar arbitrário para "escolher" entre as duas condições criaria falsa precisão não sustentada pelos dados. **Decisão**: nos casos de sobreposição, o sistema nomeia ambas as possibilidades explicitamente (ex.: "compatível com extrassístole atrial ou fibrilação atrial — distinção não sustentada apenas pelas métricas disponíveis"), em vez de escolher uma de forma arbitrária.

## 11. Achado: confiança via logprobs — limitação de plataforma, não de modelo

**Contexto**: como extensão de confiança complementar à derivada do DSP, foi implementada uma segunda camada de confiança baseada em `avg_logprobs` (probabilidade média dos tokens gerados pelo LLM), habilitada via `response_logprobs=True` na chamada ao Gemini.

**Achado**: ao testar em produção, a chamada retornou erro da própria API: `"Logprobs is not enabled for this model"`. Investigação identificou que essa não é uma limitação do modelo específico escolhido, mas sim da **plataforma**: a Gemini API pública (`generativelanguage.googleapis.com`, acessada via `genai.Client(api_key=...)`, usada neste projeto) não oferece suporte a logprobs em nenhum modelo testado pela comunidade de desenvolvedores (relatos consistentes em `gemini-1.5-flash-002`, `gemini-2.0-flash`, `gemini-2.5-flash`). O suporte a essa funcionalidade existe apenas na **Vertex AI** (a API empresarial do Google Cloud, que exige projeto GCP, billing e autenticação via service account — infraestrutura distinta da usada neste projeto).

**Decisão**: a chamada à IA foi reestruturada com fallback gracioso (`_gerar_com_fallback_logprobs`) — se a chamada com logprobs falhar especificamente por essa causa, a requisição é refeita sem essa opção, preservando a geração do laudo principal. A funcionalidade de confiança via logprobs permanece implementada e documentada, mas inativa na plataforma gratuita utilizada neste projeto. Migrar para Vertex AI apenas para habilitar essa funcionalidade secundária foi avaliado e descartado, dado o custo de infraestrutura (billing obrigatório, reconfiguração de autenticação) desproporcional ao ganho de uma camada de confiança complementar.

**Nota comparativa entre provedores**: ao avaliar um segundo provedor de LLM (ver seção 12), constatou-se que a API de Chat Completions da OpenAI suporta logprobs de forma nativa e documentada (`logprobs=True`, `top_logprobs=N`) na maioria dos modelos GPT, ao contrário da Gemini API pública. A API de Mensagens da Anthropic (Claude), por sua vez, não expõe suporte nativo a logprobs em sua documentação oficial no momento da escrita.

## 12. Segundo provedor de LLM (em avaliação)

Registrado como extensão em andamento: implementação de um segundo `LLMProvider` (candidatos avaliados: OpenAI, Claude), aproveitando o Strategy Pattern já existente (`AIFactory`), com dois objetivos — (a) validar empiricamente o desacoplamento arquitetural já defendido desde o TCC1, e (b) permitir comparação direta de comportamento entre provedores sobre o mesmo conjunto de dados de validação.

## 13. Limitações conhecidas e trabalho futuro (consolidado)

- Validação estatística formal (sensibilidade/especificidade com significância) contra dataset anotado em maior escala (MIT-BIH/PTB-XL) permanece pendente.
- Hierarquização clínica formal de severidade entre condições (particularmente APB vs. AFIB) depende de revisão por profissional médico.
- Refinamento do classificador de risco para capturar apresentações mistas de frequência e variabilidade (achado da seção 5) é candidato a evolução futura (ex: classificador multivariado).
- Validação com conjunto de dados totalmente independente do conjunto de calibração ainda não foi realizada em escala.
- Confiança via logprobs implementada mas inativa na plataforma atual (ver seção 11) — candidata a reativação caso o projeto migre para Vertex AI ou adote um provedor com suporte nativo (ex: OpenAI).
- Tempo de processamento por exame ainda não foi medido e reportado — item pendente e de baixo custo de implementação.