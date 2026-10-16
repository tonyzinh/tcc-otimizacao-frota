"""Gold local da v2, equivalente aos notebooks `nb_gld_*_v2` (sem previsão nem algoritmo)."""
from __future__ import annotations

import bisect
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import timedelta
from statistics import median, quantiles

from tcc_frota.v2 import rules
from tcc_frota.v2.silver import Silver, _km

SESSION_GAP = timedelta(minutes=20)
SNAPSHOT_STEP = timedelta(minutes=10)


def summary(values: list[float]) -> dict[str, float | int | None]:
    values = sorted(v for v in values if v is not None)
    if len(values) < 4:
        return {"n": len(values), "p10": None, "p25": None, "p50": None, "p75": None, "p90": None}
    dec = quantiles(values, n=10)
    qua = quantiles(values, n=4)
    return {"n": len(values), "p10": dec[0], "p25": qua[0], "p50": qua[1], "p75": qua[2], "p90": dec[8]}


@dataclass
class Gold:
    demanda_zona_hora: list[dict] = field(default_factory=list)
    replay_pedidos: list[dict] = field(default_factory=list)
    frota_snapshot: list[dict] = field(default_factory=list)
    frota_sessoes: list[dict] = field(default_factory=list)
    frota_motorista_hora: list[dict] = field(default_factory=list)
    calibracao: list[dict] = field(default_factory=list)
    km_vazio: list[dict] = field(default_factory=list)
    qualidade: list[dict] = field(default_factory=list)
    filtros: Counter = field(default_factory=Counter)


def replay_universe(silver: Silver, gold: Gold) -> None:
    """Pedidos imediatos de demanda na caixa: universo do replay e da previsão."""
    for req in silver.solicitacoes:
        f = gold.filtros
        f["total"] += 1
        if not req["fl_imediata"]:
            f["excluido_agendada"] += 1
            continue
        if not req["fl_demanda"]:
            f[f"excluido_nao_demanda:{req['grupo_desfecho']}"] += 1
            continue
        if not req["fl_na_caixa"]:
            f["excluido_fora_da_caixa"] += 1
            continue
        if req["ts_base"] is None:
            f["excluido_sem_carimbo"] += 1
            continue
        f["universo_replay"] += 1
        patience_obs = req["s_registro_ate_status_final"] if req["grupo_desfecho"] == "cancelada_solicitante_pre_aceite" else None
        gold.replay_pedidos.append({
            "codigo": req["codigo"],
            "tag_lote": req["tag_lote"],
            "ts_pedido": req["ts_base"],
            "data_local": req["data_base"],
            "hora_local": req["hora_base"],
            "tipo_servico": req["tipo_servico"],
            "lat_origem": req["lat_origem"], "lon_origem": req["lon_origem"],
            "h3_r7_origem": req["h3_r7_origem"], "h3_r8_origem": req["h3_r8_origem"],
            "lat_destino": req["lat_destino"], "lon_destino": req["lon_destino"],
            "grupo_desfecho": req["grupo_desfecho"],
            "fl_aceito": req["fl_aceito"],
            "fl_cancelada_pos_aceite": req["grupo_desfecho"].startswith("cancelada_pos_aceite"),
            "motorista_pseud": req["motorista_pseud"],
            "ts_aceite": req["ts_aceite"], "ts_chegada": req["ts_chegada"], "ts_fim": req["ts_fim"],
            "dur_viagem_obs_s": req["dur_viagem_s"] if req["status"] == "CorridaEncerrada" else None,
            "dist_percorrida_km": req["dist_percorrida_km"],
            "s_espera_ate_desistir": patience_obs,
            "s_registro_ate_chegada": req["s_registro_ate_chegada"],
        })


