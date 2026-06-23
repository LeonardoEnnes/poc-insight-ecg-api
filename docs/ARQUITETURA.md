# Decisões Arquiteturais

Este documento detalha o raciocínio por trás do design de software da aplicação. O objetivo desta arquitetura não é seguir cegamente um padrão teórico, mas sim garantir **testabilidade, resiliência e baixo acoplamento** através de uma abordagem orientada a dados.

---

## 1. O Paradigma: Arquitetura Hexagonal

Embora o projeto seja inspirado nos conceitos da **Clean Architecture**, a sua implementação prática assemelha-se à **Arquitetura Hexagonal**. 

O sistema é dividido em duas zonas de responsabilidade principais:
* **A Camada de Domínio/Negócio:** Representada pelos diretórios `services` (onde ocorre o fatiamento clínico do sinal do ECG) e `schemas` (validação estrutural). Complementarmente, o diretório `core` armazena as exceções globais e os prompts base. Esta zona é completamente agnóstica em relação à web ou a provedores de IA.
* **Os Adaptadores (Adapters/Infrastructure):** Representados pelos diretórios `routes` (Adaptador de Entrada HTTP/FastAPI) e `infrastructure` (Adaptadores de Saída como a fábrica de IA e os clientes HTTP externos). 

Se, por exemplo, for necessário substituir o Gemini por um modelo hospedado localmente (como o Llama 3) o `EcgService` não sofrerá nenhuma alteração. Basta criar uma nova classe na fábrica de IA (`AIFactory`) que assine o contrato exigido. 

---

## 2. Design Patterns Utilizados

Foram aplicados padrões de projeto focados na escalabilidade do código:

* **Factory Pattern:** Implementado na `AIFactory`. Centraliza a complexidade de instanciar clientes de IA (injeção de chaves, mapeamento de modelos), libertando os serviços dessa responsabilidade.
* **Strategy Pattern:** O `EcgService` interage exclusivamente com a interface base `LLMProvider`. O modelo específico (Gemini, por exemplo) executa a análise "por baixo dos panos", tornando o *provider* irrelevante para a regra de negócio.

---

## 3. Pydantic

**A Decisão:**
Nessa arquitetura com FastAPI, foi decidido usar os modelos do **Pydantic** (`app/schemas/fhir_schema.py`) com dupla função: eles validam os dados que chegam da internet e também são usados diretamente pelo núcleo do nosso sistema.

**Justificativa:**
1. **Evitar Código Repetido:** O formato médico HL7 FHIR é gigantesco. Criar classes separadas para converter os dados da web para o sistema interno daria um trabalho enorme de manutenção e não traria vantagens reais pra dentro do projeto.
2. **Escudo de Segurança:** O Pydantic funciona como um guarda-costas. Ele barra dados no formato errado ou corrompidos logo na porta de entrada da API, protegendo o motor da IA de processar "lixo".

---

## 4. Proteção de Contexto e Custos (Sliding Window / Fatiamento)

Os modelos LLM sofrem de perda de contexto quando tem janelas massivas de informação (fenómeno *Lost in the Middle*), e os custos de API escalam rapidamente com o uso intensivo de *tokens*. No contexto dessa POC, foi utilizado o arquivo mock "FHIR-Observation-2-lead" que continha uma série temporal massiva de dados. Se fosse realizado o envio destes dados isso causaria o esgotamento do limite de *tokens* (*Token Limit Exceeded*), ao contrário de exemplo menor que foi processado perfeitamente pela IA.

**A Decisão Tomada:**
Foi implementada uma trava de segurança (`MAX_SIGNAL_POINTS = 5000`), correspondendo a uma janela (aprox. 10 a 15 segundos de exame de repouso). Séries temporais de Holter ou exames massivos sofrem um *crop clínico* inicial automático. Os metadados da requisição sinalizam dinamicamente a IA que se trata de uma "análise parcial", protegendo tanto a precisão quanto a previsibilidade financeira do sistema. 

**Trabalho Futuro:** 
Caso seja necessario viabilizar a análise de exames maiores no futuro, será necessário implementar um **Map-Reduce** auxiliado por filas assíncronas (ex: Celery/RabbitMQ). O sistema deverá segmentar o ECG em múltiplas janelas, processá-las em paralelo através da IA (Map) e, então, utilizar um *prompt* agregador para consolidar as análises num único laudo (Reduce).