"""Guardas para leitura de Parquet autorizado em um Volume do Unity Catalog."""
from __future__ import annotations

import re
from pathlib import PurePosixPath


_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


def volume_parquet_path(value: str) -> str:
    """Aceita somente um arquivo ou diretório dentro de um Volume explícito.

    A validação não comprova autorização institucional nem existência do arquivo.
    """
    if not value or value != value.strip() or any(mark in value for mark in ("*", "?", "[", "]", "\\")):
        raise ValueError("informe um caminho literal de Parquet em /Volumes")
    path = PurePosixPath(value)
    parts = path.parts
    if str(path) != value or len(parts) < 6 or parts[0:2] != ("/", "Volumes") or ".." in value.split("/"):
        raise ValueError("Parquet deve estar dentro de /Volumes/<catalog>/<schema>/<volume>/<arquivo-ou-diretorio>")
    if not all(_IDENTIFIER.fullmatch(part) for part in parts[2:5]):
        raise ValueError("identificador de catálogo, esquema ou volume inválido")
    if any(part in {"", ".", ".."} for part in parts[5:]):
        raise ValueError("caminho de Parquet inválido")
    return value
