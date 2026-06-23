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
  -H 'Authorization: Bearer token-aqui' \
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
        "data": "10.0 10.0 10.0 50.0 50.0 50.0 90.0 90.0 90.0 953.0 951.0 949.0 948.0 950.0 950.0 951.0 948.0 946.0 944.0 947.0 947.0 947.0 943.0 944.0 943.0 943.0 944.0 944.0 947.0 946.0 946.0 945.0 950.0 951.0 953.0 952.0 954.0 957.0 961.0 963.0 964.0 965.0 964.0 966.0 971.0 974.0 973.0 973.0 972.0 973.0 976.0 977.0 975.0 976.0 975.0 976.0 979.0 980.0 976.0 976.0 974.0 976.0 981.0 981.0 979.0 977.0 977.0 975.0 978.0 978.0 979.0 976.0 973.0 974.0 976.0 976.0 974.0 972.0 971.0 970.0 971.0 974.0 971.0 969.0 970.0 969.0 972.0 974.0 973.0 973.0 971.0 971.0 971.0 973.0 970.0 967.0 965.0 967.0 969.0 969.0 969.0 966.0 965.0 965.0 966.0 969.0 968.0 965.0 965.0 964.0 965.0 965.0 966.0 965.0 965.0 967.0 967.0 969.0 970.0 968.0 971.0 972.0 977.0 979.0 979.0 978.0 979.0 978.0 984.0 985.0 988.0 989.0 987.0 990.0 994.0 995.0 991.0 989.0 986.0 986.0 992.0 995.0 994.0 993.0 996.0 1000.0 1002.0 994.0 986.0 981.0 978.0 973.0 976.0 970.0 967.0 966.0 964.0 966.0 966.0 967.0 966.0 965.0 961.0 963.0 965.0 964.0 964.0 963.0 958.0 962.0 964.0 965.0 964.0 961.0 960.0 963.0 963.0 962.0 962.0 957.0 954.0 945.0 940.0 934.0 926.0 921.0 927.0 953.0 993.0 1028.0 1074.0 1134.0 1193.0 1232.0 1244.0 1214.0 1139.0 1039.0 960.0 927.0 932.0 949.0 956.0 953.0 948.0 950.0 952.0 953.0 953.0 951.0 948.0 951.0 949.0 949.0 949.0 945.0 945.0 945.0 950.0 950.0 950.0 949.0 948.0 949.0 951.0 952.0 951.0 950.0 947.0 947.0 950.0 952.0 951.0 951.0 949.0 948.0 950.0 948.0 949.0 946.0 947.0 948.0 947.0 952.0 949.0 948.0 947.0 949.0 953.0 951.0 949.0 951.0 948.0 950.0 950.0 954.0 951.0 954.0 949.0 950.0 952.0 952.0 951.0 950.0 947.0 948.0 949.0 952.0 949.0 949.0 945.0 947.0 949.0 950.0 948.0 946.0 946.0 946.0 949.0 951.0 950.0 950.0 949.0 951.0 951.0 953.0 952.0 952.0 951.0 952.0 954.0 960.0 961.0 961.0 963.0 967.0 969.0 971.0 970.0 972.0 972.0 976.0 977.0 980.0 979.0 978.0 979.0 979.0 982.0 981.0 981.0 980.0 978.0 979.0 980.0 980.0 981.0 980.0 979.0 980.0 979.0 981.0 978.0 974.0 975.0 979.0 979.0 980.0 979.0 978.0 976.0 978.0 981.0 980.0 976.0 978.0 975.0 975.0 976.0 976.0 973.0 974.0 970.0 973.0 975.0 974.0 971.0 968.0 966.0 967.0 970.0 968.0 969.0 969.0 965.0 968.0 967.0 971.0 970.0 968.0 966.0 970.0 972.0 972.0 970.0 967.0 968.0 966.0 971.0 971.0 971.0 969.0 968.0 972.0 972.0 973.0 972.0 969.0 968.0 971.0 977.0 978.0 979.0 977.0 978.0 981.0 986.0 987.0 988.0 990.0 990.0 994.0 995.0 1000.0 999.0 1000.0 995.0 992.0 993.0 994.0 995.0 993.0 992.0 992.0 994.0 1002.0 1003.0 1000.0 990.0 988.0 985.0 985.0 982.0 978.0 973.0 974.0 973.0 973.0 969.0 969.0 969.0 967.0 969.0 971.0 970.0 967.0 964.0 964.0 965.0 967.0 965.0 962.0 961.0 964.0 963.0 967.0 967.0 967.0 963.0 962.0 956.0 949.0 942.0 933.0 923.0 922.0 939.0 965.0 990.0 1010.0 1032.0 1069.0 1115.0 1168.0 1208.0 1233.0 1244.0 1231.0 1178.0 1093.0 1008.0 951.0 933.0 944.0 959.0 966.0 962.0 957.0 956.0 957.0 957.0 958.0 955.0 954.0 953.0 955.0 956.0 958.0 956.0 954.0 951.0 952.0 955.0 960.0 958.0 957.0 957.0 958.0 958.0 959.0 958.0 955.0 951.0 952.0 955.0 957.0 955.0 950.0 950.0 952.0 955.0 954.0 953.0 953.0 950.0 948.0 953.0 950.0 950.0 952.0 952.0 952.0 955.0 956.0 954.0 953.0 951.0 952.0 954.0 954.0 953.0 950.0 951.0 952.0 952.0 953.0 952.0 948.0 949.0 947.0 948.0 950.0 949.0 948.0 946.0 948.0 947.0 947.0 949.0 949.0 948.0 950.0 949.0 947.0 948.0 946.0 947.0 952.0 954.0 955.0 955.0 955.0 956.0 959.0 965.0 966.0 965.0 967.0 967.0 970.0 973.0 972.0 972.0 972.0 968.0 971.0 974.0 978.0 978.0 978.0 975.0 974.0 974.0 976.0 976.0 974.0 972.0 974.0 977.0 980.0 979.0 975.0 973.0 973.0 973.0 972.0 973.0 968.0 966.0 970.0 970.0 976.0 973.0 969.0 969.0 970.0 970.0 971.0 970.0 969.0 968.0 967.0 968.0 968.0 965.0 961.0 960.0 962.0 965.0 964.0 965.0 966.0 960.0 960.0 960.0 960.0 963.0 962.0 961.0 962.0 964.0 964.0 964.0 960.0 957.0 959.0 963.0 962.0 962.0 961.0 960.0 962.0 964.0 965.0 964.0 961.0 962.0 961.0 960.0 965.0 963.0 962.0 960.0 962.0 965.0 968.0 968.0 969.0 971.0 972.0 978.0 979.0 981.0 978.0 978.0 981.0 983.0 988.0 987.0 985.0 983.0 985.0 984.0 986.0 982.0 980.0 979.0 985.0 985.0 986.0 984.0 984.0 987.0 990.0 992.0 989.0 982.0 978.0 973.0 971.0 967.0 966.0 966.0 961.0 959.0 959.0 960.0 960.0 959.0 956.0 954.0 955.0 955.0 958.0 958.0 959.0 956.0 956.0 956.0 959.0 958.0 957.0 955.0 956.0 958.0 960.0 960.0 958.0 955.0 952.0 946.0 942.0 934.0 929.0 920.0 913.0 916.0 932.0 961.0 990.0 1026.0 1074.0 1128.0 1178.0 1212.0 1219.0 1190.0 1122.0 1037.0 969.0 932.0 923.0 926.0 935.0 944.0 945.0 942.0 945.0 941.0 944.0 944.0 944.0 943.0 939.0 939.0 941.0 941.0 945.0 944.0 943.0 945.0 943.0 945.0 944.0 945.0 941.0 939.0 942.0 944.0 943.0 943.0 941.0 939.0 940.0 942.0 941.0 941.0 938.0 935.0 939.0 937.0 940.0 940.0 938.0 936.0 939.0 941.0 944.0 942.0 940.0 939.0 940.0 942.0 942.0 940.0 939.0 937.0 938.0 938.0 941.0 939.0 939.0 936.0 939.0 941.0 942.0 941.0 940.0 935.0 935.0 940.0 940.0 939.0 936.0 936.0 935.0 938.0 936.0 933.0 931.0 930.0 931.0 935.0 932.0 931.0 930.0 928.0 928.0 930.0 934.0 932.0 933.0 934.0 940.0 945.0 949.0 948.0 952.0 952.0 956.0"
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