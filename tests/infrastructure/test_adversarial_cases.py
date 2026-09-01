"""
Suíte de testes adversariais - Insight-ECG TCC2

Cobre os casos citados no roadmap: flatline, saturação, ruído, eletrodo
solto, extremos de HR, e dados malformados. Usa sinais sintéticos
(neurokit2.ecg_simulate) para casos que exigem controle preciso da
variável testada (HR extremo, ruído), e casos construídos manualmente
para os demais.
"""
import numpy as np
import neurokit2 as nk
import pytest
from app.infrastructure.signal.neurokit_processor import NeuroKitSignalProcessor
from app.core.exceptions import CorruptedSignalException

SAMPLING_RATE = 360.0
DURATION_SEC = 10


@pytest.fixture
def processor():
    return NeuroKitSignalProcessor()


# ---------------------------------------------------------------------------
# 1. Flatline - sinal isoelétrico constante (já existia, mantido aqui por
#    completude da suíte adversarial)
# ---------------------------------------------------------------------------

def test_flatline_signal_flags_insufficient_quality(processor):
    """Sinal constante (sem atividade elétrica) não deve gerar HR falso."""
    flatline = [1000.0] * int(SAMPLING_RATE * DURATION_SEC)

    result = processor.extract_features(flatline, SAMPLING_RATE)

    assert result["qualidade_deteccao"] == "INSUFICIENTE"
    assert result["hr_medio_bpm"] is None


# ---------------------------------------------------------------------------
# 2. Saturação - sinal grudado no limite do ADC (sensor saturado/estourado)
# ---------------------------------------------------------------------------

def test_saturated_signal_flags_insufficient_quality(processor):
    """Sinal saturado no limite superior do ADC (ex: 4095 em resolução 12-bit)."""
    saturado = [4095.0] * int(SAMPLING_RATE * DURATION_SEC)

    result = processor.extract_features(saturado, SAMPLING_RATE)

    assert result["qualidade_deteccao"] == "INSUFICIENTE"
    assert result["hr_medio_bpm"] is None


# ---------------------------------------------------------------------------
# 3. Ruído - sinal real com alto nível de ruído sobreposto
# ---------------------------------------------------------------------------

def test_noisy_signal_does_not_crash_and_reports_status():
    """
    Sinal com ruído alto (SNR baixo) não deve derrubar o sistema.
    Não exigimos um resultado único (pode detectar com qualidade OK
    degradada ou sinalizar INSUFICIENTE, dependendo do nível de ruído) -
    o requisito é robustez: nunca lançar exceção não tratada.
    """
    processor = NeuroKitSignalProcessor()
    sinal_ruidoso = nk.ecg_simulate(
        duration=DURATION_SEC,
        sampling_rate=SAMPLING_RATE,
        length=int(SAMPLING_RATE * DURATION_SEC),
        heart_rate=75,
        noise=0.8,
    )

    try:
        result = processor.extract_features(list(sinal_ruidoso), SAMPLING_RATE)
    except CorruptedSignalException:
        # aceitável: ruído extremo pode legitimamente ser tratado como dado corrompido
        return

    assert result["qualidade_deteccao"] in ("OK", "INSUFICIENTE")


# ---------------------------------------------------------------------------
# 4. Eletrodo solto - ruído de baixa amplitude sem forma de onda cardíaca,
#    ao longo de uma gravação de duração normal (não um buffer curto demais,
#    que é um caso técnico distinto tratado no teste 7)
# ---------------------------------------------------------------------------

def test_loose_electrode_noise_flags_insufficient_quality(processor):
    """
    Achado de teste adversarial: ruído puro de baixa amplitude (simulando
    eletrodo desconectado) podia, antes da correção de plausibilidade
    fisiológica, ser interpretado como batimentos válidos e esparsos,
    gerando HR/HRV implausíveis reportados com qualidade OK - o que
    poderia levar o RiskClassifier a gerar um alerta de risco a partir
    de ruído. Este teste é a regressão dessa correção.
    """
    np.random.seed(42)
    eletrodo_solto = list(np.random.normal(loc=1000, scale=2, size=int(SAMPLING_RATE * DURATION_SEC)))

    result = processor.extract_features(eletrodo_solto, SAMPLING_RATE)

    assert result["qualidade_deteccao"] == "INSUFICIENTE", (
        "Ruído de eletrodo solto não deve ser reportado como sinal válido (OK)"
    )
    assert result["hr_medio_bpm"] is None


