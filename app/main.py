from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(
    title="Insight ECG API", 
    description="API para analise semantica de ECG via IA generativa",
    version="0.1.0",
    )

@app.get("/health")
def health_check():
    return {
            "status": "online", 
            "message": "ta rodando",
            "enviroment": settings.ENVIRONMENT,
            "ai_provider_active": settings.AI_PROVIDER
        }
