import neurokit2 as nk
import numpy as np
from app.core.exceptions import CorruptedSignalException

class NeuroKitSignalProcessor:
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

        # sinal válido tecnicamente, mas sem batimentos detectáveis (ex: flatline,
        # eletrodo solto) - não é corrupção de dado, é achado clínico relevante
        if len(r_peaks) < 2:
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