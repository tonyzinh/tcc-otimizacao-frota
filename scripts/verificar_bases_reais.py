"""Verificação de integridade e cobertura das bases reais já extraídas (`data/extraido/v1_viagens`). Só metadados de Parquet e contagens; nada
individual (sem IDs, sem coordenadas) vai para a saída. Não consulta nenhum serviço externo nem lê `data/raw`.

Confere: (1) cada partição `dt=*` abre e tem esquema; (2) linhas por partição = linhas gravadas no LOG_LOTES (último registro do lote);
(3) cobertura de dias por entidade e por período do calendário; (4) esquema de pseudonimização registrado.
Uso: python scripts/verificar_bases_reais.py [--saida reports/revisao/verificacao_bases_reais.json]
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import pyarrow.parquet as pq

RAIZ = Path("data/extraido/v1_viagens")
PERIODOS = {
    "treino_01fev_15mar": (date(2026, 2, 1), date(2026, 3, 15)),
    "validacao_16_31mar": (date(2026, 3, 16), date(2026, 3, 31)),
    "replicacao_16_30set": (date(2026, 9, 16), date(2026, 9, 30)),
    "final_01_25out": (date(2026, 10, 1), date(2026, 10, 25)),
}


def _dias(a: date, b: date) -> list[str]:
    return [(a + timedelta(days=i)).isoformat() for i in range((b - a).days + 1)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", default="reports/revisao/verificacao_bases_reais.json")
    a = ap.parse_args()
    log: dict[tuple[str, str, str], int] = {}
    if (RAIZ / "LOG_LOTES.jsonl").exists():
        for lin in (RAIZ / "LOG_LOTES.jsonl").read_text(encoding="utf-8").splitlines():
            if lin.strip():
                r = json.loads(lin)
                if "linhas" in r:
                    log[(r["fonte"], r["entidade"], r["lote"])] = int(r["linhas"])  # o último registro do lote prevalece
    res: dict = {"entidades": {}, "problemas": [], "pseudonimizacao": None}
    pj = RAIZ / "PSEUDONIMIZACAO.json"
    if pj.exists():
        p = json.loads(pj.read_text(encoding="utf-8"))
        res["pseudonimizacao"] = {k: p[k] for k in ("esquema", "chave_id", "hex") if k in p}
    for fonte in ("ods", "es"):
        base = RAIZ / fonte
        if not base.exists():
            continue
        for ent in sorted(x for x in base.iterdir() if x.is_dir()):
            dias: dict[str, int] = defaultdict(int)
            esquemas = set()
            for part in sorted(ent.glob("dt=*")):
                dia = part.name[3:]
                for f in sorted(p for p in part.glob("*.parquet") if p.name != "rejeitados.parquet"):  # rejeitados ficam à parte
                    try:
                        md = pq.ParquetFile(f)
                        dias[dia] += md.metadata.num_rows
                        esquemas.add(tuple(md.schema_arrow.names))
                    except Exception as e:
                        res["problemas"].append({"arquivo": f"{fonte}/{ent.name}/{part.name}/{f.name}", "erro": str(e)[:160]})
                lg = log.get((fonte, ent.name, dia))
                if lg is not None and lg != dias[dia]:
                    res["problemas"].append({"entidade": f"{fonte}/{ent.name}", "dia": dia, "linhas_parquet": dias[dia], "linhas_log": lg})
            cob = {}
            for nome, (d0, d1) in PERIODOS.items():
                alvo = _dias(d0, d1)
                com = [d for d in alvo if dias.get(d, 0) > 0]
                cob[nome] = {
                    "dias_periodo": len(alvo),
                    "dias_com_dado": len(com),
                    "primeiro": com[0] if com else None,
                    "ultimo": com[-1] if com else None,
                }
            res["entidades"][f"{fonte}/{ent.name}"] = {
                "particoes": len(dias),
                "linhas_total": int(sum(dias.values())),
                "esquemas_distintos": len(esquemas),
                "colunas": sorted(next(iter(esquemas))) if len(esquemas) == 1 else None,
                "cobertura": cob,
            }
    Path(a.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(a.saida).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in res["entidades"].items():
        c = v["cobertura"]
        print(
            k,
            v["linhas_total"],
            {n: f"{x['dias_com_dado']}/{x['dias_periodo']}" for n, x in c.items()},
            "esquemas",
            v["esquemas_distintos"],
        )
    print("problemas:", len(res["problemas"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
