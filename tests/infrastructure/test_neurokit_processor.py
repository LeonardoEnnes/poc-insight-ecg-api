import pytest
from pathlib import Path
from app.infrastructure.signal.neurokit_processor import NeuroKitSignalProcessor
from app.core.exceptions import CorruptedSignalException

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SAMPLING_RATE = 360.0  # confirmado no cabeçalho dos arquivos IF4Health


def load_signal(filename: str) -> list[float]:
    path = FIXTURES_DIR / filename
    with open(path) as f:
        return [float(line.strip()) for line in f if line.strip() and not line.startswith("#")]


@pytest.fixture
def processor():
    return NeuroKitSignalProcessor()


# Faixas plausíveis (não exatas) usadas como sanity check clínico.
# Não são "gabarito" oficial - servem pra pegar regressão grosseira,
# não para validação estatística formal (isso é feito à parte, com N maior).
CASOS = [
    ("01_ecg.txt", "Normal (NSR)", 50, 100),
    ("02_apb.txt", "Extrassístole atrial (APB)", 50, 110),
    ("03_afl.txt", "Flutter atrial (AFL)", 100, 170),
    ("04_afib.txt", "Fibrilação atrial (AFIB)", 50, 120),
]


@pytest.mark.parametrize("filename,label,hr_min,hr_max", CASOS)
def test_extract_features_hr_within_plausible_range(processor, filename, label, hr_min, hr_max):
    """
    Sanity check clínico: a frequência cardíaca calculada deve cair numa
    faixa plausível para cada classe. Não substitui validação estatística
    formal contra dataset anotado - é um teste de regressão rápido.
    """
    signal = load_signal(filename)
    result = processor.extract_features(signal, sampling_rate=SAMPLING_RATE)

    assert result["qualidade_deteccao"] == "OK", f"Falha ao detectar picos em {label}"
    assert hr_min <= result["hr_medio_bpm"] <= hr_max, (
        f"{label}: HR {result['hr_medio_bpm']} fora da faixa esperada [{hr_min}, {hr_max}]"
    )


def test_afib_has_higher_hrv_than_normal(processor):
    """
    Marcador clínico central da fibrilação atrial: ritmo 'irregularmente
    irregular' -> variabilidade RR (SDNN) bem maior que o ritmo normal.
    Esse é o teste que mais importa para o recorte clínico do TCC2.
    """
    normal = processor.extract_features(load_signal("01_ecg.txt"), SAMPLING_RATE)
    afib = processor.extract_features(load_signal("04_afib.txt"), SAMPLING_RATE)

    assert afib["hrv_sdnn_ms"] > normal["hrv_sdnn_ms"]


def test_extract_features_flags_insufficient_quality_on_flatline(processor):
    """Sinal isoelétrico (flatline) não deve gerar HR falso - deve sinalizar INSUFICIENTE."""
    flatline_signal = [1000.0] * 3600  # 10s de sinal constante, sem picos

    result = processor.extract_features(flatline_signal, sampling_rate=SAMPLING_RATE)

    assert result["qualidade_deteccao"] == "INSUFICIENTE"
    assert result["hr_medio_bpm"] is None


def test_extract_features_raises_on_garbage_input(processor):
    """Entrada não numérica ou vazia deve estourar exceção de domínio, não crashar."""
    with pytest.raises(CorruptedSignalException):
        processor.extract_features([], sampling_rate=SAMPLING_RATE)