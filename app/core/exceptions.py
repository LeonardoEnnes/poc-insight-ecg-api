class InsightEcgBaseException(Exception):
    """"raiz das exceptions da aplicacao"""
    def __init__(self, message:str):
        self.message = message
        super().__init__(self.message)

class NotFoundException(InsightEcgBaseException):
    def __init__(self, resource: str):
        super().__init__(f"{resource} não foi encontrado.")

class CorruptedSignalException(InsightEcgBaseException):
    def __init__(self):
        super().__init__("Sinal de ECG vazio ou corrompido.")

class SignalTooLongException(InsightEcgBaseException):
    def __init__(self, total_points: int, limit: int):
        super().__init__(f"Sinal excede o limite seguro ({total_points}/{limit} pontos).")

class InvalidSignalValueException(InsightEcgBaseException): 
    def __init__(self):
        super().__init__("O sinal contém valores inválidos ou não numéricos.")

class AIIntegrationException(InsightEcgBaseException):
    def __init__(self, message: str):
        super().__init__(f"Erro na integração com a IA: {message}")

class UnsupportedAIProviderException(InsightEcgBaseException):
    def __init__(self, provider_name: str):
        super().__init__(f"Provedor de IA '{provider_name}' não suportado ou não implementado.")