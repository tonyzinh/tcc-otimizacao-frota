"""Calculadora de decisão por benefício líquido NB(e*): protocolo de avaliação da v2 (docs/TCC_REFORMULACAO.md §2).

Entrada: o e* da operação (km vazio extra aceito por corrida adicional atendida) e, por dia, as corridas atendidas e o KM vazio
(coleta + reposicionamento + deriva) do plano e do baseline. Saída: NB(e*) em corridas-equivalentes por dia, IC de decisão
(a mais larga das oito variantes de bootstrap por dia da Fase 1) e a decisão:

* "adotar":      limite inferior do IC > 0 (benefício líquido demonstrado);
* "não adotar":  limite superior do IC < 0 (prejuízo líquido demonstrado);
* "inconclusivo": o IC contém 0. O MDE de NB(e*) indica o menor efeito que o protocolo detectaria com 80% de poder.

A regra é a proposta do autor (não é política da empresa). Não corrige para múltiplos testes: use uma linha por decisão.
Só lê agregados diários (sem IDs nem coordenadas).
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np

from . import inferencia as inf
from .reamostragem import SCHEMES, indices, scheme_seed

ADOTAR, NAO_ADOTAR, INCONCLUSIVO = "adotar", "não adotar", "inconclusivo"
MIN_DIAS = 8


@dataclass(frozen=True)
class DiasAgregados:
    """Agregados diários de um braço: mesmas datas, mesma ordem."""
    datas: tuple[date, ...]
    atendidas: tuple[float, ...]
    km_vazio: tuple[float, ...]


@dataclass(frozen=True)
class Decisao:
    e_star: float
    dias: int
    delta_atendidas_dia: float
    delta_km_vazio_dia: float
    nb: float
    ic_inf: float
    ic_sup: float
    variante: str
    mde_nb: float
    decisao: str


def _validar(plano: DiasAgregados, base: DiasAgregados) -> None:
    if plano.datas != base.datas:
        raise ValueError("plano e baseline precisam ter as mesmas datas, na mesma ordem")
    if len(set(plano.datas)) != len(plano.datas):
        raise ValueError("datas duplicadas")
    for a in (plano, base):
        if not (len(a.datas) == len(a.atendidas) == len(a.km_vazio)):
            raise ValueError("comprimentos diferentes")
        if any(not np.isfinite(v) or v < 0 for v in (*a.atendidas, *a.km_vazio)):
            raise ValueError("valores negativos ou não finitos")
    if len(plano.datas) < MIN_DIAS:
        raise ValueError(f"são necessários ao menos {MIN_DIAS} dias")


def _pares(plano: DiasAgregados, base: DiasAgregados) -> inf.Pairs:
    n = len(plano.datas)

    def bloco(a: DiasAgregados) -> dict[str, np.ndarray]:
        d = {k: np.zeros(n) for k in inf.FIELDS}
        d["served"], d["empty_km"] = np.array(a.atendidas, float), np.array(a.km_vazio, float)
        return d
    return inf.Pairs(("decisao", "", "", ""), plano.datas, bloco(base), bloco(plano))


def decidir(e_star: float, plano: DiasAgregados, baseline: DiasAgregados, *, reps: int = 10000, rotulo: str = "decisao") -> Decisao:
    """NB(e*), IC (variante mais larga) e decisão. `rotulo` fixa as sementes de reamostragem (use o período para reproduzir a Fase 1/4)."""
    if not e_star > 0:
        raise ValueError("e* deve ser positivo")
    _validar(plano, baseline)
    pr = _pares(plano, baseline)
    point = float(inf.stat_nb(pr, e_star))
    ivs = {}
    for s in SCHEMES:
        idx = indices(s, list(pr.dates), reps, scheme_seed(rotulo, s))
        ivs[s] = inf.summarize(point, np.asarray(inf.stat_nb(pr, e_star, idx)))
    name, wide = inf.widest(ivs)
    ses = [v.se for v in ivs.values() if np.isfinite(v.se)]
    if not np.isfinite(wide.lo):
        decisao = INCONCLUSIVO
    elif wide.lo > 0:
        decisao = ADOTAR
    elif wide.hi < 0:
        decisao = NAO_ADOTAR
    else:
        decisao = INCONCLUSIVO
    return Decisao(float(e_star), len(pr.dates), float(inf.stat_d_served_day(pr)), float(inf.stat_d_empty_day(pr)), point,
                   wide.lo, wide.hi, name, inf.mde(max(ses)) if ses else float("nan"), decisao)


def dias_de_csv(path: Path, *, periodo: str, cenario: str, grupo: str | None = None, par: str | None = None,
                baseline: str = "sem_reposicionamento", campo_km: str = "empty_km") -> tuple[DiasAgregados, DiasAgregados]:
    """Lê um CSV diário agregado no formato `fase4_dias.csv` (ou `fase2_controle_dias.csv`) e devolve (plano, baseline)."""
    with open(path, encoding="utf-8", newline="") as h:
        rows = [r for r in csv.DictReader(h) if r["periodo"] == periodo]
    plano = {r["data"]: r for r in rows if r["cenario"] == cenario and (grupo is None or r["grupo"] == grupo)
             and (par is None or r.get("par") == par)}
    candidatos = [r for r in rows if r["cenario"] == baseline and (par is None or r.get("par") == par)]
    if grupo is not None and any(r["grupo"] == grupo for r in candidatos):    # arquivos em que o baseline herda o grupo do experimento
        candidatos = [r for r in candidatos if r["grupo"] == grupo]
    base = {r["data"]: r for r in candidatos}
    if len(base) != len(candidatos):
        raise ValueError("baseline ambíguo: informe `grupo` ou `par` para escolher um único baseline por dia")
    if not plano:
        raise ValueError("nenhuma linha do plano com esse filtro")
    datas = sorted(plano)
    faltam = [d for d in datas if d not in base]
    if faltam:
        raise ValueError(f"dias sem baseline: {faltam[:3]}")
    datas_d = tuple(date.fromisoformat(d) for d in datas)

    def bloco(m): return DiasAgregados(datas_d, tuple(float(m[d]["served"]) for d in datas), tuple(float(m[d][campo_km]) for d in datas))
    return bloco(plano), bloco(base)
