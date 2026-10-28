"""Regressão numérica: valores congelados em 28/10/2026 (antes da padronização de código) para o experimento sintético
determinístico (dia 0, política proporcional) e para a decisão F4 de setembro. Os números vêm de
`reports/validation_current/baseline_antes_final.json`, não são recalculados pelo código testado."""

from pathlib import Path

import pytest

from tcc_frota.algoritmos.base import PlannerSpec
from tcc_frota.v3 import controle as c
from tcc_frota.v3 import decisao as dc

RAIZ = Path(__file__).resolve().parents[2]
METRICAS = {
    "alcancavel|proporcional": {
        "empty_km": 43.949411552,
        "n_requests": 70.0,
        "pickup_km": 20.073817912,
        "reposition_km": 23.87559364,
        "served": 70.0,
    },
    "alcancavel|sem_reposicionamento": {
        "empty_km": 37.825672611,
        "n_requests": 70.0,
        "pickup_km": 37.825672611,
        "reposition_km": 0.0,
        "served": 70.0,
    },
    "fora_do_raio|proporcional": {
        "empty_km": 43.949411552,
        "n_requests": 70.0,
        "pickup_km": 20.073817912,
        "reposition_km": 23.87559364,
        "served": 70.0,
    },
    "fora_do_raio|sem_reposicionamento": {
        "empty_km": 1.016717849,
        "n_requests": 70.0,
        "pickup_km": 1.016717849,
        "reposition_km": 0.0,
        "served": 7.0,
    },
}

CHAVES = ("n_requests", "served", "pickup_km", "reposition_km", "empty_km")


@pytest.mark.parametrize("cenario", sorted(c.SCENARIOS))
def test_run_day_retorna_metricas_congeladas_quando_semente_fixa(cenario):
    # Arrange
    specs = [PlannerSpec("proporcional", "proporcional", {"max_km": 3.0})]
    # Act
    linhas = c.run_day(0, cenario, specs, mode="fixa", forecast="verdadeira")
    # Assert
    obtido = {f"{cenario}|{r['cenario']}": {k: round(float(r[k]), 9) for k in CHAVES} for r in linhas}
    esperado = {k: v for k, v in METRICAS.items() if k.startswith(f"{cenario}|")}
    assert obtido == esperado


def test_decidir_retorna_inconclusivo_quando_f4_setembro_proporcional_e30():
    # Arrange
    csv = RAIZ / "reports/tcc_v2/fase4_dias.csv"
    plano, base = dc.dias_de_csv(csv, periodo="set2026", cenario="proporcional", grupo="origem|B0|rho1|c1", par="origem|B0|rho1")
    # Act
    d = dc.decidir(30, plano, base, reps=2000, rotulo="set2026")
    # Assert
    assert (round(d.nb, 9), round(d.ic_inf, 6), round(d.ic_sup, 6), d.decisao) == (-0.537742662, -1.156924, 0.086219, "inconclusivo")
