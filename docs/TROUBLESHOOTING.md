# Gemini 

Sempre acesse o https://aistudio.google.com/ para ter controle de gastos dos tokens da IA

### (Erro 502)
Como o sistema depende de LLMs fornecidos em nuvem (atualmente  o Gemini), podem ocorrer instabilidades externas que fogem ao controle da aplicação.

### O Problema
Em momentos de pico de uso global, a API do Gemini (especialmente modelos recentes como o `gemini-3.5-flash`) pode rejeitar requisições, retornando a mensagem:
> *"This model is currently experiencing high demand. Spikes in demand are usually temporary."*

#### Solução Provisória
Para contornar filas de requisição e testar a API localmente sem interrupções, altere temporariamente o modelo utilizado no seu arquivo `.env` para uma versão mais leve e com menor tráfego (ex: `gemini-3.1-flash-lite`).

1. Abra o arquivo `.env`
2. Altere a variável do modelo: `LLM_MODEL=gemini-3.1-flash-lite` -- Ou outro modelo de sua preferencia voce pode encontrar mais modelos em [Link](https://ai.google.dev/gemini-api/docs/models?hl=pt-br)
3. Reinicie o container: `docker compose up --build`

Caso encontre algum erro especifico do **Gemini** de uma olhada na documentação oficial: [Link](https://ai.google.dev/gemini-api/docs)