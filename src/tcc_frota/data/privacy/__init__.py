"""Privacidade: pseudonimização estável e guarda do segredo."""

from tcc_frota.data.privacy.pseudonimizacao import (
    ESQUEMA,
    PseudonimizacaoError,
    Segredo,
    SegredoAusente,
    SegredoIncompativel,
    carregar_segredo,
    garantir_compatibilidade,
    pseudonimo,
)

__all__ = [
    "ESQUEMA",
    "PseudonimizacaoError",
    "Segredo",
    "SegredoAusente",
    "SegredoIncompativel",
    "carregar_segredo",
    "garantir_compatibilidade",
    "pseudonimo",
]
