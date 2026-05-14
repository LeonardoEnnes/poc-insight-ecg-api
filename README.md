# POC: Insight-ECG API

> [!IMPORTANT]
> This poc is still in development

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg)](https://www.docker.com/)

## Short Overview

**Insight-ECG** is an AI-driven Proof of Concept (POC) designed to act as the intelligence layer for the **IF4Health** ecosystem. 

## Architecture & Tech Stack

This project follows a modular, pragmatically SOLID architecture to separate data ingestion, validation, and AI inference.

* **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Asynchronous, high-performance web framework).
* **Data Validation:** [Pydantic](https://docs.pydantic.dev/) (Strict FHIR schema validation).
* **AI Integration:** Google GenAI SDK (Gemini).
* **Infrastructure:** Docker & Docker Compose for seamless deployment.

## How to Run Locally

This project is fully containerized. You do not need to install Python dependencies locally to run the API.

### Prerequisites
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
* WSL 2 Integration enabled (if running on Windows).

### Up and Running

1. Clone the repository:
   ```bash
   git clone [https://github.com/YOUR_USERNAME/poc-insight-ecg-api.git](https://github.com/YOUR_USERNAME/poc-insight-ecg-api.git)
   cd poc-insight-ecg-api

2. Start the application using Docker Compose:

    ```bash
    docker compose up --build
    ```

3. Access the API and Documentation:

- Health Check: http://localhost:8000/health

- Interactive API Docs (Swagger UI): http://localhost:8000/docs