# Integração IF-Cloud — Insight-ECG

Este documento descreve como usar as rotas do Insight-ECG que buscam exames no IF-Cloud, o servidor FHIR do ecossistema **IF4Health**.

---

## 1. Autenticação

O IF-Cloud usa tokens JWT enviados no cabeçalho `Authorization: Bearer`. O Insight-ECG apenas repassa o token do usuário; ele não armazena credenciais.

### Como obter o token
1. Acesse o painel do Biofass: [`/dashboard`](https://if4health.charqueadas.ifsul.edu.br/biofass/dashboard).
2. Autentique-se com um usuário com perfil de Profissional de Saúde.
3. No Swagger do Biofass, execute `/auth/token` e copie o valor de `access_token`.

> [!CAUTION]
> Nunca registre um token real neste repositório, em exemplos ou em *issues*. Use sempre um marcador como `SEU_TOKEN_AQUI`.

---

## 2. Cadastrar um exame de teste no IF-Cloud

Para testar a integração, cadastre um recurso `Observation` com um sinal real. Os payloads em `tests/fixtures/payloads/` (um por padrão: `normal`, `apb`, `afl`, `afib`) já estão no formato aceito, com 3.600 amostras a 360 Hz (`period` de 2,7778 ms):

```bash
curl -X POST 'https://if4health.charqueadas.ifsul.edu.br/biofass/Observation' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer SEU_TOKEN_AQUI' \
  -d @tests/fixtures/payloads/normal/payload_01_ecg.json
```

A resposta traz o identificador do recurso criado (campo `id` ou `_id`). **Guarde esse valor**: ele é o `observation_id` usado nas rotas.

> [!NOTE]
> Sinais com poucos pontos ou com `period` artificial (por exemplo, 20.000 ms) não representam um ECG real. O Insight-ECG rejeita sinais curtos demais com erro 422 (sinal corrompido) e marca como `INDETERMINADO` os sinais em que não detecta batimentos suficientes. Nesses casos, o laudo informa que a análise não é confiável, em vez de interpretar o traçado.

---

## 3. Testar pelas rotas do Insight-ECG

Com a aplicação rodando (`docker compose up --build`):

1. Acesse http://localhost:8000/docs.
2. Clique em **Authorize** (cadeado no topo) e cole o token obtido no passo 1.
3. Use uma das rotas com o `observation_id` cadastrado:

| Rota | Parâmetros | O que é analisado |
|---|---|---|
| `GET /api/v1/ecg/process/if-cloud/{observation_id}` | `minute` (padrão 0) | O minuto indicado do exame |
| `GET /api/v1/ecg/process/if-cloud/{observation_id}/range` | `start`, `end` | O intervalo de pontos indicado |
| `GET /api/v1/ecg/process/if-cloud/{observation_id}/full` | — | O exame inteiro, sujeito ao fatiamento clínico de 30.000 pontos |

Todas as rotas entregam o recurso obtido ao mesmo `EcgService` usado pela rota `POST /api/v1/ecg/process`, então o processamento (DSP, classificação de risco, redação do laudo e trava determinística) é idêntico.

### Respostas de erro esperadas

| Situação | Código |
|---|---|
| Token inválido ou expirado | 401 |
| `observation_id` não encontrado no IF-Cloud | 404 |
| Recurso fora do contrato FHIR ou sinal corrompido/curto demais | 422 |
| IF-Cloud inacessível ou falha no provedor de LLM | 502 |
