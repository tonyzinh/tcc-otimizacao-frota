"""Execução de UM par (cenário, semente) sintético com as políticas A, B e C no MESMO mundo.

Políticas (identificadores iguais aos dos resultados congelados em ``reports/sintetico_v2/metodos_avaliacao_D``):
  ``A`` despacho imediato pelo mais próximo; ``D_lote60s_guloso_fifo`` = B (mais próximo em lotes de 60 s);
  ``D_lote60s_hungaro`` = C (atribuição conjunta, Húngaro, lotes de 60 s).
Sem reposicionamento: km vazio = km de busca. Resultado de simulação em cenários sintéticos; não é desempenho operacional.
"""

from __future__ import annotations

import numpy as np

from tcc_frota.assignment import dispatch as dp
from tcc_frota.domain.entities import SimParams, SimResult
from tcc_frota.scenarios import generator as g
from tcc_frota.scenarios.geography import construir_pontos, construir_rede, recortar_operacional
from tcc_frota.simulation.engine import simulate

DAY_WINDOW_S = (0.0, 86400.0)
BATCH_S = 60.0
POLICY_IDS = {"A": "A", "B": "D_lote60s_guloso_fifo", "C": "D_lote60s_hungaro"}
OPERATIONAL_RADIUS_KM = 20.0  # recorte: pontos a até 20 km por via (ida e volta) do centro de Vitória
MIN_NODES_PER_CELL = 20


def build_world(zone_resolution: int = 7) -> g.Mundo:
    """Mundo geográfico (pontos H3 de espera + rede viária OSM + distâncias de menor caminho) para uma resolução de zona."""
    points = construir_pontos(construir_rede(), res_zona=zone_resolution, min_nos=MIN_NODES_PER_CELL)
    return g.Mundo.de(recortar_operacional(points, OPERATIONAL_RADIUS_KM), zone_resolution)


def sim_params(op: g.Operacao) -> SimParams:
    """Parâmetros do simulador sintético: raio por via, velocidade e paciência da operação; fator rua/reta 1 (distância já é por via)."""
    return SimParams(radius_km=op.raio_despacho_km, speed_kmh=op.velocidade_kmh, road_factor=1.0, patience_s=op.paciencia_s)


def pair_metrics(res: SimResult, n_vehicles: int) -> dict:
    """Métricas de uma simulação sintética. Espera (média e P90) só entre os pedidos atendidos."""
    w = np.array(res.wait_s, float)
    n = max(res.n_requests, 1)
    return {
        "pedidos": res.n_requests,
        "atendidos": res.served,
        "nao_atendidos": res.n_requests - res.served,
        "prop_atendida": res.served / n,
        "km_vazio_total": res.empty_km,
        "km_busca": res.pickup_km,
        "km_reposicionamento": res.reposition_km,
        "km_retorno": 0.0,
        "km_outros_vazios": 0.0,
        "km_vazio_por_atendimento": res.empty_km / res.served if res.served else float("nan"),
        "espera_media_s": float(w.mean()) if len(w) else float("nan"),
        "espera_p90_s": float(np.percentile(w, 90)) if len(w) else float("nan"),
        "movimentos_planejados": res.moves_planned,
        "movimentos_executados": res.moves_executed,
        "n_veiculos": n_vehicles,
    }


def run_pair(scenario: g.Cenario, seed: int, world: g.Mundo, op: g.Operacao | None = None) -> list[dict]:
    """Roda A, B e C para (cenário, semente) com pedidos, frota e distâncias idênticos (assinatura verificada).

    Returns:
        Uma linha por política, com as colunas dos resultados congelados.

    Raises:
        AssertionError: se as entradas das políticas diferirem.
    """
    op = op or g.Operacao()
    metric = g.MetricaRapida(world)
    params = sim_params(op)
    lam = g.lambda_esperado(scenario, op, world, dia_avaliado=True)
    requests, _ = g.gerar_pedidos(lam, op, world, g.rng_de(scenario, seed, "avaliado"))
    fleet = g.gerar_frota(scenario, world, g.rng_de(scenario, seed, "frota"))
    drivers = g.frota_para_sim(fleet, world)
    runs = (
        (POLICY_IDS["A"], None, None),
        (POLICY_IDS["B"], BATCH_S, dp.POLICIES["nearest_fifo"]),
        (POLICY_IDS["C"], BATCH_S, dp.POLICIES["hungarian"]),
    )
    rows, signature = [], None
    for name, batch_s, assigner in runs:
        res = simulate(requests, drivers, params, DAY_WINDOW_S, {}, metric=metric, batch_s=batch_s, assigner=assigner)
        if signature is None:
            signature = res.signature
        elif res.signature != signature:
            raise AssertionError("entradas diferentes entre políticas")
        rows.append({"cenario": scenario.id, "semente": seed, "politica": name, **pair_metrics(res, len(fleet))})
    return rows