def demand_by_zone_hour(gold: Gold) -> None:
    cells: dict[tuple, Counter] = defaultdict(Counter)
    for req in gold.replay_pedidos:
        key = (req["data_local"], req["hora_local"], req["h3_r7_origem"], req["h3_r8_origem"])
        cells[key]["qtd_demanda"] += 1
        cells[key]["qtd_aceitas"] += req["fl_aceito"]
        cells[key]["qtd_nao_atendidas"] += req["grupo_desfecho"] in ("nao_atendida", "nao_atendida_limite_espera")
        cells[key]["qtd_canceladas_pre_aceite"] += req["grupo_desfecho"] == "cancelada_solicitante_pre_aceite"
    gold.demanda_zona_hora = [
        {"data_local": d, "hora_local": h, "h3_r7": r7, "h3_r8": r8, **dict(c)}
        for (d, h, r7, r8), c in sorted(cells.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2] or "", kv[0][3] or ""))
    ]


def fleet_tables(silver: Silver, gold: Gold) -> None:
    by_driver: dict[str, list[dict]] = defaultdict(list)
    for row in silver.posicoes:
        if row["motorista_pseud"] is None:
            continue
        keep = {k: row[k] for k in ("tag_lote", "ts_snapshot", "motorista_pseud", "estado", "passageiro_embarcado",
                                    "lat", "lon", "h3_r7", "h3_r8", "fl_coordenada_valida", "fl_posicao_atual")}
        gold.frota_snapshot.append(keep)
        by_driver[row["motorista_pseud"]].append(keep)
    hours: dict[tuple, Counter] = defaultdict(Counter)
    for driver, rows in by_driver.items():
        rows.sort(key=lambda r: r["ts_snapshot"])
        seq = 0
        current: list[dict] = []

        def close() -> None:
            nonlocal seq
            if not current:
                return
            seq += 1
            first = next((r for r in current if r["fl_coordenada_valida"]), current[0])
            last = next((r for r in reversed(current) if r["fl_coordenada_valida"]), current[-1])
            gold.frota_sessoes.append({
                "motorista_pseud": driver, "seq_sessao": seq,
                "ts_inicio": current[0]["ts_snapshot"], "ts_fim": current[-1]["ts_snapshot"] + SNAPSHOT_STEP,
                "lat_inicio": first["lat"], "lon_inicio": first["lon"], "h3_r7_inicio": first["h3_r7"],
                "lat_fim": last["lat"], "lon_fim": last["lon"], "h3_r7_fim": last["h3_r7"],
                "qtd_fotos": len(current),
            })

        for row in rows:
            working = row["estado"] in rules.WORKING_STATES
            if working and current and row["ts_snapshot"] - current[-1]["ts_snapshot"] > SESSION_GAP:
                close()
                current = []
            if working:
                current.append(row)
                local = row["ts_snapshot"]
                hours[(driver, local.date(), local.hour)]["min_trabalhando"] += 10
                hours[(driver, local.date(), local.hour)]["min_livre"] += 10 * (row["estado"] == 1)
            else:
                close()
                current = []
        close()
    gold.frota_motorista_hora = [
        {"motorista_pseud": d, "data_local": day, "hora_local": h, **dict(c)}
        for (d, day, h), c in sorted(hours.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2]))
    ]


