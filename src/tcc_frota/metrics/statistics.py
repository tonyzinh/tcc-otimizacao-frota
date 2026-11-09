"""Estatística das comparações pareadas: bootstrap por blocos (dias), bootstrap por semente, correção de Holm e P90 agregado.

O dia (dados históricos) ou a semente (sintético) é a unidade de análise; nunca as corridas. Semente do bootstrap fixa (20261108).
"""

from __future__ import annotations

import numpy as np

BOOTSTRAP_SEED = 20261108
BOOTSTRAP_RESAMPLES = 10_000


def moving_block_bootstrap(x: np.ndarray, block: int = 7, n: int = BOOTSTRAP_RESAMPLES, seed: int = BOOTSTRAP_SEED) -> tuple[float, float]:
    """IC95% da média por bootstrap de blocos móveis (circular) sobre uma série diária.

    Args:
        x: série diária (ex.: diferença de km vazio entre políticas, uma por dia).
        block: tamanho do bloco em dias (respeita a dependência temporal curta).
        n: número de reamostragens.
        seed: semente do gerador.

    Returns:
        (limite inferior, limite superior) do IC95%; (nan, nan) se a série for vazia.
    """
    x = np.asarray(x, float)
    t = len(x)
    if t == 0:
        return float("nan"), float("nan")
    b = max(1, min(block, t))
    rng = np.random.default_rng(seed)
    k = int(np.ceil(t / b))
    means = np.empty(n)
    for i in range(n):
        start = rng.integers(0, t, k)
        idx = ((start[:, None] + np.arange(b)[None, :]) % t).ravel()[:t]
        means[i] = x[idx].mean()
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def seed_bootstrap(d: np.ndarray, n: int = BOOTSTRAP_RESAMPLES, seed: int = BOOTSTRAP_SEED) -> tuple[float, float, float]:
    """IC95% percentil da média e p bilateral por bootstrap simples sobre sementes independentes.

    Returns:
        (limite inferior, limite superior, p bilateral); o p mínimo é 1/n.
    """
    rng = np.random.default_rng(seed)
    means = d[rng.integers(0, len(d), (n, len(d)))].mean(axis=1)
    p = min(1.0, 2 * min(float((means <= 0).mean()), float((means >= 0).mean())))
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)), max(p, 1.0 / n)


def holm_adjust(p: list[float]) -> list[float]:
    """Valores p ajustados pelo método de Holm (step-down), na ordem original."""
    order = np.argsort(p)
    m = len(p)
    adjusted, running_max = [0.0] * m, 0.0
    for rank, i in enumerate(order):
        running_max = max(running_max, min(1.0, (m - rank) * p[i]))
        adjusted[i] = running_max
    return adjusted


def pooled_percentile(series_of_lists, q: float = 90.0) -> float:
    """Percentil `q` das esperas de todos os atendidos do período (lista de listas por dia concatenada)."""
    if not len(series_of_lists):
        return float("nan")
    w = np.concatenate([np.asarray(v, float) for v in series_of_lists])
    return float(np.percentile(w, q)) if len(w) else float("nan")
