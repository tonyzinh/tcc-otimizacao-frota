"""Relatório de qualidade e reconciliação dos lotes extraídos (agregados; sem linhas individuais).

Uso: python -m tcc_frota.extracao.qualidade --inicio 2026-03-10 --fim 2026-03-10
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from tcc_frota.extracao.saida import RAIZ_PADRAO, agora_utc, versao_codigo

SAIDA_PADRAO = Path(__file__).resolve().parents[3] / "reports" / "extracao_v1_viagens"


def _ler(raiz: Path, fonte: str, entidade: str, dias: list[str]) -> pd.DataFrame:
    partes = [pd.read_parquet(p) for d in dias if (p := raiz / fonte / entidade / f"dt={d}" / "part-000.parquet").is_file()]
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()


def _vc(serie) -> dict:
    return {str(k): int(v) for k, v in serie.value_counts().items()}


def _manifestos(raiz: Path, dias: list[str]) -> list[dict]:
    out = []
    for m in sorted(raiz.glob("*/*/dt=*/manifest.json")):
        d = json.loads(m.read_text(encoding="utf-8"))
        if d["lote"] in dias or d["lote"] == "snapshot":
            out.append({k: d[k] for k in ("fonte", "entidade", "lote", "linhas", "rejeitadas", "sha256", "filtro", "limites", "fuso")})
    return out


def relatorio(raiz: Path, dias: list[str]) -> dict:
    sol = _ler(raiz, "ods", "solicitacao", dias)
    st = _ler(raiz, "ods", "status_solicitacao", dias)
    cob = _ler(raiz, "ods", "telemetria_cobli", dias)
    pos = _ler(raiz, "es", "posicao_ofertas", dias)
    r: dict = {"gerado_em_utc": agora_utc(), "codigo": versao_codigo(), "dias": dias, "lotes": _manifestos(raiz, dias)}
    if len(sol):
        r["solicitacao"] = {
            "linhas": len(sol),
            "status": _vc(sol["tx_status"]),
            "servicos": _vc(sol["cd_tipo_servico"]),
            "regioes": _vc(sol["cd_regiao"]),
            "nulos_pct": {c: round(float(sol[c].isna().mean() * 100), 1) for c in ("cd_motorista", "cd_veiculo", "dt_fim_realizada", "nu_dr_real", "nu_distancia_aceite_cheguei", "nu_distpercorrida")},
            "tx_tipo_prime": _vc(sol["tx_tipo_prime"].fillna("(nulo)")),
            "tx_modelo_solicitacao": _vc(sol["tx_modelo_solicitacao"].fillna("(nulo)")),
            "chave_unica": bool(sol["cd_solicitacao"].is_unique),
        }
        enc = sol[sol["tx_status"] == "CorridaEncerrada"]
        ordem_ok = (enc["dt_inicio_realizada"].dropna() <= enc["dt_fim_realizada"].dropna()).mean() if len(enc) else None
        r["solicitacao"]["encerradas"] = {
            "n": len(enc),
            "km_corrida": round(float(enc["nu_distpercorrida"].sum()) / 1000, 1),
            "km_aproximacao_aceite_cheguei": round(float(enc["nu_distancia_aceite_cheguei"].sum()) / 1000, 1),
            "inicio_antes_do_fim_pct": None if ordem_ok is None else round(float(ordem_ok) * 100, 1),
        }
    if len(st) and len(sol):
        r["status_solicitacao"] = {"linhas": len(st), "orfas_sem_solicitacao": int((~st["cd_solicitacao"].isin(sol["cd_solicitacao"])).sum()), "status": _vc(st["tx_status"])}
    if len(cob):
        t = cob[cob["type"] == "trips"]
        r["cobli"] = {
            "linhas": len(cob), "trips": len(t), "stops": int((cob["type"] == "stops").sum()), "placas": int(cob["license_plate"].nunique()),
            "km_trips": round(float(t["distance_in_meters"].sum()) / 1000, 1),
            "trips_sem_motorista_pct": round(float(t["driver_id"].isna().mean() * 100), 1),
            "distancia_nula_ou_zero_pct": round(float((t["distance_in_meters"].fillna(0) <= 0).mean() * 100), 1),
            "fim_antes_inicio": int((t["end_address_datetime"] < t["start_address_datetime"]).sum()),
        }
        if "solicitacao" in r:
            enc = r["solicitacao"]["encerradas"]
            r["reconciliacao_km_um_dia"] = {
                "cobli_trips_km": r["cobli"]["km_trips"],
                "corridas_km + aproximacao_km": round(enc["km_corrida"] + enc["km_aproximacao_aceite_cheguei"], 1),
                "residuo_km": round(r["cobli"]["km_trips"] - enc["km_corrida"] - enc["km_aproximacao_aceite_cheguei"], 1),
                "aviso": "Comparação agregada de um dia, sem casar viagem a viagem; resíduo não é KM morto medido (inclui circulação, retorno, erros de grupo/placa, corridas não encerradas).",
            }
    if len(pos):
        r["posicao_ofertas"] = {
            "linhas": len(pos), "motoristas": int(pos["cd_motorista"].nunique()), "snapshots": int(pos["doc_codigo"].nunique()),
            "status": _vc(pos["status"]),
            "sem_gps_pct": round(float(pos["latitude"].isna().mean() * 100), 1),
            "defasagem_gps_mediana_s": float((pos["event_time"] - pos["data_posicao_gps"]).dt.total_seconds().median()),
        }
    return r


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="tcc_frota.extracao.qualidade")
    p.add_argument("--inicio", required=True)
    p.add_argument("--fim", required=True)
    p.add_argument("--raiz", default=str(RAIZ_PADRAO))
    p.add_argument("--saida", default=str(SAIDA_PADRAO))
    a = p.parse_args(argv)
    dias = [d.strftime("%Y-%m-%d") for d in pd.date_range(a.inicio, a.fim)]
    rel = relatorio(Path(a.raiz), dias)
    saida = Path(a.saida)
    saida.mkdir(parents=True, exist_ok=True)
    alvo = saida / f"qualidade_{a.inicio}_{a.fim}.json"
    alvo.write_text(json.dumps(rel, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in rel.items() if k != "lotes"}, ensure_ascii=False, indent=1, default=str))
    print("->", alvo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
