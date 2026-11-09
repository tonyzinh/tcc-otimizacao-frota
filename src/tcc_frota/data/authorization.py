"""Portão de autorização de dados reais: só o proprietário levanta TCC_REAL_DATA_AUTHORIZED."""

from __future__ import annotations

import os


def authorize(dataset_kind: str, destination: str = "local") -> None:
    """Recusa o acesso a dados reais sem a variável de ambiente de autorização.

    Args:
        dataset_kind: "synthetic" ou "real".
        destination: "local" ou "external" (serviço externo exige autorização separada).

    Raises:
        ValueError: tipo ou destino desconhecido.
        PermissionError: dados reais sem TCC_REAL_DATA_AUTHORIZED=YES, ou destino externo sem TCC_EXTERNAL_DATA_AUTHORIZED=YES.
    """
    if dataset_kind not in {"synthetic", "real"}:
        raise ValueError("dataset_kind deve ser synthetic ou real")
    if destination not in {"local", "external"}:
        raise ValueError("destination inválido")
    if dataset_kind == "real" and os.getenv("TCC_REAL_DATA_AUTHORIZED") != "YES":
        raise PermissionError("dados reais exigem TCC_REAL_DATA_AUTHORIZED=YES e autorização formal")
    if dataset_kind == "real" and destination == "external" and os.getenv("TCC_EXTERNAL_DATA_AUTHORIZED") != "YES":
        raise PermissionError("ambiente externo exige autorização separada")
