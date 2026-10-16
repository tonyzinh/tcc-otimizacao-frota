"""Fases D e E: fórmula do valor líquido, leitor do YAML privado e deslocamento de livres (valores genéricos)."""
from datetime import datetime, timedelta

import pytest

from tcc_frota.analise.deslocamento_livre import free_movement
from tcc_frota.analise.valor_liquido import cost_per_km, load_costs


def test_cost_formula_and_breakeven():
    c = cost_per_km(1.0, 0.5, 20.0)          # 1 + 0,5·60/20 = 2,5 R$/km
    assert c == pytest.approx(2.5)
    assert 20.0 / c == pytest.approx(8.0)     # e* = margem / custo


def test_private_yaml_reader(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("r_km: 1.5  # comentário\nmargens:\n  a: 10.0\n  b: 12.5\nvel: [16.0, 20.0]\n", encoding="utf-8")
    assert load_costs(p) == {"r_km": 1.5, "margens": {"a": 10.0, "b": 12.5}, "vel": [16.0, 20.0]}


def snap(did, t, estado, lat, lon=-40.3):
    return {"motorista_pseud": did, "ts_snapshot": t, "estado": estado, "lat": lat, "lon": lon, "fl_coordenada_valida": True}


def test_free_movement_counts_only_free_to_free_within_gap_and_window():
    t0 = datetime(2026, 3, 5, 5, 0)
    rows = [snap("a", t0, 1, -20.30), snap("a", t0 + timedelta(minutes=10), 1, -20.31),     # 1,1 km, conta
            snap("a", t0 + timedelta(minutes=20), 3, -20.35),                              # ocupado, não conta
            snap("a", t0 + timedelta(minutes=30), 1, -20.36), snap("a", t0 + timedelta(minutes=50), 1, -20.40),  # gap 20 min
            snap("b", datetime(2026, 3, 5, 12, 0), 1, -20.3), snap("b", datetime(2026, 3, 5, 12, 10), 1, -20.4)]  # fora da janela
    out = {r["mes"]: r for r in free_movement(rows)}
    assert out["mar2026"]["intervalos_livre_livre"] == 1
    assert out["mar2026"]["km_dia_reta_media"] == pytest.approx(1.112, abs=0.01)
    assert out["mar2026"]["fracao_intervalos_mov_maior_0_5km_pct"] == 100.0
