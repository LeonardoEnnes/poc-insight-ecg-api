import neurokit2 as nk
import numpy as np
from app.core.exceptions import CorruptedSignalException

class NeuroKitSignalProcessor:
    # Piso de plausibilidade fisiológica: nenhuma condição clínica viável
    # produz menos que isso, mesmo bradicardia severa. Usado para rejeitar
    # ruído/artefato que produz poucos picos espúrios (ex: eletrodo solto),
    # distinto do limiar clínico de bradicardia do RiskClassifier (50bpm),
    # que é uma decisão de risco, não um filtro de qualidade de sinal.
    MIN_BPM_PLAUSIVEL = 25

    def extract_features(self, signal: list[float], sampling_rate: float) -> dict:
        if not signal:
            raise CorruptedSignalException()

        try:
            cleaned = nk.ecg_clean(np.array(signal), sampling_rate=sampling_rate)
            _, info = nk.ecg_peaks(cleaned, sampling_rate=sampling_rate)
        except Exception:
            # falha na limpeza/detecção em si (ex: entrada malformada) = dado corrompido
            raise CorruptedSignalException()

        r_peaks = info["ECG_R_Peaks"]

        duration_sec = len(signal) / sampling_rate
        min_picos_esperados = max(2, duration_sec * (self.MIN_BPM_PLAUSIVEL / 60))

        # sinal válido tecnicamente, mas sem batimentos plausíveis detectáveis
        # (ex: flatline, eletrodo solto, ruído puro) - não é corrupção de dado,
        # é achado clínico/técnico relevante que não deve ser reportado como OK
        if len(r_peaks) < min_picos_esperados:
            return {
                "hr_medio_bpm": None,
                "hrv_sdnn_ms": None,
                "n_picos_detectados": len(r_peaks),
                "qualidade_deteccao": "INSUFICIENTE",
            }

        rr_intervals_ms = np.diff(r_peaks) / sampling_rate * 1000
        hr_series = nk.ecg_rate(r_peaks, sampling_rate=sampling_rate, desired_length=len(cleaned))

        return {
            "hr_medio_bpm": round(float(np.mean(hr_series)), 1),
            "hrv_sdnn_ms": round(float(np.std(rr_intervals_ms)), 1),
            "n_picos_detectados": len(r_peaks),
            "qualidade_deteccao": "OK",
        }