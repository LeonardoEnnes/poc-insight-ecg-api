"""
Script de validação em lote - Insight-ECG TCC2

Roda o DSP (NeuroKit2) + RiskClassifier sobre múltiplos arquivos por
categoria clínica, gerando um relatório agregado (CSV + resumo no console)
para avaliar se os limiares atuais do ThresholdRiskClassifier se sustentam
com N maior que 1 por classe.

COMO USAR:
1. Organize os arquivos .txt em pastas por categoria, dentro de uma pasta
   raiz (ex: "dados_validacao/"), assim:

       dados_validacao/
           normal/
               arquivo1.txt
               arquivo2.txt
               ...
           apb/
               arquivo1.txt
               ...
           afl/
               ...
           afib/
               ...

2. Rode: python validar_em_lote.py dados_validacao/

3. O script gera:
   - relatorio_completo.csv (uma linha por arquivo, com HR/HRV/risco)
   - Um resumo agregado impresso no console (média, desvio padrão por classe)
   - Uma matriz de "risco esperado x risco obtido" por categoria, para
     avaliar visualmente se o classificador está separando bem as classes
"""

import sys
import csv
from pathlib import Path
from collections import defaultdict

import numpy as np
import neurokit2 as nk

SAMPLING_RATE = 360.0  # confirmado no cabeçalho dos arquivos IF4Health

# Mapeamento de nome de pasta -> risco esperado (ajuste conforme seu critério clínico)
# Isto é só para fins de comparação/relatório - o classificador em si NÃO usa isso.
RISCO_ESPERADO_POR_CATEGORIA = {
    "normal": "BAIXO",
    "apb": "MEDIO",     # ajuste se seu critério clínico definir diferente
    "afl": "ALTO",
    "afib": "MEDIO",    # ajuste se seu critério clínico definir diferente
}


def load_signal(path: Path) -> list[float]:
    with open(path) as f:
        return [
            float(line.strip())
            for line in f
            if line.strip() and not line.startswith("#")
        ]


def extract_features(signal: list[float], sampling_rate: float) -> dict:
    """Mesma lógica do NeuroKitSignalProcessor do projeto."""
    if not signal:
        return {
            "hr_medio_bpm": None,
            "hrv_sdnn_ms": None,
            "n_picos_detectados": 0,
            "qualidade_deteccao": "INSUFICIENTE",
        }
    try:
        cleaned = nk.ecg_clean(np.array(signal), sampling_rate=sampling_rate)
        _, info = nk.ecg_peaks(cleaned, sampling_rate=sampling_rate)
    except Exception as e:
        return {
            "hr_medio_bpm": None,
            "hrv_sdnn_ms": None,
            "n_picos_detectados": 0,
            "qualidade_deteccao": f"ERRO: {e}",
        }

    r_peaks = info["ECG_R_Peaks"]
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


class ThresholdRiskClassifier:
    """Cópia local do classificador do projeto, para rodar fora do container."""

    HR_BRADICARDIA_BPM = 50
    HR_TAQUICARDIA_BPM = 100
    HRV_SDNN_ELEVADO_MS = 40  # CORRIGIDO - recalibrado apos analise N=16 (era 90, defasado)

    def classify(self, features: dict) -> str:
        hr = features.get("hr_medio_bpm")
        hrv = features.get("hrv_sdnn_ms")
        qualidade = features.get("qualidade_deteccao")

        if qualidade != "OK" or hr is None:
            return "INDETERMINADO"
        if hr > self.HR_TAQUICARDIA_BPM or hr < self.HR_BRADICARDIA_BPM:
            return "ALTO"
        if hrv is not None and hrv > self.HRV_SDNN_ELEVADO_MS:
            return "MEDIO"
        return "BAIXO"


def main(root_dir: str):
    root = Path(root_dir)
    classifier = ThresholdRiskClassifier()

    linhas = []
    agregados = defaultdict(list)  # categoria -> lista de dicts de features

    categorias = [d for d in root.iterdir() if d.is_dir()]
    if not categorias:
        print(f"Nenhuma subpasta encontrada em {root_dir}. Verifique a estrutura esperada.")
        return

    for categoria_dir in sorted(categorias):
        categoria = categoria_dir.name.lower()
        arquivos = sorted(categoria_dir.glob("*.txt"))

        if not arquivos:
            print(f"[AVISO] Nenhum .txt encontrado em {categoria_dir}")
            continue

        for arquivo in arquivos:
            signal = load_signal(arquivo)
            features = extract_features(signal, SAMPLING_RATE)
            risco_obtido = classifier.classify(features)
            risco_esperado = RISCO_ESPERADO_POR_CATEGORIA.get(categoria, "?")

            linha = {
                "categoria": categoria,
                "arquivo": arquivo.name,
                "hr_medio_bpm": features["hr_medio_bpm"],
                "hrv_sdnn_ms": features["hrv_sdnn_ms"],
                "n_picos_detectados": features["n_picos_detectados"],
                "qualidade_deteccao": features["qualidade_deteccao"],
                "risco_obtido": risco_obtido,
                "risco_esperado": risco_esperado,
                "acerto": "SIM" if risco_obtido == risco_esperado else "NAO",
            }
            linhas.append(linha)
            agregados[categoria].append(features)

    # --- salvar CSV completo ---
    if linhas:
        with open("relatorio_completo.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=linhas[0].keys())
            writer.writeheader()
            writer.writerows(linhas)
        print(f"\nRelatório completo salvo em: relatorio_completo.csv ({len(linhas)} arquivos processados)\n")

    # --- resumo agregado por categoria ---
    print("=" * 90)
    print("RESUMO AGREGADO POR CATEGORIA")
    print("=" * 90)
    print(f"{'Categoria':12s} | {'N':>3s} | {'HR médio (± dp)':22s} | {'HRV médio (± dp)':22s} | {'Acurácia':>10s}")
    print("-" * 90)

    for categoria, feats_lista in agregados.items():
        hrs = [f["hr_medio_bpm"] for f in feats_lista if f["hr_medio_bpm"] is not None]
        hrvs = [f["hrv_sdnn_ms"] for f in feats_lista if f["hrv_sdnn_ms"] is not None]
        n = len(feats_lista)

        hr_str = f"{np.mean(hrs):.1f} ± {np.std(hrs):.1f}" if hrs else "N/A"
        hrv_str = f"{np.mean(hrvs):.1f} ± {np.std(hrvs):.1f}" if hrvs else "N/A"

        acertos = sum(1 for l in linhas if l["categoria"] == categoria and l["acerto"] == "SIM")
        acuracia = f"{acertos}/{n} ({100*acertos/n:.0f}%)" if n else "N/A"

        print(f"{categoria:12s} | {n:>3d} | {hr_str:22s} | {hrv_str:22s} | {acuracia:>10s}")

    print("=" * 90)
    print("\nATENÇÃO: revise manualmente os casos com 'acerto=NAO' no CSV completo.")
    print("Se houver muitos erros numa categoria específica, pode ser necessário")
    print("ajustar o limiar (HRV_SDNN_ELEVADO_MS ou as faixas de HR) do RiskClassifier,")
    print("com base na distribuição real observada acima - não antes disso.\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python validar_em_lote.py <pasta_raiz_com_subpastas_por_categoria>")
        sys.exit(1)
    main(sys.argv[1])