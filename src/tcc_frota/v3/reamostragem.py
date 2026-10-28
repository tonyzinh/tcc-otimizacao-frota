"""Reamostragem por dia com dependência (Fase 1): iid, estratificada por dia da semana e em blocos.

Todas as funções devolvem uma matriz (B, n) de índices de dias. A mesma matriz é reutilizada em todas as linhas
do mesmo período, o que preserva a dependência entre testes (necessária ao Romano–Wolf) e dá números aleatórios comuns.
"""
from __future__ import annotations

import zlib
from datetime import date

import numpy as np
from arch.bootstrap import CircularBlockBootstrap, StationaryBootstrap

SEED_BASE = 20261028
BLOCKS = (2, 3, 7)
SCHEMES = ("iid", "dow") + tuple(f"circular_b{b}" for b in BLOCKS) + tuple(f"estacionario_b{b}" for b in BLOCKS)


def scheme_seed(label: str, scheme: str) -> int:
    """Semente estável (não usa `hash`, que varia entre processos)."""
    return (SEED_BASE + zlib.crc32(f"{label}|{scheme}".encode())) % (2**32 - 1)


def indices(scheme: str, dates: list[date], reps: int, seed: int) -> np.ndarray:
    n = len(dates)
    if n < 2:
        raise ValueError("são necessários ao menos 2 dias")
    if scheme == "iid":
        return np.random.default_rng(seed).integers(0, n, size=(reps, n))
    if scheme == "dow":
        rng = np.random.default_rng(seed)
        out = np.empty((reps, n), dtype=np.int64)
        for weekday in {d.weekday() for d in dates}:
            pos = np.array([i for i, d in enumerate(dates) if d.weekday() == weekday])
            out[:, pos] = pos[rng.integers(0, len(pos), size=(reps, len(pos)))]
        return out
    kind, _, block = scheme.rpartition("_b")
    if kind not in ("circular", "estacionario") or not block.isdigit():
        raise ValueError(f"esquema desconhecido: {scheme}")
    cls = CircularBlockBootstrap if kind == "circular" else StationaryBootstrap
    boot = cls(int(block), np.arange(n), seed=seed)
    out = np.empty((reps, n), dtype=np.int64)
    for r in range(reps):
        out[r] = boot.update_indices()
    return out
