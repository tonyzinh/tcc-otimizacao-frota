import csv
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

from tcc_frota.v3 import decisao as dc

ROOT = Path(__file__).resolve().parents[2]
DATAS = tuple(date(2026, 3, 16) + timedelta(days=i) for i in range(16))


def _dias(served, km):
    return dc.DiasAgregados(DATAS, tuple(float(x) for x in served), tuple(float(x) for x in km))


def _mundo(delta_n, delta_km, ruido=0.0, seed=3):
    rng = np.random.default_rng(seed)
    base = _dias(100 + rng.normal(0, ruido, 16), 300 + rng.normal(0, ruido, 16))
    plano = _dias(
        np.array(base.atendidas) + delta_n + rng.normal(0, ruido, 16), np.array(base.km_vazio) + delta_km + rng.normal(0, ruido, 16)
    )
    return plano, base


def test_adotar_quando_ganho_de_corridas_supera_o_custo():
    plano, base = _mundo(delta_n=20, delta_km=100, ruido=1)  # NB(30) ≈ 20 − 100/30 > 0
    d = dc.decidir(30, plano, base, reps=500)
    assert d.decisao == dc.ADOTAR and d.ic_inf > 0
    assert d.nb == pytest.approx(20 - 100 / 30, abs=1.0)
    assert d.delta_atendidas_dia == pytest.approx(20, abs=1.0)


def test_nao_adotar_quando_so_ha_custo():
    plano, base = _mundo(delta_n=0, delta_km=50, ruido=1)
    d = dc.decidir(30, plano, base, reps=500)
    assert d.decisao == dc.NAO_ADOTAR and d.ic_sup < 0


def test_e_star_altera_a_decisao():
    plano, base = _mundo(delta_n=2, delta_km=60, ruido=0.5)  # NB = 2 − 60/e
    assert dc.decidir(10, plano, base, reps=500).decisao == dc.NAO_ADOTAR
    assert dc.decidir(100, plano, base, reps=500).decisao == dc.ADOTAR


def test_inconclusivo_com_ruido_grande_e_efeito_nulo():
    plano, base = _mundo(delta_n=0, delta_km=0, ruido=20)
    d = dc.decidir(30, plano, base, reps=500)
    assert d.decisao == dc.INCONCLUSIVO and d.ic_inf < 0 < d.ic_sup
    assert d.mde_nb > 0


def test_deterministico_e_variante_mais_larga():
    plano, base = _mundo(1, 10, ruido=2)
    a, b = dc.decidir(20, plano, base, reps=300), dc.decidir(20, plano, base, reps=300)
    assert a == b


def test_validacoes():
    plano, base = _mundo(1, 1, 1)
    with pytest.raises(ValueError):
        dc.decidir(0, plano, base)
    with pytest.raises(ValueError):
        dc.decidir(30, dc.DiasAgregados(DATAS[::-1], plano.atendidas, plano.km_vazio), base)
    with pytest.raises(ValueError):
        dc.decidir(
            30,
            dc.DiasAgregados(DATAS[:4], plano.atendidas[:4], plano.km_vazio[:4]),
            dc.DiasAgregados(DATAS[:4], base.atendidas[:4], base.km_vazio[:4]),
        )
    with pytest.raises(ValueError):
        dc.decidir(30, dc.DiasAgregados(DATAS, (-1.0,) * 16, plano.km_vazio), base)


def test_dias_de_csv_exige_baseline_unico(tmp_path):
    campos = ["periodo", "data", "grupo", "cenario", "par", "served", "empty_km"]
    rows = [{"periodo": "p", "data": d.isoformat(), "grupo": "g", "cenario": "x", "par": "a", "served": 10, "empty_km": 5} for d in DATAS]
    rows += [
        {"periodo": "p", "data": d.isoformat(), "grupo": "base", "cenario": "sem_reposicionamento", "par": "a", "served": 9, "empty_km": 5}
        for d in DATAS
    ]
    rows += [
        {
            "periodo": "p",
            "data": DATAS[0].isoformat(),
            "grupo": "base2",
            "cenario": "sem_reposicionamento",
            "par": "a",
            "served": 9,
            "empty_km": 5,
        }
    ]
    f = tmp_path / "d.csv"
    with open(f, "w", encoding="utf-8", newline="") as h:
        w = csv.DictWriter(h, campos)
        w.writeheader()
        w.writerows(rows)
    with pytest.raises(ValueError):
        dc.dias_de_csv(f, periodo="p", cenario="x", grupo="g", par="a")
    rows.pop()
    with open(f, "w", encoding="utf-8", newline="") as h:
        w = csv.DictWriter(h, campos)
        w.writeheader()
        w.writerows(rows)
    plano, base = dc.dias_de_csv(f, periodo="p", cenario="x", grupo="g", par="a")
    assert plano.datas == base.datas == DATAS and plano.atendidas[0] == 10 and base.atendidas[0] == 9


def test_reproduz_a_linha_da_fase4():
    """Mesma linha de `fase4_F4_origem_nb.csv` (set/2026, proporcional contra B0, e*=30): ponto e IC idênticos."""
    plano, base = dc.dias_de_csv(
        ROOT / "reports/tcc_v2/fase4_dias.csv", periodo="set2026", cenario="proporcional", grupo="origem|B0|rho1|c1", par="origem|B0|rho1"
    )
    d = dc.decidir(30, plano, base, reps=10000, rotulo="set2026")
    ref = next(
        r
        for r in csv.DictReader(open(ROOT / "reports/tcc_v2/fase4_F4_origem_nb.csv", encoding="utf-8"))
        if r["periodo"] == "set2026" and r["grupo"] == "origem|B0|rho1|c1" and r["cenario"] == "proporcional" and float(r["e_star"]) == 30
    )
    assert d.nb == pytest.approx(float(ref["nb"]), abs=1e-4)
    assert d.ic_inf == pytest.approx(float(ref["ic_inf"]), abs=1e-3) and d.ic_sup == pytest.approx(float(ref["ic_sup"]), abs=1e-3)
    assert d.decisao == dc.INCONCLUSIVO
