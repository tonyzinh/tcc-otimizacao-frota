"""Leitura do `.env` do projeto, tolerante ao formato real do arquivo.

O `.env` mistura linhas `KEY=valor` com comentários `-- ...`; por isso há um analisador próprio.
Lê só do arquivo (não de `os.environ`): variáveis como `USER` e `PASSWORD` colidem com as do
sistema operacional e apontariam para a conta errada.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class ConfigError(RuntimeError):
    """Configuração ausente ou inválida (nunca inclui valores de credenciais)."""


def default_env_path() -> Path:
    override = os.getenv("TCC_ENV_FILE")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[4] / ".env"  # src/tcc_frota/data/reading/env.py -> raiz do repositório


def parse_env(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.lstrip("﻿").splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "--")) or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not _KEY.fullmatch(key):
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def load_env(path: str | Path | None = None) -> dict[str, str]:
    target = Path(path) if path else default_env_path()
    if not target.is_file():
        raise ConfigError(f"arquivo de configuração não encontrado: {target.name}")
    return parse_env(target.read_text(encoding="utf-8-sig"))


def require(values: dict[str, str], *keys: str) -> None:
    missing = [k for k in keys if not values.get(k)]
    if missing:
        raise ConfigError("chaves ausentes ou vazias no .env: " + ", ".join(missing))
