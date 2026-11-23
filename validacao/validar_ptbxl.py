"""
Validação externa do classificador de risco na base PTB-XL (PhysioNet).

Roda o MESMO processamento de sinal (NeuroKitSignalProcessor) e o MESMO
classificador (ThresholdRiskClassifier) da API, sem chamar o LLM e sem
alterar nenhum limiar. Os limiares foram calibrados nos 52 exames do
IF4Health; aqui eles são aplicados, congelados, a pacientes e equipamentos
diferentes (500 Hz, derivação II).

USO (dentro do container, a partir da raiz do projeto):
    docker exec -it poc-api pip install wfdb
    docker exec -it poc-api python validar_ptbxl.py --n 25

Na primeira execução, o script baixa do PhysioNet apenas os metadados e
os registros sorteados (alguns MB), guardando tudo em .cache_ptbxl/.
Execuções seguintes reutilizam o cache.

SAÍDAS:
    relatorio_ptbxl.csv  -> uma linha por exame (métricas, risco obtido x esperado)
    resumo no console    -> acurácia por padrão e precisão/revocação/F1 por risco
"""

import argparse
import ast
import csv
import sys
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import wfdb

_aqui = Path(__file__).resolve().parent
for _p in (_aqui, _aqui.parent):
    if (_p / "app").is_dir():
        sys.path.insert(0, str(_p))
        break
from app.core.exceptions import CorruptedSignalException  # noqa: E402
from app.infrastructure.classification.threshold_risk_classifier import (  # noqa: E402
    ThresholdRiskClassifier,
)
from app.infrastructure.signal.neurokit_processor import (  # noqa: E402
    NeuroKitSignalProcessor,
)

BASE_URL = "https://physionet.org/files/ptb-xl/1.0.3/"
CACHE = Path(".cache_ptbxl")
DERIVACAO = "II"

# Mesmo mapeamento técnico usado na validação do IF4Health
RISCO_ESPERADO = {"normal": "BAIXO", "apb": "MEDIO", "afl": "ALTO", "afib": "MEDIO"}
CODIGOS_ARRITMIA = {"PAC", "AFLT", "AFIB"}


def baixar(caminho_relativo: str) -> Path:
    destino = CACHE / caminho_relativo
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(BASE_URL + caminho_relativo, destino)
    return destino


def categoria(scp: dict) -> str | None:
    """Atribui um dos 4 padrões a partir dos códigos SCP do PTB-XL.
    Exames com mais de uma das arritmias de interesse são descartados."""
    codigos = set(scp)
    arritmias = codigos & CODIGOS_ARRITMIA
    if len(arritmias) > 1:
        return None
    if arritmias == {"AFIB"}:
        return "afib"
    if arritmias == {"AFLT"}:
        return "afl"
    if arritmias == {"PAC"}:
        return "apb"
    # normal: ritmo sinusal + laudo NORM com 100% de confiança
    if "SR" in codigos and scp.get("NORM", 0) == 100.0:
        return "normal"
    return None


def selecionar(n_por_classe: int, semente: int) -> pd.DataFrame:
    meta = pd.read_csv(baixar("ptbxl_database.csv"), index_col="ecg_id")
    meta["scp"] = meta["scp_codes"].apply(ast.literal_eval)
    meta["categoria"] = meta["scp"].apply(categoria)
    # fold 10: conjunto de teste recomendado pelos autores, rótulos revisados
    meta = meta[(meta["strat_fold"] == 10) & meta["categoria"].notna()]
    amostras = []
    for cat in RISCO_ESPERADO:
        grupo = meta[meta["categoria"] == cat]
        k = min(n_por_classe, len(grupo))
        if k < n_por_classe:
            print(f"[AVISO] {cat}: só {k} exames disponíveis no fold 10")
        amostras.append(grupo.sample(n=k, random_state=semente))
    return pd.concat(amostras)


def carregar_sinal(filename_hr: str) -> tuple[list[float], float]:
    for ext in (".hea", ".dat"):
        baixar(filename_hr + ext)
    rec = wfdb.rdrecord(str(CACHE / filename_hr))
    idx = rec.sig_name.index(DERIVACAO)
    sinal = rec.p_signal[:, idx]
    sinal = sinal[np.isfinite(sinal)]
    return sinal.tolist(), float(rec.fs)


