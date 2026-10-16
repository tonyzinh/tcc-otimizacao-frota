r"""5.5 Recozimento simulado: mesma representação, vizinhança e avaliação do LNS (5.4).

Aceita um vizinho pior com probabilidade exp(−ΔJ / T_e), T_e = T₀ · r^e (e = avaliação), e guarda o
melhor plano visto. Início: guloso de valor marginal do artigo (α = 0,2). A escolha final entre
plano inicial, melhor plano e plano vazio é feita nos pseudodias de aceitação, como no LNS.
"""
from __future__ import annotations

from math import exp

from tcc_frota.algoritmos.busca_local import BuscaLocalLNS


class RecozimentoSimulado(BuscaLocalLNS):
    family = "recozimento"

    def __init__(self, t0: float, resfriamento: float, avaliacoes: int, max_km: float, k: int = 2):
        super().__init__("guloso", avaliacoes, k, max_km)
        self.t0, self.resfriamento = t0, resfriamento

    @property
    def params(self) -> dict:
        return {"t0": self.t0, "resfriamento": self.resfriamento, "avaliacoes": self.avaliacoes, "k": self.k,
                "max_km": self.max_km}

    def accept(self, delta: float, step: int, rng) -> bool:
        if delta < -1e-12:
            return True
        t = self.t0 * self.resfriamento ** step
        return t > 0 and rng.random() < exp(-delta / t)