def calibration(silver: Silver, gold: Gold) -> None:
    rows: list[dict] = []
    reqs = {r["codigo"]: r for r in silver.solicitacoes}
    # (1) Fator rua/reta da viagem: distância percorrida registrada sobre reta origem-destino.
    trip_ratio = []
    for r in silver.solicitacoes:
        if r["status"] == "CorridaEncerrada" and r["dist_percorrida_km"] and r["lat_destino"] is not None:
            reta = _km(r["lat_origem"], r["lon_origem"], r["lat_destino"], r["lon_destino"])
            if reta >= 0.5:
                trip_ratio.append(r["dist_percorrida_km"] / reta)
    rows.append({"medida": "fator_rua_reta_viagem", "unidade": "razao",
                 "fonte": "nU_DISTPERCORRIDA / Haversine(origem, destino solicitado), encerradas, reta >= 0,5 km",
                 **summary(trip_ratio)})
    # (2) Fator rua/reta da busca e velocidade até o passageiro: distMotorista (histórico).
    positions: dict[str, list[dict]] = defaultdict(list)
    for p in silver.posicoes:
        if p["motorista_pseud"] and p["fl_coordenada_valida"]:
            positions[p["motorista_pseud"]].append(p)
    for v in positions.values():
        v.sort(key=lambda p: p["ts_snapshot"])
    times = {d: [p["ts_snapshot"] for p in v] for d, v in positions.items()}
    pick_ratio, pick_speed, pick_speed_reta = [], [], []
    for h in silver.historico:
        req = reqs.get(h["codigo"])
        if not req or not h["dist_motorista_m"] or not req["ts_aceite"] or not req["ts_chegada"]:
            continue
        seconds = (req["ts_chegada"] - req["ts_aceite"]).total_seconds()
        road_km = h["dist_motorista_m"] / 1000
        if seconds >= 60 and road_km > 0.2:
            pick_speed.append(road_km / (seconds / 3600))
        driver = h["motorista_pseud"]
        if driver in positions and req["lat_origem"] is not None:
            i = bisect.bisect_right(times[driver], req["ts_aceite"]) - 1
            if i >= 0:
                snap = positions[driver][i]
                if (req["ts_aceite"] - snap["ts_snapshot"]).total_seconds() <= 600 and snap["estado"] in (1, 4):
                    reta = _km(snap["lat"], snap["lon"], req["lat_origem"], req["lon_origem"])
                    if reta >= 0.5:
                        pick_ratio.append(road_km / reta)
    rows.append({"medida": "fator_rua_reta_busca", "unidade": "razao",
                 "fonte": "distMotorista / Haversine(foto livre anterior ao aceite, origem), reta >= 0,5 km",
                 **summary(pick_ratio)})
    rows.append({"medida": "velocidade_busca", "unidade": "km/h (distância por rua)",
                 "fonte": "distMotorista / (chegada - aceite), tempo >= 60 s",
                 **summary(pick_speed)})
    # (3) Tempos observados nas imediatas de demanda.
    by_group: dict[str, list[float]] = defaultdict(list)
    search = []
    for r in gold.replay_pedidos:
        if r["s_registro_ate_chegada"] is not None and r["grupo_desfecho"] == "atendida":
            search.append(r["s_registro_ate_chegada"])
    for r in silver.solicitacoes:
        if r["fl_imediata"] and r["fl_demanda"] and r["fl_na_caixa"] and r["s_registro_ate_status_final"] is not None:
            by_group[r["grupo_desfecho"]].append(r["s_registro_ate_status_final"])
    rows.append({"medida": "tempo_busca_registro_ate_chegada", "unidade": "s",
                 "fonte": "imediatas encerradas na caixa", **summary(search)})
    for group in ("nao_atendida", "nao_atendida_limite_espera", "cancelada_solicitante_pre_aceite"):
        rows.append({"medida": f"tempo_registro_ate_{group}", "unidade": "s",
                     "fonte": "logStatus do status final", **summary(by_group.get(group, []))})
    gold.calibracao = rows


def empty_km(silver: Silver, gold: Gold) -> None:
    """Descritivo diário: busca observada estimada (foto × fator), separada por fonte."""
    days: dict[tuple, Counter] = defaultdict(Counter)
    for c in silver.corridas:
        if not c["fl_imediata"] or c["data_base"] is None:
            continue
        key = (c["data_base"],)
        days[key]["corridas_encerradas"] += 1
        if c["km_busca_estimado"] is not None:
            days[key]["corridas_com_km_busca"] += 1
            days[key]["km_busca_estimado"] += c["km_busca_estimado"]
        if c["dist_percorrida_km"] is not None:
            days[key]["km_com_passageiro_registrado"] += c["dist_percorrida_km"]
    gold.km_vazio = [{"data_local": k[0], "parcela_busca": "estimada: reta da foto x fator", **dict(v)}
                     for k, v in sorted(days.items())]


