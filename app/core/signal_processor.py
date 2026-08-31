from typing import Protocol

class SignalProcessor(Protocol):
    def extract_features(self, signal: list[float], sampling_rate: float) -> dict:
        """Extrai métricas determinísticas do sinal de ECG."""
        ...