"""Testes do fluxo sintético em um mundo pequeno de grade (sem fontes privadas nem download de geografia)."""

from __future__ import annotations

import h3
import numpy as np
import pytest

from tcc_frota.scenarios import generator as g
from tcc_frota.scenarios.geography import Pontos, haversine_km


def _mundo(res_zona: int = 7) -> g.Mundo:
    lats, lons = [], []
    for i in range(10):
        for j in range(10):
            lats.append(-20.34 + 0.008 * i)
            lons.append(-40.34 + 0.008 * j)
    lat, lon = np.array(lats), np.array(lons)
    d = haversine_km(lat[:, None], lon[:, None], lat[None, :], lon[None, :]) * 1.3  # rede de grade fictícia, só para teste
    cel = np.array([h3.latlng_to_cell(a, b, 8) for a, b in zip(lat, lon, strict=True)])
    zona = np.array([h3.cell_to_parent(c, res_zona) for c in cel])
    n = len(lat)
    p = Pontos(lat, lon, np.arange(n), cel, zona, np.array(["Vitória"] * n), d, {})
    return g.Mundo.de(p, res_zona)


CEN = g.Cenario("T", "teste", "hubs", n_veiculos=12, pedidos_por_veiculo=4.0, codigo=99)


@pytest.fixture(scope="module")
def mundo() -> g.Mundo:
    return _mundo()


def test_mesma_semente_gera_mesmos_dados(mundo):
    op = g.Operacao()
    lam = g.lambda_esperado(CEN, op, mundo, True)
    r1, c1 = g.gerar_pedidos(lam, op, mundo, g.rng_de(CEN, 5, "avaliado"))
    r2, c2 = g.gerar_pedidos(lam, op, mundo, g.rng_de(CEN, 5, "avaliado"))
    assert r1 == r2 and (c1 == c2).all()
    assert g.gerar_frota(CEN, mundo, g.rng_de(CEN, 5, "frota")) == g.gerar_frota(CEN, mundo, g.rng_de(CEN, 5, "frota"))


def test_sementes_diferentes_geram_dados_diferentes(mundo):
    lam = g.lambda_esperado(CEN, g.Operacao(), mundo, True)
    a, _ = g.gerar_pedidos(lam, g.Operacao(), mundo, g.rng_de(CEN, 1, "avaliado"))
    b, _ = g.gerar_pedidos(lam, g.Operacao(), mundo, g.rng_de(CEN, 2, "avaliado"))
    assert a != b


def test_origens_e_destinos_sao_pontos_validos(mundo):
    op = g.Operacao()
    reqs, _ = g.gerar_pedidos(g.lambda_esperado(CEN, op, mundo, True), op, mundo, g.rng_de(CEN, 3, "avaliado"))
    assert reqs
    met = g.MetricaRede(mundo)
    for r in reqs:
        assert met.km(r.lat, r.lon, r.dlat, r.dlon) > 0  # origem e destino existem e são distintos


def test_metrica_recusa_posicao_fora_dos_pontos(mundo):
    with pytest.raises(KeyError):
        g.MetricaRede(mundo).km(-20.0, -40.0, float(mundo.pontos.lat[0]), float(mundo.pontos.lon[0]))


def test_lambda_soma_demanda_total(mundo):
    for esp in ("uniforme", "hubs", "movel"):
        c = CEN.com(espacial=esp)
        assert g.lambda_esperado(c, g.Operacao(), mundo, False).sum() == pytest.approx(c.n_veiculos * c.pedidos_por_veiculo)


def test_desvio_muda_so_o_dia_avaliado(mundo):
    c = CEN.com(desvio="hubs_trocados")
    op = g.Operacao()
    assert np.allclose(g.lambda_esperado(c, op, mundo, False), g.lambda_esperado(CEN, op, mundo, False))
    assert not np.allclose(g.lambda_esperado(c, op, mundo, True), g.lambda_esperado(CEN, op, mundo, True))
