"""Silver local da v2, equivalente aos notebooks `nb_slv_*_v2`.

Linhas são dicionários com tipos Python. Coordenadas de origem/destino de passageiros saem com
3 casas; identificadores de motorista saem pseudonimizados; nenhuma função imprime linhas.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime

from tcc_frota.distance import haversine_km
from tcc_frota.models import Position
from tcc_frota.v2 import rules
from tcc_frota.v2.raw import Batch, iter_hits


def _km(lat1, lon1, lat2, lon2) -> float:
    return haversine_km(Position("a", lat1, lon1), Position("b", lat2, lon2))


@dataclass
class Silver:
    solicitacoes: list[dict] = field(default_factory=list)
    status: list[dict] = field(default_factory=list)
    historico: list[dict] = field(default_factory=list)
    posicoes: list[dict] = field(default_factory=list)
    sumarios: list[dict] = field(default_factory=list)
    dormida: list[dict] = field(default_factory=list)
    corridas: list[dict] = field(default_factory=list)
    losses: Counter = field(default_factory=Counter)
    ingested: Counter = field(default_factory=Counter)


def _final_status_time(logs: list[dict], status: str) -> datetime | None:
    times = [rules.parse_ts(item.get("dT_REGISTRO")) for item in logs if item.get("tX_STATUS") == status]
    times = [t for t in times if t is not None]
    return max(times) if times else None


def request_row(source: dict, tag: str, file_name: str, page: int, salt: str) -> dict:
    status = source.get("tX_STATUS")
    rule = rules.treatment(status)
    lat_raw = rules.coordinate(source.get("tX_ORIGEM_LAT"))
    lon_raw = rules.coordinate(source.get("tX_ORIGEM_LNG"))
    dlat_raw = rules.coordinate(source.get("tX_DESTINO_LAT"))
    dlon_raw = rules.coordinate(source.get("tX_DESTINO_LNG"))
    rlat = rules.coordinate(source.get("tX_DESTINOREAL_LAT"))
    rlon = rules.coordinate(source.get("tX_DESTINOREAL_LNG"))
    registro = rules.parse_ts(source.get("dT_REGISTRO"))
    aceite = rules.parse_ts(source.get("dT_ACEITE_MOTORISTA"))
    chegada = rules.parse_ts(source.get("dT_CHEGADA_MOTORISTA"))
    inicio = rules.parse_ts(source.get("dT_INICIO_REALIZADA"))
    fim = rules.parse_ts(source.get("dT_FIM_REALIZADA"))
    logs = source.get("logStatus") or []
    final_at = _final_status_time(logs, status) if status else None
    basis, base_at = rules.demand_time_basis(source)
    trip_s = rules.trip_seconds(source.get("tX_DURACAO"))
    dist = source.get("nU_DISTPERCORRIDA")
    return {
        "codigo": int(source["codigo"]),
        "tag_lote": tag,
        "arquivo_origem": file_name,
        "pagina": page,
        "status": status,
        "grupo_desfecho": rule.grupo,
        "fl_demanda": rule.demanda,
        "fl_aceito": rule.aceito,
        "fl_imediata": rules.is_immediate(source),
        "fl_na_caixa": rules.in_box(lat_raw, lon_raw),
        "tipo_solicitacao": source.get("tX_TP_SOLICITACAO"),
        "tipo_servico": source.get("cD_TIPO_SERVICO"),
        "ts_registro": registro,
        "ts_agendamento": rules.parse_ts(source.get("dT_AGENDAMENTO")),
        "ts_aceite": aceite,
        "ts_chegada": chegada,
        "ts_inicio": inicio,
        "ts_fim": fim,
        "ts_status_final": final_at,
        "base_temporal": basis,
        "ts_base": base_at,
        "data_base": base_at.date() if base_at else None,
        "hora_base": base_at.hour if base_at else None,
        "lat_origem": rules.round3(lat_raw),
        "lon_origem": rules.round3(lon_raw),
        "h3_r7_origem": rules.h3_cell(lat_raw, lon_raw, 7),
        "h3_r8_origem": rules.h3_cell(lat_raw, lon_raw, 8),
        "lat_destino": rules.round3(dlat_raw),
        "lon_destino": rules.round3(dlon_raw),
        "h3_r7_destino": rules.h3_cell(dlat_raw, dlon_raw, 7),
        "lat_destino_real": rules.round3(rlat),
        "lon_destino_real": rules.round3(rlon),
        "dist_percorrida_km": float(dist) / 1000 if dist not in (None, "") and float(dist) > 0 else None,
        "dur_viagem_s": trip_s,
        "motorista_pseud": rules.pseudonym(source.get("cD_MOTORISTA"), salt),
        "fl_tempos_ordenados": rules.times_ordered(registro, aceite, chegada, inicio, fim),
        "s_registro_ate_aceite": (aceite - registro).total_seconds() if aceite and registro else None,
        "s_registro_ate_chegada": (chegada - registro).total_seconds() if chegada and registro else None,
        "s_registro_ate_status_final": (final_at - registro).total_seconds() if final_at and registro else None,
        # Semântica não confirmada (PENDENTE): mantidos só para auditoria, nunca como verdade.
        "nu_dr_real_pendente": source.get("nU_DR_REAL"),
        "fl_h3_repos_real_pendente": source.get("tX_H3INDEX_REPOSICIONAMENTO_REAL") is not None,
        "fl_indice_viabilidade": bool(source.get("indiceViabilidade")),
    }


def build_requests(batches: dict[str, Batch], salt: str, silver: Silver) -> None:
    by_code: dict[int, dict] = {}
    for tag, batch in sorted(batches.items()):
        for file_name, page, source in iter_hits(batch, "req"):
            silver.ingested[f"{tag}:req"] += 1
            row = request_row(source, tag, file_name, page, salt)
            for item in source.get("logStatus") or []:
                silver.status.append(
                    {"codigo": row["codigo"], "status": item.get("tX_STATUS"), "ts_status": rules.parse_ts(item.get("dT_REGISTRO"))}
                )
            previous = by_code.get(row["codigo"])
            if previous is not None:
                silver.losses["dedup_codigo"] += 1
                # Mantém a versão com status final mais recente (RN003).
                if (row["ts_status_final"] or row["ts_registro"]) <= (previous["ts_status_final"] or previous["ts_registro"]):
                    continue
            by_code[row["codigo"]] = row
    silver.solicitacoes = sorted(by_code.values(), key=lambda r: r["codigo"])
    seen: set[tuple] = set()
    unique_status = []
    for item in silver.status:
        key = (item["codigo"], item["status"], item["ts_status"])
        if key not in seen:
            seen.add(key)
            unique_status.append(item)
    silver.status = unique_status


def build_history(batches: dict[str, Batch], salt: str, silver: Silver) -> None:
    for tag, batch in sorted(batches.items()):
        for _, _, source in iter_hits(batch, "hist"):
            silver.ingested[f"{tag}:hist"] += 1
            lat = rules.coordinate(source.get("origemLat"))
            lon = rules.coordinate(source.get("origemLng"))
            silver.historico.append(
                {
                    "codigo": int(source["codigo"]),
                    "status": source.get("status"),
                    "ts_registro": rules.parse_ts(source.get("dataRegistro")),
                    "dist_motorista_m": source.get("distMotorista"),
                    "eta_motorista_s": source.get("etaMotorista"),
                    "motorista_pseud": rules.pseudonym(source.get("idMotorista"), salt),
                    "lat_origem": rules.round3(lat),
                    "lon_origem": rules.round3(lon),
                }
            )


def build_fleet(batches: dict[str, Batch], salt: str, silver: Silver) -> None:
    for tag, batch in sorted(batches.items()):
        snapshot_counts: dict[str, Counter] = {}
        for _, _, source in iter_hits(batch, "snap"):
            silver.ingested[f"{tag}:snap"] += 1
            taken = rules.parse_ts(source.get("dataHora"))
            counts = Counter()
            for offer in source.get("ofertaList") or []:
                state = offer.get("status")
                lat = rules.coordinate(offer.get("latitude"))
                lon = rules.coordinate(offer.get("longitude"))
                gps = rules.parse_ts(offer.get("dataPosicaoGPS"))
                valid = rules.in_box(lat, lon)
                age = (taken - gps).total_seconds() if gps and taken else None
                if state == 3:
                    counts["qtdComPassageiro" if offer.get("passageiroEmbarcado") else "qtdACaminho"] += 1
                else:
                    counts[{1: "qtdOnline", 4: "qtdSelecionado", 5: "qtdIndisponivel"}.get(state, "outro")] += 1
                silver.posicoes.append(
                    {
                        "tag_lote": tag,
                        "snapshot": source.get("codigo"),
                        "ts_snapshot": taken,
                        "motorista_pseud": rules.pseudonym(offer.get("codigo"), salt),
                        "estado": state,
                        "estado_label": rules.DRIVER_STATES.get(state, "DESCONHECIDO"),
                        "passageiro_embarcado": bool(offer.get("passageiroEmbarcado")),
                        "lat": round(lat, 4) if lat is not None else None,
                        "lon": round(lon, 4) if lon is not None else None,
                        "h3_r7": offer.get("h3Index"),
                        "h3_r8": rules.h3_cell(lat, lon, 8) if valid else None,
                        "idade_posicao_s": age,
                        "fl_coordenada_valida": valid,
                        "fl_posicao_atual": age is not None and -60 <= age <= 300,
                    }
                )
            snapshot_counts[source.get("codigo")] = counts
        for _, _, source in iter_hits(batch, "sum"):
            silver.ingested[f"{tag}:sum"] += 1
            counts = snapshot_counts.get(source.get("codigo"))
            keys = ("qtdOnline", "qtdACaminho", "qtdComPassageiro", "qtdSelecionado", "qtdIndisponivel")
            silver.sumarios.append(
                {
                    "tag_lote": tag,
                    "codigo": source.get("codigo"),
                    "ts": rules.parse_ts(source.get("dataHora")),
                    **{key: source.get(key) for key in keys + ("qtdOffline", "qtdAproveitamento")},
                    "fl_tem_foto": counts is not None,
                    "fl_consistente_com_posicoes": None if counts is None else all(counts.get(key, 0) == source.get(key) for key in keys),
                }
            )


def build_overnight(silver: Silver) -> None:
    """Última posição válida do dia D e primeira de D+1 por motorista (base do regime B)."""
    first: dict[tuple[str, date], dict] = {}
    last: dict[tuple[str, date], dict] = {}
    for row in silver.posicoes:
        if not row["fl_coordenada_valida"] or row["estado"] not in rules.WORKING_STATES or row["motorista_pseud"] is None:
            continue
        key = (row["motorista_pseud"], row["ts_snapshot"].date())
        if key not in first or row["ts_snapshot"] < first[key]["ts_snapshot"]:
            first[key] = row
        if key not in last or row["ts_snapshot"] > last[key]["ts_snapshot"]:
            last[key] = row
    out = []
    for (driver, day), end in sorted(last.items()):
        nxt = first.get((driver, date.fromordinal(day.toordinal() + 1)))
        out.append(
            {
                "motorista_pseud": driver,
                "data_local": day,
                "ts_ultima": end["ts_snapshot"],
                "lat_ultima": end["lat"],
                "lon_ultima": end["lon"],
                "h3_r7_ultima": end["h3_r7"],
                "ts_primeira_dia_seguinte": nxt["ts_snapshot"] if nxt else None,
                "lat_primeira_dia_seguinte": nxt["lat"] if nxt else None,
                "lon_primeira_dia_seguinte": nxt["lon"] if nxt else None,
                "km_reta_dormida": _km(end["lat"], end["lon"], nxt["lat"], nxt["lon"]) if nxt else None,
            }
        )
    silver.dormida = out


def build_rides(silver: Silver, road_factor: float) -> None:
    """Corridas encerradas; KM de busca = reta da última foto livre (até 10 min antes do aceite) × fator."""
    by_driver: dict[str, list[dict]] = defaultdict(list)
    for row in silver.posicoes:
        if row["motorista_pseud"] and row["fl_coordenada_valida"]:
            by_driver[row["motorista_pseud"]].append(row)
    for rows in by_driver.values():
        rows.sort(key=lambda r: r["ts_snapshot"])
    import bisect

    times = {d: [r["ts_snapshot"] for r in rows] for d, rows in by_driver.items()}
    for req in silver.solicitacoes:
        if req["status"] != "CorridaEncerrada":
            continue
        km_reta = None
        driver = req["motorista_pseud"]
        if driver in by_driver and req["ts_aceite"] and req["lat_origem"] is not None:
            i = bisect.bisect_right(times[driver], req["ts_aceite"]) - 1
            if i >= 0:
                snap = by_driver[driver][i]
                if (req["ts_aceite"] - snap["ts_snapshot"]).total_seconds() <= 600 and snap["estado"] in (1, 4):
                    km_reta = _km(snap["lat"], snap["lon"], req["lat_origem"], req["lon_origem"])
        silver.corridas.append(
            {
                "codigo": req["codigo"],
                "motorista_pseud": driver,
                "fl_imediata": req["fl_imediata"],
                "data_base": req["data_base"],
                "ts_aceite": req["ts_aceite"],
                "ts_chegada": req["ts_chegada"],
                "ts_inicio": req["ts_inicio"],
                "ts_fim": req["ts_fim"],
                "fl_tempos_ordenados": req["fl_tempos_ordenados"],
                "km_busca_reta_foto": km_reta,
                "km_busca_estimado": km_reta * road_factor if km_reta is not None else None,
                "dist_percorrida_km": req["dist_percorrida_km"],
                "dur_viagem_s": req["dur_viagem_s"],
            }
        )


def build_silver(batches: dict[str, Batch], salt: str, road_factor: float = 1.42) -> Silver:
    silver = Silver()
    build_requests(batches, salt, silver)
    build_history(batches, salt, silver)
    build_fleet(batches, salt, silver)
    build_overnight(silver)
    build_rides(silver, road_factor)
    return silver