# ---------------------------------------------------------------------------
# 5 e 6. Extremos de HR - taquicardia e bradicardia extremas sintéticas
# ---------------------------------------------------------------------------

def test_extreme_tachycardia_is_detected_correctly(processor):
    """Taquicardia extrema (180bpm) deve ser detectada com HR próximo do real."""
    sinal = nk.ecg_simulate(
        duration=DURATION_SEC,
        sampling_rate=SAMPLING_RATE,
        length=int(SAMPLING_RATE * DURATION_SEC),
        heart_rate=180,
        noise=0.01,
    )

    result = processor.extract_features(list(sinal), SAMPLING_RATE)

    assert result["qualidade_deteccao"] == "OK"
    assert 160 <= result["hr_medio_bpm"] <= 200


def test_extreme_bradycardia_is_detected_correctly(processor):
    """
    Bradicardia extrema (35bpm) deve ser detectada corretamente - caso
    de fronteira importante: poucos picos numa janela de 10s (~5-6),
    não deve ser confundido com ruído pela checagem de plausibilidade
    (MIN_BPM_PLAUSIVEL = 25, abaixo do caso real testado).
    """
    sinal = nk.ecg_simulate(
        duration=DURATION_SEC,
        sampling_rate=SAMPLING_RATE,
        length=int(SAMPLING_RATE * DURATION_SEC),
        heart_rate=35,
        noise=0.01,
    )

    result = processor.extract_features(list(sinal), SAMPLING_RATE)

    assert result["qualidade_deteccao"] == "OK", (
        "Bradicardia real não deve ser confundida com ruído/artefato"
    )
    assert 25 <= result["hr_medio_bpm"] <= 50


# ---------------------------------------------------------------------------
# 7. Dados malformados - valores não numéricos ou inválidos (NaN/Inf)
# ---------------------------------------------------------------------------

def test_signal_with_nan_values_does_not_crash(processor):
    """Sinal contendo NaN não deve derrubar o sistema com exceção não tratada."""
    sinal_com_nan = [1000.0, float("nan"), 998.0] * 100

    # comportamento aceitável: ou trata graciosamente (INSUFICIENTE/OK),
    # ou sinaliza como corrompido - o que não pode acontecer é uma
    # exceção não tratada (crash) se propagando para fora do serviço
    try:
        result = processor.extract_features(sinal_com_nan, SAMPLING_RATE)
        assert result["qualidade_deteccao"] in ("OK", "INSUFICIENTE")
    except CorruptedSignalException:
        pass  # comportamento aceitável e esperado


def test_signal_with_infinite_values_raises_corrupted_exception(processor):
    """Sinal contendo valores infinitos deve ser tratado como corrompido."""
    sinal_com_inf = [1000.0, float("inf"), 998.0] * 100

    with pytest.raises(CorruptedSignalException):
        processor.extract_features(sinal_com_inf, SAMPLING_RATE)


# ---------------------------------------------------------------------------
# 8. Buffer tecnicamente curto demais para o filtro (edge case técnico,
#    distinto do "eletrodo solto" clínico do teste 4)
# ---------------------------------------------------------------------------

def test_extremely_short_buffer_raises_corrupted_exception(processor):
    """
    Buffer com poucos pontos (insuficiente até para o filtro de limpeza
    do NeuroKit) deve ser tratado como corrompido, não crashar.
    """
    buffer_curto = [1000.0, 1005.0, 998.0, 1002.0, 999.0]

    with pytest.raises(CorruptedSignalException):
        processor.extract_features(buffer_curto, SAMPLING_RATE)