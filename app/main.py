from fastapi import FastAPI
from app.core.config import settings
from app.core.exceptions_handler import add_exception_handlers
from app.routes import ecg_router

app = FastAPI(
    title="Insight ECG API", 
    description="API para analise semantica de ECG via IA generativa",
    version="0.1.0",
    )

app.include_router(ecg_router.router)
add_exception_handlers(app)

@app.get("/health")
def health_check():
    return {
            "status": "online", 
            "message": "Api rodando",
            "enviroment": settings.ENVIRONMENT,
            "ai_provider_active": settings.AI_PROVIDER
        }
