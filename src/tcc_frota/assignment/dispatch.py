"""Atribuição de solicitações a veículos em lote: mais próximo FIFO (política B) e algoritmo Húngaro (política C).

Contrato (usado por `simulation.engine.simulate(batch_s=..., assigner=...)`): `policy(t, requests, candidates) -> [(request_id, driver_id)]`.
`candidates[request_id]` = [(distância reta em km, driver_id)] ordenada, só com motoristas ELEGÍVEIS (online, livres, no raio, sem conflito
de compromisso). A política vê apenas pedidos já chegados e o estado do instante `t`.

Formulação do Húngaro (lexicográfica, sem a saída trivial de "não atender ninguém"):
  maximizar o número de pedidos atendidos e, entre as soluções com esse máximo, minimizar a soma das distâncias de busca.
Implementação: custo de um par viável = d_ij - M, com M maior que qualquer soma possível de distâncias; "não atribuído" custa 0 (colunas
fictícias). Desempate determinístico: custo inteiro (metros*1e5 + índice i*nc + j).

Algoritmos:
  - `hungarian`: Kuhn-Munkres com potenciais duais e caminhos aumentantes de menor custo (implementação própria, O(n^2 m)).
    `scipy.optimize.linear_sum_assignment` NÃO é política; serve só de oráculo nos testes (compara nº de pares e soma das distâncias).
  - `nearest_fifo`: pedidos em ordem (chegada, id); cada um recebe o motorista elegível mais próximo ainda livre.

Nomes antigos (código congelado): guloso_fifo -> nearest_fifo, hungaro -> hungarian; o antigo `fluxo` (custo mínimo em rede) saiu do código
ativo e está no arquivo de preservação (ver docs/repository_migration.md).
"""

from __future__ import annotations

import numpy as np


def nearest_fifo(t, pedidos, candidatos):
    """Despacho atual sob a mesma janela: pedido mais antigo primeiro, motorista elegível mais próximo ainda livre."""
    usados: set[str] = set()
    saida = []
    for r in pedidos:
        for _d, did in candidatos.get(r.rid, ()):
            if did not in usados:
                saida.append((r.rid, did))
                usados.add(did)
                break
    return saida


def _matriz(pedidos, candidatos):
    """Custos inteiros e exatos: metros * 1e5 + índice (i*nc + j). O índice desempata de forma determinística e IGUAL para Húngaro e
    fluxo; com custos inteiros o ótimo é único na prática e as duas formulações devolvem o mesmo conjunto de pares."""
    rids = [r.rid for r in pedidos if r.rid in candidatos]
    dids = sorted({did for r in rids for _d, did in candidatos[r]})
    col = {d: j for j, d in enumerate(dids)}
    m = np.full((len(rids), len(dids)), np.inf)
    nc = max(len(dids), 1)
    for i, rid in enumerate(rids):
        for d, did in candidatos[rid]:
            m[i, col[did]] = round(d * 1000.0) * 1e5 + (i * nc + col[did])
    return rids, dids, m


def _big(m: np.ndarray) -> float:
    fin = m[np.isfinite(m)]
    return float(fin.max() * (m.shape[0] + 1) + 1.0) if fin.size else 1.0


def kuhn_munkres(a: np.ndarray) -> list[int]:
    """Húngaro (potenciais u, v; caminho aumentante) para matriz n x m com n <= m e custos finitos. Devolve a coluna de cada linha."""
    n, m = a.shape
    if n > m:
        raise ValueError("requer n <= m")
    u, v = np.zeros(n + 1), np.zeros(m + 1)
    p, way = [0] * (m + 1), [0] * (m + 1)
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [float("inf")] * (m + 1)
        usado = [False] * (m + 1)
        while True:
            usado[j0] = True
            i0, delta, j1 = p[j0], float("inf"), 0
            for j in range(1, m + 1):
                if not usado[j]:
                    cur = a[i0 - 1, j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j], way[j] = cur, j0
                    if minv[j] < delta:
                        delta, j1 = minv[j], j
            for j in range(m + 1):
                if usado[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
    res = [-1] * n
    for j in range(1, m + 1):
        if p[j]:
            res[p[j] - 1] = j - 1
    return res


def hungarian(t, pedidos, candidatos):
    rids, dids, inf = _matriz(pedidos, candidatos)
    if not rids:
        return []
    big = _big(inf)
    n, m = inf.shape
    a = np.zeros((n, m + n))  # colunas extras = "não atribuído" (custo 0)
    a[:, :m] = np.where(np.isfinite(inf), inf - big, 1e9)
    cols = kuhn_munkres(a)
    return [(rids[i], dids[j]) for i, j in enumerate(cols) if j < m and np.isfinite(inf[i, j])]


POLICIES = {"nearest_fifo": nearest_fifo, "hungarian": hungarian}
