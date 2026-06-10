from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.exceptions import SignalTooLongException, CorruptedSignalException, InvalidSignalValueException

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