def quality(silver: Silver, gold: Gold) -> None:
    out = []
    months: dict[str, list[dict]] = defaultdict(list)
    for r in silver.solicitacoes:
        months[r["ts_registro"].strftime("%Y-%m") if r["ts_registro"] else "sem_data"].append(r)
    fields = ("lat_origem", "lat_destino", "ts_aceite", "ts_chegada", "ts_inicio", "ts_fim", "dur_viagem_s",
              "dist_percorrida_km", "motorista_pseud", "lat_destino_real", "nu_dr_real_pendente")
    for month, rows in sorted(months.items()):
        enc = [r for r in rows if r["status"] == "CorridaEncerrada"]
        out.append({"grupo": "volume", "mes": month, "medida": "solicitacoes", "valor": len(rows)})
        out.append({"grupo": "volume", "mes": month, "medida": "imediatas", "valor": sum(r["fl_imediata"] for r in rows)})
        out.append({"grupo": "volume", "mes": month, "medida": "fora_da_caixa", "valor": sum(not r["fl_na_caixa"] for r in rows)})
        out.append({"grupo": "qualidade", "mes": month, "medida": "encerradas_tempos_ordenados_pct",
                    "valor": 100 * sum(r["fl_tempos_ordenados"] for r in enc) / max(1, len(enc))})
        for f in fields:
            out.append({"grupo": "cobertura_encerradas_pct", "mes": month, "medida": f,
                        "valor": 100 * sum(r[f] is not None for r in enc) / max(1, len(enc))})
        nao = [r for r in rows if r["status"] == "NaoAtendida"]
        out.append({"grupo": "qualidade", "mes": month, "medida": "nao_atendidas_com_origem_pct",
                    "valor": 100 * sum(r["lat_origem"] is not None for r in nao) / max(1, len(nao))})
        for status, n in Counter(r["status"] for r in rows).items():
            out.append({"grupo": "status", "mes": month, "medida": status, "valor": n})
    for key, n in sorted(gold.filtros.items()):
        out.append({"grupo": "filtro_replay", "mes": "todos", "medida": key, "valor": n})
    by_tag: dict[str, list] = defaultdict(list)
    for s in silver.sumarios:
        if s["fl_tem_foto"]:
            by_tag[s["tag_lote"]].append(s["fl_consistente_com_posicoes"])
    for tag, flags in sorted(by_tag.items()):
        out.append({"grupo": "frota", "mes": tag, "medida": "fotos_consistentes_com_sumario_pct",
                    "valor": 100 * sum(flags) / max(1, len(flags))})
    snaps: dict[str, list] = defaultdict(list)
    for p in gold.frota_snapshot:
        snaps[p["tag_lote"]].append(p["ts_snapshot"])
    for tag, ts in sorted(snaps.items()):
        uniq = sorted(set(ts))
        gaps = [(b - a).total_seconds() / 60 for a, b in zip(uniq, uniq[1:])]
        out.append({"grupo": "frota", "mes": tag, "medida": "lacunas_foto_maior_que_10min",
                    "valor": sum(g > 10.5 for g in gaps)})
        out.append({"grupo": "frota", "mes": tag, "medida": "maior_lacuna_foto_min", "valor": max(gaps) if gaps else None})
    dormida = [d["km_reta_dormida"] for d in silver.dormida if d["km_reta_dormida"] is not None]
    s = summary(dormida)
    for k in ("n", "p50", "p90"):
        out.append({"grupo": "dormida", "mes": "todos", "medida": f"km_reta_ultima_D_primeira_D1_{k}", "valor": s[k]})
    gold.qualidade = out


def build_gold(silver: Silver) -> Gold:
    gold = Gold()
    replay_universe(silver, gold)
    demand_by_zone_hour(gold)
    fleet_tables(silver, gold)
    calibration(silver, gold)
    empty_km(silver, gold)
    quality(silver, gold)
    return gold
