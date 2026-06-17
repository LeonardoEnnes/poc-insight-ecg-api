from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from app.core.exceptions import (
    SignalTooLongException, 
    CorruptedSignalException, 
    InvalidSignalValueException,
    AIIntegrationException,
    UnsupportedAIProviderException
)

def add_exception_handlers(app: FastAPI):
    """Registra todos os interceptadores de exceção da aplicação."""
    
    @app.exception_handler(SignalTooLongException)
    async def signal_too_long_handler(request: Request, exc: SignalTooLongException):
        return JSONResponse(
            status_code=413,
            content={"error": "Limite Excedido", "detail": exc.message},
        )

    @app.exception_handler(CorruptedSignalException)
    async def corrupted_signal_handler(request: Request, exc: CorruptedSignalException):
        return JSONResponse(
            status_code=422,
            content={"error": "Dados Inválidos", "detail": exc.message},
        )
        
    @app.exception_handler(InvalidSignalValueException)
    async def invalid_signal_value_handler(request: Request, exc: InvalidSignalValueException):
        return JSONResponse(
            status_code=400,
            content={"error": "Valor de Sinal Inválido", "detail": exc.message},
        )
        
    @app.exception_handler(ValidationError)
    async def pydantic_validation_handler(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=422,
            content={"error": "Contrato FHIR Inválido", "detail": exc.errors()},
    )
        
    @app.exception_handler(AIIntegrationException)
    async def ai_integration_handler(request: Request, exc: AIIntegrationException):
        return JSONResponse(
            status_code=502, 
            content={"error": "Falha no Serviço de IA", "detail": exc.message},
        )

    @app.exception_handler(UnsupportedAIProviderException)
    async def unsupported_ai_handler(request: Request, exc: UnsupportedAIProviderException):
        return JSONResponse(
            status_code=501,
            content={"error": "Provedor Não Suportado", "detail": exc.message},
        )