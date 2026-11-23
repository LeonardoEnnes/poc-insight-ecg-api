"""
Recalibração do limiar de SDNN com separação treino/teste na base PTB-XL.

PROTOCOLO (sem vazamento de dados):
    1. TREINO  -> folds 1 a 8 do PTB-XL. O limiar de SDNN é escolhido aqui,
                  testando valores de 30 a 150 ms e ficando com o de maior
                  F1 macro. Os limiares de frequência (50 e 100 bpm) são
                  convenções clínicas e não são ajustados.
    2. TESTE   -> os MESMOS 80 exames do fold 10 usados em validar_ptbxl.py
                  (n=25 por padrão, semente 42). Nenhum exame do teste
                  participa da escolha do limiar.
    3. IF4HEALTH -> os 52 exames originais são reavaliados com o novo
                  limiar, para mostrar o efeito na base de calibração antiga.

Nada é alterado na API: o script só informa o limiar sugerido e o
desempenho antes/depois. A troca no código é decisão posterior.

USO (mesma pasta do validar_ptbxl.py):
    docker exec -it poc-api python calibrar_ptbxl.py
    docker exec -it poc-api python calibrar_ptbxl.py --n-treino 150

SAÍDAS:
    calibracao_ptbxl.csv -> F1 macro e acurácia no treino para cada limiar
    resumo no console    -> limiar escolhido e comparação 40 ms x novo limiar
"""

import argparse
import ast
import csv
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validar_ptbxl as v 

from app.core.exceptions import CorruptedSignalException  # noqa: E402
from app.infrastructure.classification.threshold_risk_classifier import (  # noqa: E402
    ThresholdRiskClassifier,
)
from app.infrastructure.signal.neurokit_processor import NeuroKitSignalProcessor  # noqa: E402


def _baixar_com_retry(caminho_relativo: str) -> Path:
    """Download resiliente: o PhysioNet devolve 502/503/429 de vez em quando
    sob muitas requisições seguidas. Tenta de novo com espera crescente e
    grava em arquivo temporário, para nunca deixar um arquivo pela metade
    no cache."""
    import time
    import urllib.error
    import urllib.request

    destino = v.CACHE / caminho_relativo
    if destino.exists():
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp = destino.with_suffix(destino.suffix + ".part")
    for tentativa in range(1, 7):
        try:
            urllib.request.urlretrieve(v.BASE_URL + caminho_relativo, tmp)
            tmp.replace(destino)
            time.sleep(0.2)
            return destino
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            espera = 5 * tentativa
            print(f"    [rede] {e} em {caminho_relativo} - nova tentativa em {espera}s ({tentativa}/6)")
            time.sleep(espera)
    raise RuntimeError(f"Falha ao baixar {caminho_relativo} após 6 tentativas. "
                       "Rode o script de novo: o que já foi baixado fica no cache.")


v.baixar = _baixar_com_retry  # carregar_sinal() e selecionar() passam a usar a versão resiliente

LIMIAR_ATUAL = 40
GRADE = list(range(30, 155, 5))
RISCOS = ["BAIXO", "MEDIO", "ALTO"]
IF4HEALTH_DIR = Path("tests/fixtures/ecgs_raw")
IF4HEALTH_FS = 360.0


# ---------------------------------------------------------------- dados
def selecionar_treino(n_por_classe: int, semente: int) -> pd.DataFrame:
    meta = pd.read_csv(v.baixar("ptbxl_database.csv"), index_col="ecg_id")
    meta["scp"] = meta["scp_codes"].apply(ast.literal_eval)
    meta["categoria"] = meta["scp"].apply(v.categoria)
    meta = meta[meta["strat_fold"].between(1, 8) & meta["categoria"].notna()]
    partes = []
    for cat in v.RISCO_ESPERADO:
        grupo = meta[meta["categoria"] == cat]
        k = min(n_por_classe, len(grupo))
        print(f"  treino {cat:7s}: {k} exames (disponíveis: {len(grupo)})")
        partes.append(grupo.sample(n=k, random_state=semente))
    return pd.concat(partes)


def extrair(df: pd.DataFrame, dsp, cache_csv: Path) -> pd.DataFrame:
    """Extrai FC/SDNN de cada exame; reaproveita o cache se já existir."""
    if cache_csv.exists():
        feito = pd.read_csv(cache_csv, index_col="ecg_id")
        if set(df.index) <= set(feito.index):
            return feito.loc[df.index]
    linhas = []
    for i, (ecg_id, row) in enumerate(df.iterrows(), 1):
        if i % 25 == 0:
            print(f"    {i}/{len(df)}")
        sinal, fs = v.carregar_sinal(row["filename_hr"])
        linhas.append({"ecg_id": ecg_id, "categoria": row["categoria"],
                       **features_seguras(dsp, sinal, fs)})
    out = pd.DataFrame(linhas).set_index("ecg_id")
    out.to_csv(cache_csv)
    return out