def metricas_por_risco(linhas: list[dict]) -> None:
    classes = ["BAIXO", "MEDIO", "ALTO"]
    print(f"\n{'Risco':10s} | {'Precisão':>8s} | {'Revocação':>9s} | {'F1':>5s} | {'Suporte':>7s}")
    print("-" * 52)
    f1s = []
    for c in classes:
        tp = sum(1 for l in linhas if l["risco_esperado"] == c and l["risco_obtido"] == c)
        fp = sum(1 for l in linhas if l["risco_esperado"] != c and l["risco_obtido"] == c)
        fn = sum(1 for l in linhas if l["risco_esperado"] == c and l["risco_obtido"] != c)
        suporte = tp + fn
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / suporte if suporte else 0.0
        f1 = 2 * p * r / (p + r) if p + r else 0.0
        f1s.append(f1)
        print(f"{c:10s} | {p:8.3f} | {r:9.3f} | {f1:5.3f} | {suporte:7d}")
    print(f"\nF1 macro: {np.mean(f1s):.3f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=25, help="exames por padrão")
    ap.add_argument("--semente", type=int, default=42)
    args = ap.parse_args()

    dsp, clf = NeuroKitSignalProcessor(), ThresholdRiskClassifier()
    selecao = selecionar(args.n, args.semente)
    print(f"{len(selecao)} exames selecionados. Processando...")

    linhas = []
    for ecg_id, row in selecao.iterrows():
        sinal, fs = carregar_sinal(row["filename_hr"])
        try:
            feats = dsp.extract_features(sinal, fs)
        except CorruptedSignalException:
            feats = {"hr_medio_bpm": None, "hrv_sdnn_ms": None,
                     "n_picos_detectados": 0, "qualidade_deteccao": "CORROMPIDO"}
        risco = clf.classify(feats)["risco_determinado"]
        esperado = RISCO_ESPERADO[row["categoria"]]
        linhas.append({
            "ecg_id": ecg_id,
            "categoria": row["categoria"],
            "fs_hz": fs,
            "hr_medio_bpm": feats["hr_medio_bpm"],
            "hrv_sdnn_ms": feats["hrv_sdnn_ms"],
            "n_picos": feats["n_picos_detectados"],
            "qualidade": feats["qualidade_deteccao"],
            "risco_obtido": risco,
            "risco_esperado": esperado,
            "acerto": "SIM" if risco == esperado else "NAO",
        })

    with open("relatorio_ptbxl.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=linhas[0].keys())
        w.writeheader()
        w.writerows(linhas)

    print("\n" + "=" * 78)
    print(f"{'Padrão':8s} | {'N':>3s} | {'FC média ± dp':16s} | {'SDNN ± dp':16s} | {'Acurácia':>12s}")
    print("-" * 78)
    por_cat = defaultdict(list)
    for l in linhas:
        por_cat[l["categoria"]].append(l)
    for cat in RISCO_ESPERADO:
        ls = por_cat[cat]
        if not ls:
            continue
        hr = [l["hr_medio_bpm"] for l in ls if l["hr_medio_bpm"] is not None]
        sd = [l["hrv_sdnn_ms"] for l in ls if l["hrv_sdnn_ms"] is not None]
        ac = sum(l["acerto"] == "SIM" for l in ls)
        fmt = lambda v: f"{np.mean(v):.1f} ± {np.std(v):.1f}" if v else "N/A"
        print(f"{cat:8s} | {len(ls):3d} | {fmt(hr):16s} | {fmt(sd):16s} | "
              f"{ac:3d}/{len(ls):<3d} ({100*ac/len(ls):.0f}%)")
    total = sum(l["acerto"] == "SIM" for l in linhas)
    print(f"\nAcurácia geral: {total}/{len(linhas)} ({100*total/len(linhas):.1f}%)")
    print("Riscos obtidos:", dict(Counter(l["risco_obtido"] for l in linhas)))
    metricas_por_risco(linhas)
    print("\nRelatório completo: relatorio_ptbxl.csv")


if __name__ == "__main__":
    main()