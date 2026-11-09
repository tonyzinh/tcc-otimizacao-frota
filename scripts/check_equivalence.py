"""Verifica que o código reorganizado reproduz os resultados congelados (NÃO é novo teste científico: reexecução de equivalência).

  --synthetic   3 pares (cenário, semente) sintéticos contra ``reports/synthetic/dispatch_evaluation`` (não exige dados privados);
  --historical  1 dia real por período contra ``reports/historical/frozen_evaluation/execucao`` (exige TCC_REAL_DATA_AUTHORIZED=YES e dados locais);
  --analysis    regenera totais, contrastes e tabelas a partir dos Parquet congelados e compara com ``reports/historical/frozen_evaluation/analise``.

Não escreve em pastas congeladas; grava o resultado em ``reports/manifests/equivalencia_reorganizacao.json``.
Uso: python scripts/check_equivalence.py --synthetic --analysis [--historical --historical-days 2026-09-16,2026-10-01]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

FROZEN_SYNTH = Path("reports/synthetic/dispatch_evaluation")
FROZEN_HIST = Path("reports/historical/frozen_evaluation")
OUT = Path("reports/manifests/equivalencia_reorganizacao.json")


def _same(a, b) -> bool:
    return bool(a == b or (isinstance(a, float) and isinstance(b, float) and np.isnan(a) and np.isnan(b)))


def check_synthetic() -> dict:
    from tcc_frota.scenarios import catalog, runner

    world = runner.build_world(7)
    cases, ok = [], True
    for scenario_id, seed in (("S1", 20001), ("S3", 20007), ("S2_frota_escassa", 20040)):
        new = pd.DataFrame(runner.run_pair(catalog.SCENARIOS_BY_ID[scenario_id], seed, world))
        old = pd.read_parquet(FROZEN_SYNTH / f"cen={scenario_id}__sem={seed}.parquet")
        diffs = []
        for policy in new.politica:
            a = new[new.politica == policy].iloc[0]
            b = old[old.politica == {"A": "R0"}.get(policy, policy)].iloc[0]
            for col in ("pedidos", "atendidos", "km_vazio_total", "km_busca", "espera_media_s", "espera_p90_s", "n_veiculos"):
                if not _same(a[col], b[col]):
                    diffs.append(f"{policy}.{col}: {a[col]} != {b[col]}")
        ok &= not diffs
        cases.append({"cenario": scenario_id, "semente": seed, "diferencas": diffs})
    return {"equivalente": ok, "casos": cases}


def check_historical(days: list[str]) -> dict:
    from tcc_frota.simulation import historical as hs

    cases, ok = [], True
    for day in days:
        period = "replicacao" if day.startswith("2026-09") else "final"
        t0 = time.time()
        new = pd.DataFrame(hs.run_day(day))
        old = pd.read_parquet(FROZEN_HIST / "execucao" / "grupo_B" / period / f"dia={day}.parquet")
        cols = [c for c in old.columns if c not in ("tempo_plano_s", "esperas_s")]
        diffs = []
        for name in new.config:
            a, b = new[new.config == name].iloc[0], old[old.config == name].iloc[0]
            diffs += [f"{name}.{c}" for c in cols if not _same(a[c], b[c])]
            if not np.array_equal(np.array(a.esperas_s), np.array(b.esperas_s)):
                diffs.append(f"{name}.esperas_s")
        ok &= not diffs
        cases.append({"dia": day, "diferencas": diffs, "segundos": round(time.time() - t0, 1)})
    return {"equivalente": ok, "casos": cases}


def check_analysis() -> dict:
    from tcc_frota.metrics import historical as hi

    report, ok = {}, True
    for period in hi.PERIODS:
        df = hi.load_days(FROZEN_HIST / "execucao" / "grupo_B" / period)
        new = hi.absolute_totals(df)
        old = pd.read_csv(FROZEN_HIST / "analise" / f"{period}_absolutos.csv")
        same_totals = bool(
            new.atendidos.tolist() == old.atendidos.tolist() and np.allclose(new.km_vazio_total, old.km_vazio_total, rtol=0, atol=1e-6)
        )
        old_c = json.loads((FROZEN_HIST / "analise" / f"{period}_contrastes.json").read_text(encoding="utf-8"))
        key = "variacao_km_vazio_pct (negativo = reducao)"
        same_contrasts = True
        for a, b, role in hi.CONTRASTS:
            n = hi.paired_contrast(df, a, b, role)
            r = next(x for x in old_c if x["contraste"] == n["contraste"])
            same_contrasts &= bool(
                abs(n[key] - r[key]) < 1e-6
                and np.allclose(n["ic95_diferenca_media_diaria_km"], r["ic95_diferenca_media_diaria_km"], atol=1e-6)
                and n["classe"] == r["classe"]
            )
        report[period] = {"totais_iguais": same_totals, "contrastes_iguais": same_contrasts}
        ok &= same_totals and same_contrasts
    return {"equivalente": ok, "periodos": report}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--historical", action="store_true")
    ap.add_argument("--historical-days", default="2026-09-16,2026-10-01")
    ap.add_argument("--analysis", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT, help="arquivo JSON de saída (não sobrescreva evidências anteriores)")
    a = ap.parse_args()
    result: dict = {
        "executado_em": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "observacao": "reexecução de equivalência; não é novo teste científico",
    }
    if a.synthetic:
        result["sintetico"] = check_synthetic()
    if a.analysis:
        result["analise"] = check_analysis()
    if a.historical:
        from tcc_frota.data.authorization import authorize

        authorize("real")
        result["historico"] = check_historical(a.historical_days.split(","))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    parts = [v["equivalente"] for k, v in result.items() if isinstance(v, dict)]
    return 0 if parts and all(parts) else 1


if __name__ == "__main__":
    raise SystemExit(main())