def features_seguras(dsp, sinal, fs) -> dict:
    try:
        return dsp.extract_features(sinal, fs)
    except CorruptedSignalException:
        return {"hr_medio_bpm": None, "hrv_sdnn_ms": None,
                "n_picos_detectados": 0, "qualidade_deteccao": "CORROMPIDO"}


def carregar_if4health(dsp) -> pd.DataFrame:
    linhas = []
    for pasta in sorted(p for p in IF4HEALTH_DIR.iterdir() if p.is_dir()):
        for arq in sorted(pasta.glob("*.txt")):
            sinal = [float(l) for l in arq.read_text().splitlines()
                     if l.strip() and not l.startswith("#")]
            linhas.append({"ecg_id": f"{pasta.name}/{arq.name}",
                           "categoria": pasta.name.lower(),
                           **features_seguras(dsp, sinal, IF4HEALTH_FS)})
    return pd.DataFrame(linhas).set_index("ecg_id")


# ---------------------------------------------------------------- avaliação
def avaliar(feats: pd.DataFrame, limiar: float) -> dict:
    clf = ThresholdRiskClassifier()
    clf.HRV_SDNN_ELEVADO_MS = limiar  # sobrescreve só nesta instância
    obtido = [clf.classify(r.to_dict())["risco_determinado"] for _, r in feats.iterrows()]
    esperado = [v.RISCO_ESPERADO[c] for c in feats["categoria"]]
    f1s = []
    for c in RISCOS:
        tp = sum(o == c and e == c for o, e in zip(obtido, esperado))
        fp = sum(o == c and e != c for o, e in zip(obtido, esperado))
        fn = sum(o != c and e == c for o, e in zip(obtido, esperado))
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * p * r / (p + r) if p + r else 0.0)
    acerto = np.array([o == e for o, e in zip(obtido, esperado)])
    por_cat = {cat: (acerto[feats["categoria"].values == cat].mean()
                     if (feats["categoria"] == cat).any() else float("nan"))
               for cat in v.RISCO_ESPERADO}
    return {"acc": acerto.mean(), "f1": float(np.mean(f1s)), "por_cat": por_cat}


def imprimir_comparacao(nome: str, feats: pd.DataFrame, novo: float) -> None:
    a, b = avaliar(feats, LIMIAR_ATUAL), avaliar(feats, novo)
    print(f"\n{nome} (N={len(feats)})")
    print(f"{'':12s} | {f'{LIMIAR_ATUAL} ms (atual)':>14s} | {f'{novo} ms (novo)':>14s}")
    print("-" * 46)
    for cat in v.RISCO_ESPERADO:
        print(f"{cat:12s} | {100*a['por_cat'][cat]:13.0f}% | {100*b['por_cat'][cat]:13.0f}%")
    print(f"{'Acurácia':12s} | {100*a['acc']:13.1f}% | {100*b['acc']:13.1f}%")
    print(f"{'F1 macro':12s} | {a['f1']:14.3f} | {b['f1']:14.3f}")


# ---------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-treino", type=int, default=100, help="exames por padrão no treino")
    ap.add_argument("--semente", type=int, default=42)
    args = ap.parse_args()
    dsp = NeuroKitSignalProcessor()

    print("1) TREINO (folds 1-8)")
    treino = extrair(selecionar_treino(args.n_treino, args.semente), dsp,
                     v.CACHE / f"features_treino_n{args.n_treino}_s{args.semente}.csv")

    grade = []
    for t in GRADE:
        r = avaliar(treino, t)
        grade.append({"limiar_ms": t, "f1_macro_treino": round(r["f1"], 4),
                      "acuracia_treino": round(r["acc"], 4)})
    with open("calibracao_ptbxl.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=grade[0].keys())
        w.writeheader()
        w.writerows(grade)
    melhor = max(grade, key=lambda g: g["f1_macro_treino"])
    novo = melhor["limiar_ms"]
    print(f"\n  Limiar escolhido no treino: {novo} ms "
          f"(F1 macro {melhor['f1_macro_treino']:.3f}, acurácia {100*melhor['acuracia_treino']:.1f}%)")

    print("\n2) TESTE (fold 10, os mesmos 80 exames da validação externa)")
    # compatível com as duas versões do validar_ptbxl.py (com ou sem --folds)
    import inspect
    if "folds" in inspect.signature(v.selecionar).parameters:
        sel_teste = v.selecionar(25, 42, [10])
    else:
        sel_teste = v.selecionar(25, 42)
    teste = extrair(sel_teste, dsp, v.CACHE / "features_teste_n25_s42.csv")
    imprimir_comparacao("PTB-XL teste", teste, novo)

    if IF4HEALTH_DIR.is_dir():
        print("\n3) IF4HEALTH (base de calibração original)")
        imprimir_comparacao("IF4Health", carregar_if4health(dsp), novo)

    print("\nGrade completa do treino: calibracao_ptbxl.csv")


if __name__ == "__main__":
    main()