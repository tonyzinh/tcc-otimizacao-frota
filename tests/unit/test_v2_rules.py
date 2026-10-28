"""Regras de limpeza da v2 (Fase 1): cada regra tem um teste com dados artificiais."""

import json
import os
from datetime import datetime, timedelta

import pytest

from tcc_frota.v2 import raw, rules
from tcc_frota.v2.gold import Gold, fleet_tables, replay_universe
from tcc_frota.v2.silver import Silver, build_requests, request_row

SALT = "sal-de-teste-com-16+"


def req(codigo=1, status="NaoAtendida", agendamento=None, lat="-20.31987", lng="-40.33811", **extra):
    base = {
        "codigo": codigo,
        "tX_STATUS": status,
        "tX_TP_SOLICITACAO": "TempoReal",
        "cD_TIPO_SERVICO": 1,
        "dT_REGISTRO": "2026-03-10T05:00:00.1234567-03:00",
        "dT_AGENDAMENTO": agendamento,
        "tX_ORIGEM_LAT": lat,
        "tX_ORIGEM_LNG": lng,
        "tX_DESTINO_LAT": "-20.29",
        "tX_DESTINO_LNG": "-40.30",
        "logStatus": [{"dT_REGISTRO": "2026-03-10T05:02:00-03:00", "tX_STATUS": status}],
    }
    base.update(extra)
    return base


def test_timestamp_with_seven_decimals_and_offset_is_local():
    ts = rules.parse_ts("2026-03-01T00:01:52.2000000-03:00")
    assert ts.tzinfo is not None and ts.hour == 0 and ts.microsecond == 200000
    assert rules.parse_ts("2026-03-01T03:01:52Z").hour == 0
    assert rules.parse_ts(None) is None
    with pytest.raises(ValueError):
        rules.parse_ts("2026-03-01 00:01:52")


@pytest.mark.parametrize(
    "status,demanda,aceito",
    [
        ("CorridaEncerrada", True, True),
        ("NaoAtendida", True, False),
        ("LimiteEsperaAtingido", True, False),
        ("CorridaCanceladaSolicitante", True, False),
        ("CorridaCanceladaSolicitantePosAceite", True, True),
        ("CorridaCanceladaMotoristaPosAceite", True, True),
        ("PagamentoRejeitado", False, False),
        ("CorridaCanceladaOperador", False, False),
        ("Retracamento", False, False),
        ("CorridaCanceladaAgendamento", False, False),
        ("CorridaIniciada", False, False),
        ("Inventado", False, False),
    ],
)
def test_status_treatment_table(status, demanda, aceito):
    t = rules.treatment(status)
    assert (t.demanda, t.aceito) == (demanda, aceito)


def test_tempo_real_with_schedule_is_not_immediate():
    assert rules.is_immediate(req())
    assert not rules.is_immediate(req(agendamento="2026-03-12T07:00:00-03:00"))
    basis, at = rules.demand_time_basis(req(agendamento="2026-03-12T07:00:00-03:00"))
    assert basis == "dT_AGENDAMENTO" and at.day == 12


def test_box_and_rounding():
    assert rules.in_box(-20.3, -40.3) and not rules.in_box(-19.9, -40.3) and not rules.in_box(None, -40.3)
    assert rules.round3(-20.31987) == -20.32


def test_duration_ticks_and_ordered_times():
    assert rules.trip_seconds(8_360_000_000) == pytest.approx(836.0)
    assert rules.trip_seconds(0) is None
    t0 = datetime(2026, 3, 1, 5, tzinfo=rules.TZ)
    assert rules.times_ordered(t0, None, t0 + timedelta(minutes=5), None, t0 + timedelta(minutes=20))
    assert not rules.times_ordered(t0, t0 - timedelta(seconds=1), None, None, None)


def test_pseudonym_is_salted_deterministic_and_requires_salt():
    a = rules.pseudonym(1494, SALT)
    assert a == rules.pseudonym(1494, SALT) and len(a) == 16 and "1494" not in a
    assert a != rules.pseudonym(1494, SALT + "x")
    with pytest.raises(ValueError):
        rules.pseudonym(1, "curto")


def test_unserved_request_keeps_rounded_origin_and_no_raw_driver_id():
    row = request_row(req(cD_MOTORISTA=777), "mar2026", "req_mar2026_p01.json", 1, SALT)
    assert row["fl_demanda"] and not row["fl_aceito"]
    assert row["lat_origem"] == -20.32 and row["lon_origem"] == -40.338
    assert row["h3_r8_origem"] and row["h3_r7_origem"]
    assert row["motorista_pseud"] != 777 and len(row["motorista_pseud"]) == 16
    assert row["s_registro_ate_status_final"] == pytest.approx(119.8766, abs=1e-3)


