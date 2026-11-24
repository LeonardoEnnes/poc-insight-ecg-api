# Integração IF-Cloud — Insight-ECG

Este documento detalha o fluxo completo de integração entre o motor de Inteligência Artificial do **Insight-ECG** e o barramento de serviços FHIR do ecossistema **IF4Health**.

---

## 1. Autenticação e Controle de Acesso

o IF-Cloud implementa tokens JWT transmitidos via cabeçalho HTTP `Authorization: Bearer`. 

### Fluxo de Obtenção de Token:
1. Acesse o painel administrativo do Biofass [(`/dashboard`)](https://if4health.charqueadas.ifsul.edu.br/biofass/dashboard).
2. Efetue a autenticação utilizando credenciais com privilégios de saúde de nível Profissional de Saúde.
3. No Swagger vá em `/auth/token`, execute a chamada de troca para capturar o parâmetro `access_token` gerado para a sessão.

---

## 2. Injeção de Dados Mock
A fim de testar a conexão com essa aplicação, Vamos injetar dados ficticios dentro do sistema. 

Importante: Os dados desse mock serão dados como inconclusivos propositalmente, pois a quantidade de dados é pequena, Caso queira dados completos use o segundo exemplo

### insira algum dos seguintes comandos:
#### Exemplo 1:
```bash
curl -X 'POST' \
  '[https://if4health.charqueadas.ifsul.edu.br/biofass/Observation](https://if4health.charqueadas.ifsul.edu.br/biofass/Observation)' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer aquivai-o-token' \
  -k \
  -d '{
  "resourceType": "Observation",
  "status": "final",
  "device": {
    "display": "Teste do ecg"
  },
  "component": [
    {
      "valueSampledData": {
        "origin": { "value": 0 },
        "period": 20000.0, 
        "factor": 1.0,
        "lowerLimit": -1000,
        "upperLimit": 1000,
        "dimensions": 1,
        "data": "10.0 10.0 10.0 50.0 50.0 50.0 90.0 90.0 90.0"
      }
    }
  ]
}'
```
Explicacao: Ao configurar a propriedade `period` (taxa de amostragem) para um valor artificialmente alto (`20000.0 ms`), instruímos o motor do IF-Cloud a estender a linha do tempo do exame com poucos pontos, forçando a criação interna de múltiplos blocos lógicos indexados em base zero (`_0`, `_1`, `_2`).

Resultado Esperado: Retorno 200 OK contendo os metadados estruturados FHIR e o identificador persistido no banco de dados do servidor (campo id ou _id). **Salve o hash**

#### Exemplo 2:
```bash

curl -X 'POST' \
  'https://if4health.charqueadas.ifsul.edu.br/biofass/Observation' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGllbnRfaWQiOiJuZW9mYXNzIiwic2NvcGUiOiJ1c2VyLyouY3J1ZHNoIiwic3ViIjoiNjhkZDgyOWI4ZjBhMWJkZDM0ODA4OWQzIiwiZmhpclVzZXIiOiJodHRwczovL2lmNGhlYWx0aC5jaGFycXVlYWRhcy5pZnN1bC5lZHUuYnIvYmlvZmFzcy8vUHJhY3RpdGlvbmVyLzY4ZGQ4MjliOGYwYTFiZGQzNDgwODlkMyIsImlhdCI6MTc4MzU1MjI1NCwiZXhwIjoxNzgzNTU1ODU0fQ.qOHVr7807XEK4WzFZTXFV0FuV468tRQo1D9lQL394Aw9Zw4IGbQ3bsFN8DNR9kH82_XARUDevLlcHJwL86uaQSaN-edVqg78CfGBaC2SbibQ6RLb8JCDZ0TEKxJTE7Ga2Xw1pDKQv6jcn6VNh37ggnmdohj4-Dvcd7SAzCtpz8zffbh-ufq9If8KF53HiqvWymXiWgWaMpJQ3qN5PXXJjf88ocNQ2WEGyUE-SWSO-5vJ99CgWFOyvkLv9kNtVxtFwaP6HHyIXZgq_Z2h6tsbpK3sD8r0hiv6k08ItR37PIL2JPkA4W8jOYU9_27IXnSgM83WeCp_6Paofx9b-c8fjw' \
  -k \
  -d '{
  "resourceType": "Observation",
  "status": "final",
  "device": {
    "display": "Teste do ecg 2"
  },
  "component": [
    {
      "valueSampledData": {
        "origin": { "value": 0 },
        "period": 20000.0,
        "factor": 1.0,
        "lowerLimit": -1000,
        "upperLimit": 1000,
        "dimensions": 1,
        "data": "950.0 1200.0 1450.0 1300.0 900.0 650.0 500.0 750.0 1100.0 1400.0 1480.0 1250.0 850.0 600.0 550.0 800.0 1150.0 1450.0 1500.0 1200.0 800.0 550.0 600.0 850.0 1200.0 1480.0 1450.0 1150.0 750.0 500.0 650.0 900.0 1250.0 1500.0 1400.0 1050.0 700.0 550.0 700.0 1000.0 1350.0 1480.0 1300.0 950.0 600.0 500.0 750.0 1100.0 1450.0 1500.0 1250.0 850.0 550.0 600.0 850.0 1200.0 1450.0 1400.0 1100.0 700.0 500.0 650.0 950.0 1300.0 1480.0 1350.0 1000.0 650.0 550.0 750.0 1150.0 1450.0 1500.0 1250.0 800.0 500.0 600.0 850.0 1250.0 1480.0 1400.0 1050.0 700.0 550.0 700.0 1000.0 1350.0 1500.0 1300.0 900.0 600.0 500.0 750.0 1100.0 1450.0 1480.0 1200.0 800.0 550.0 600.0 850.0 1200.0 1450.0 1400.0 1100.0 750.0 500.0 650.0 950.0 1300.0 1500.0 1350.0 950.0 650.0 550.0 750.0 1150.0 1480.0 1450.0 1200.0 850.0 500.0 600.0 900.0 1250.0 1500.0 1400.0 1050.0 700.0 550.0"
      }
    }
  ]
}'

```
> Se não quiser injetar os dados acima, pode injetar dados reais ou utilizar os json contidos na pasta mocks

### 3. Matriz de Validação e Testes Locais:
Após subir a stack de contêineres locais via Docker (docker compose up -d --build), a aplicação exporta a rota ```GET /api/v1/ecg/process/if-cloud/{observation_id}```. Esta rota intercepta o ID e o minuto solicitados, consome o dado bruto do IF-Cloud, valida os contratos via Pydantic e processa o laudo via IA.

- Acesse o ambiente de documentação interativa em http://localhost:8000/docs para validar o comportamento do fatiamento:
- Clique no botão global Authorize (ícone de cadeado no topo da página) e cole o token obtido no Passo 1.
- Expanda a rota de integração e forneça o identificador gerado na injeção da massa de dados.

Altere sequencialmente o parâmetro de query minute para validar as respostas:
| Parâmetro `minute` | Valores Extraídos do Banco | Diagnóstico do Laudo Gerado pela IA |
| :--- | :--- | :--- |
| `0` | `"10.0 10.0 10.0"` | Análise baseada na amplitude estagnada em 10.0. |
| `1` | `"50.0 50.0 50.0"` | Análise baseada na amplitude estagnada em 50.0. |
| `2` | `"90.0 90.0 90.0"` | Suspeita de assistolia ou falha técnica (lead-off) em 90.0. |