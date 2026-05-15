# POC: Insight-ECG API

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg)](https://www.docker.com/)


> [!IMPORTANT]
> POC ainda em desenvolvimento

## Visão Geral

O **Insight-ECG** é uma Prova de Conceito (POC) baseada em Inteligência Artificial projetada para atuar como a camada de inteligência do ecossistema **IF4Health**.

## Arquitetura e Tecnologias

* **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Framework web assíncrono e de alta performance).
* **Validação de Dados:** [Pydantic](https://docs.pydantic.dev/) (Validação estrita de *schemas* FHIR).
* **Integração de IA:** Google GenAI SDK (Gemini).
* **Infraestrutura:** Docker & Docker Compose para um *deploy* contínuo e sem atritos.

## Como Executar Localmente

Este projeto é totalmente conteinerizado. Você não precisa instalar dependências Python localmente para rodar a API.

### Pré-requisitos
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado e em execução.
* Integração com WSL 2 ativada (se estiver rodando no Windows).

### Subindo o Ambiente

1. Clone o repositório:
   ```bash
   git clone [https://github.com/SEU_USUARIO/poc-insight-ecg-api.git](https://github.com/SEU_USUARIO/poc-insight-ecg-api.git)
   cd poc-insight-ecg-api

2. Inicie a aplicação usando o Docker Compose:

    ```bash
    docker compose up --build
    ```

3. Acesse a API e a documentação:

- Health Check: http://localhost:8000/health

- Interactive API Docs (Swagger UI): http://localhost:8000/docs