def _batch(tmp_path, hits, tag="mar2026"):
    folder = tmp_path / f"dados_{tag}" / f"dados_{tag}"
    folder.mkdir(parents=True)
    (folder / f"req_{tag}_p01.json").write_text(json.dumps({"hits": {"hits": [{"_source": h} for h in hits]}}), encoding="utf-8")
    manifest = {"tag": tag, "fases": {"req": {"lidos": len(hits), "total": len(hits), "ok": True, "arquivos": [f"req_{tag}_p01.json"]}}}
    (folder / f"manifest_{tag}.json").write_text(json.dumps(manifest), encoding="utf-8")
    return folder


def test_dedup_by_code_keeps_latest_final_status(tmp_path):
    late = req(codigo=5, status="CorridaEncerrada")
    late["logStatus"] = [{"dT_REGISTRO": "2026-03-10T06:00:00-03:00", "tX_STATUS": "CorridaEncerrada"}]
    _batch(tmp_path, [req(codigo=5), late, req(codigo=6)])
    batches = raw.discover(tmp_path)
    silver = Silver()
    build_requests(batches, SALT, silver)
    assert [r["codigo"] for r in silver.solicitacoes] == [5, 6]
    assert silver.solicitacoes[0]["status"] == "CorridaEncerrada"
    assert silver.losses["dedup_codigo"] == 1


def test_discovery_accepts_nested_and_backslash_names_and_rejects_bad_manifests(tmp_path):
    _batch(tmp_path, [req()], "mar2026")
    flat = tmp_path / "dados_set2026"
    flat.mkdir()
    # Zip do Windows extraído fora do Windows gera nome com barra invertida; no Windows vira subpasta.
    name = "dados_set2026\\req_set2026_p01.json" if os.sep == "/" else "sub/req_set2026_p01.json"
    (flat / name).parent.mkdir(exist_ok=True)
    (flat / name).write_text(json.dumps({"hits": {"hits": []}}), encoding="utf-8")
    (flat / "manifest_set2026.json").write_text(
        json.dumps({"tag": "set2026", "fases": {"req": {"lidos": 0, "total": 0, "ok": True, "arquivos": ["req_set2026_p01.json"]}}}),
        encoding="utf-8",
    )
    bad = tmp_path / "historico56"
    bad.mkdir()
    (bad / "manifest_historico56.json").write_text(
        json.dumps(
            {"tag": "historico56", "fases": {"req": {"lidos": 9, "total": 10, "ok": True, "arquivos": ["req_historico56_p01.json"]}}}
        ),
        encoding="utf-8",
    )
    found = raw.discover(tmp_path)
    assert found["mar2026"].ok and found["set2026"].ok
    assert not found["historico56"].ok and len(found["historico56"].problems) == 2
    with pytest.raises(FileNotFoundError):
        raw.prepare_raw(tmp_path, echo=lambda *_: None)
    accepted = raw.prepare_raw(tmp_path, required=("mar2026", "set2026"), materialize_to=tmp_path / "norm", echo=lambda *_: None)
    assert set(accepted) == {"mar2026", "set2026"}
    assert (tmp_path / "norm" / "set2026" / "req_set2026_p01.json").is_file()


def test_replay_universe_filters_are_counted():
    silver = Silver()
    rows = [
        request_row(req(codigo=1), "t", "f", 1, SALT),
        request_row(req(codigo=2, agendamento="2026-03-12T07:00:00-03:00"), "t", "f", 1, SALT),
        request_row(req(codigo=3, status="PagamentoRejeitado"), "t", "f", 1, SALT),
        request_row(req(codigo=4, lat="-19.5"), "t", "f", 1, SALT),
    ]
    silver.solicitacoes = rows
    gold = Gold()
    replay_universe(silver, gold)
    assert [r["codigo"] for r in gold.replay_pedidos] == [1]
    assert gold.filtros["excluido_agendada"] == 1 and gold.filtros["excluido_fora_da_caixa"] == 1
    assert gold.filtros["excluido_nao_demanda:nao_demanda_pagamento"] == 1


def test_sessions_split_on_gap_and_unavailable_state():
    t0 = datetime(2026, 3, 10, 5, tzinfo=rules.TZ)
    states = [(0, 1), (10, 3), (20, 1), (60, 1), (70, 5), (80, 1)]  # lacuna de 40 min e Indisponível
    silver = Silver(
        posicoes=[
            {
                "tag_lote": "t",
                "ts_snapshot": t0 + timedelta(minutes=m),
                "motorista_pseud": "d1",
                "estado": s,
                "passageiro_embarcado": False,
                "lat": -20.3,
                "lon": -40.3,
                "h3_r7": "x",
                "h3_r8": "y",
                "fl_coordenada_valida": True,
                "fl_posicao_atual": True,
            }
            for m, s in states
        ]
    )
    gold = Gold()
    fleet_tables(silver, gold)
    spans = [(s["ts_inicio"].minute, s["qtd_fotos"]) for s in gold.frota_sessoes]
    assert spans == [(0, 3), (0, 1), (20, 1)]  # 05:00–05:30, 06:00, 06:20
