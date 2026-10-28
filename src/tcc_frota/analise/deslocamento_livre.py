"""Fase E: medida descritiva do deslocamento de motoristas com status "livre" (sem interpretar a causa).

A partir das fotos da frota (a cada 10 min), pares consecutivos do mesmo motorista com estado 1 → 1 e
intervalo ≤ 11 min, iniciados na janela 04–11h: distância em linha reta e × 1,4 por dia, e fração dos
intervalos com deslocamento > 0,5 km. Também a cobertura descritiva de `nU_DR_REAL` e
`tX_H3INDEX_REPOSICIONAMENTO_REAL` nas corridas encerradas (semântica não confirmada pela empresa).
Os identificadores de motorista das fotos e das corridas não coincidem: nada é cruzado entre as fontes.
Só agregados por mês saem do módulo.
"""

from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from statistics import mean, median

from tcc_frota.v2.sim import reta_km

MONTHS = {"mar2026": (2026, 3), "set2026": (2026, 9)}
WINDOW = (4, 11)
MAX_GAP = timedelta(minutes=11)
FACTOR = 1.4
MOVE_KM = 0.5


def free_movement(snapshots: list[dict]) -> list[dict]:
    by_driver: dict[str, list[dict]] = defaultdict(list)
    for p in snapshots:
        if p["fl_coordenada_valida"] and p["motorista_pseud"]:
            by_driver[p["motorista_pseud"]].append(p)
    per_day: dict[tuple[str, object], float] = defaultdict(float)
    days_seen: dict[str, set] = defaultdict(set)
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for rows in by_driver.values():
        rows.sort(key=lambda r: r["ts_snapshot"])
        for a, b in zip(rows, rows[1:]):
            t = a["ts_snapshot"]
            month = next((k for k, (y, m) in MONTHS.items() if t.year == y and t.month == m), None)
            if month is None or not (WINDOW[0] <= t.hour < WINDOW[1]):
                continue
            days_seen[month].add(t.date())
            if a["estado"] != 1 or b["estado"] != 1 or b["ts_snapshot"] - t > MAX_GAP:
                continue
            km = reta_km(a["lat"], a["lon"], b["lat"], b["lon"])
            per_day[(month, t.date())] += km
            counts[month][0] += 1
            counts[month][1] += km > MOVE_KM
    out = []
    for month in MONTHS:
        days = sorted(days_seen[month])
        vals = [per_day.get((month, d), 0.0) for d in days]
        n, moved = counts[month]
        out.append(
            {
                "mes": month,
                "dias_com_fotos_na_janela": len(days),
                "intervalos_livre_livre": n,
                "km_dia_reta_media": mean(vals) if vals else float("nan"),
                "km_dia_reta_mediana": median(vals) if vals else float("nan"),
                "km_dia_x1_4_media": FACTOR * mean(vals) if vals else float("nan"),
                "fracao_intervalos_mov_maior_0_5km_pct": 100 * moved / n if n else float("nan"),
            }
        )
    return out


def field_coverage(solicitacoes: list[dict]) -> list[dict]:
    out = []
    for month, (y, m) in MONTHS.items():
        rows = [
            r
            for r in solicitacoes
            if r["status"] == "CorridaEncerrada" and r["data_base"] and r["data_base"].year == y and r["data_base"].month == m
        ]
        dr = [r["nu_dr_real_pendente"] for r in rows if r["nu_dr_real_pendente"] is not None]
        nums = sorted(float(v) for v in dr if isinstance(v, (int, float)))
        out.append(
            {
                "mes": month,
                "corridas_encerradas": len(rows),
                "nu_dr_real_preenchido_pct": 100 * len(dr) / len(rows) if rows else float("nan"),
                "nu_dr_real_mediana": median(nums) if nums else float("nan"),
                "nu_dr_real_p90": nums[int(0.9 * (len(nums) - 1))] if nums else float("nan"),
                "h3_reposicionamento_real_preenchido_pct": 100 * sum(r["fl_h3_repos_real_pendente"] for r in rows) / len(rows)
                if rows
                else float("nan"),
            }
        )
    return out


def write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as h:
        w = csv.DictWriter(h, fieldnames=list(rows[0]))
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})


def main() -> int:
    os.environ.setdefault("TCC_REAL_DATA_AUTHORIZED", "YES")
    from tcc_frota.algoritmos.bateria import build_study

    study = build_study(Path("data/raw"))
    mov = free_movement(study.gold.frota_snapshot)
    cov = field_coverage(study.silver.solicitacoes)
    write(Path("resultados/seletivo/deslocamento_livre.csv"), mov)
    write(Path("resultados/seletivo/cobertura_campos_reposicionamento.csv"), cov)
    for r in mov + cov:
        print(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
