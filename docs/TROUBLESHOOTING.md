# Troubleshooting

## Provedor de LLM

Acompanhe o consumo da cota em https://aistudio.google.com/ (Gemini) ou https://platform.openai.com/usage (OpenAI).

### Erro 502 — modelo sobrecarregado

Como o sistema depende de LLMs em nuvem, podem ocorrer instabilidades externas. Em momentos de pico, a API do Gemini pode rejeitar requisições com a mensagem:
> *"This model is currently experiencing high demand. Spikes in demand are usually temporary."*

O Insight-ECG devolve esse caso como **502 (Bad Gateway)**, sem expor detalhes internos.

**Solução provisória:** troque temporariamente o modelo por uma versão mais leve.
1. Abra o arquivo `.env`.
2. Altere a variável `AI_MODEL_NAME` (por exemplo, `AI_MODEL_NAME=gemini-3.1-flash-lite`). A lista de modelos está em [ai.google.dev/gemini-api/docs/models](https://ai.google.dev/gemini-api/docs/models?hl=pt-br).
3. Reinicie o container: `docker compose up --build`.

Outra alternativa é trocar de provedor com `AI_PROVIDER=openai`.

### Erro 404 — modelo descontinuado

Nomes de modelo são descontinuados com frequência. Se a API responder que o modelo "is no longer available", a própria mensagem costuma indicar o substituto. Atualize `AI_MODEL_NAME` no `.env` e, para os testes de qualidade, o `model_name` em `tests/quality/gemini_judge_model.py`.

### Erro 429 nos testes de qualidade

A cota gratuita do Gemini permite poucas requisições por dia. Rode os testes de `tests/quality/` isoladamente e com moderação:
```bash
docker exec -it poc-api pytest tests/quality/ -v -s
```

## CI

A CI roda apenas a suíte principal (`pytest --ignore=tests/quality`), com provedores de IA simulados. Os testes de qualidade textual precisam de uma chave real e são pulados automaticamente quando ela não está configurada.

Para erros específicos do Gemini, consulte a [documentação oficial](https://ai.google.dev/gemini-api/docs).
