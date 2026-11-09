"""Configurações externas concordam com o código (políticas e catálogo de cenários)."""

from __future__ import annotations

import json
from pathlib import Path

from tcc_frota.scenarios import catalog
from tcc_frota.simulation import historical as hs

ROOT = Path(__file__).resolve().parents[2]


def test_policies_config_matches_code_when_historical_ids_are_compared():
    cfg = json.loads((ROOT / "configs" / "policies" / "policies.json").read_text(encoding="utf-8"))
    by_id = {p["id"]: p for p in cfg["politicas"]}
    assert {k: v["id_historico_gravado"] for k, v in by_id.items()} == hs.POLICY_IDS
    batch = {name: window for name, window, _ in hs.POLICY_SPECS}
    for key, name in hs.POLICY_IDS.items():
        assert (batch[name] or 0) == by_id[key]["janela_lote_s"]


def test_scenario_catalog_config_matches_code_when_ids_and_codes_are_compared():
    doc = json.loads((ROOT / "configs" / "scenarios" / "catalog.json").read_text(encoding="utf-8"))
    assert [c["id"] for c in doc["cenarios"]] == [c.id for c in catalog.matriz()]
    assert [c["codigo_da_semente"] for c in doc["cenarios"]] == [c.codigo for c in catalog.matriz()]


def test_scenario_catalog_has_22_unique_ids_and_5_principal():
    ids = [c.id for c in catalog.matriz()]
    assert len(ids) == len(set(ids)) == 22
    assert catalog.PRINCIPAIS == ("S1", "S2", "S3", "S4", "S5")


def test_experiment_configs_declare_frozen_statistics_when_loaded():
    hist = json.loads((ROOT / "configs" / "experiments" / "historical.json").read_text(encoding="utf-8"))
    assert hist["estatistica"]["semente"] == 20261108 and hist["estatistica"]["reamostragens"] == 10000
    assert hist["simulador"]["fator_rua_reta"] == hs.PARAMS.road_factor
    assert hist["simulador"]["raio_despacho_km_em_linha_reta"] == hs.PARAMS.radius_km
