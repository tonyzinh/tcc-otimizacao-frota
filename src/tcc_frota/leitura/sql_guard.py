"""Lista de permissões para SQL: aceita apenas uma instrução `SELECT`/`WITH ... SELECT`.

É defesa em profundidade e falha fechada; não substitui permissões de leitura no login.
Literais, comentários e identificadores entre `[]`/`""` são neutralizados antes da checagem,
então uma coluna chamada `[Update]` ou um texto `'delete'` não disparam falso positivo.
"""

from __future__ import annotations

import re


class UnsafeQueryError(ValueError):
    """A consulta não é uma leitura simples aprovada."""


_FORBIDDEN = (
    "INSERT UPDATE DELETE MERGE DROP ALTER CREATE TRUNCATE EXEC EXECUTE GRANT REVOKE DENY BACKUP RESTORE "
    "SHUTDOWN RECONFIGURE DBCC WAITFOR OPENROWSET OPENQUERY OPENDATASOURCE BULK INTO DECLARE SET USE "
    "KILL PRINT RAISERROR THROW BEGIN COMMIT ROLLBACK SAVE CHECKPOINT"
).split()
_FORBIDDEN_RE = re.compile(r"\b(?:" + "|".join(_FORBIDDEN) + r")\b|\bNEXT\s+VALUE\b|\bXP_\w*|\bSP_\w*", re.I)


def _neutralize(sql: str) -> str:
    out: list[str] = []
    i, n = 0, len(sql)
    while i < n:
        c = sql[i]
        if sql.startswith("--", i):
            j = sql.find("\n", i)
            i = n if j < 0 else j
            out.append(" ")
        elif sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            if j < 0:
                raise UnsafeQueryError("comentário de bloco não fechado")
            i = j + 2
            out.append(" ")
        elif c in "'\"[":
            close = "]" if c == "[" else c
            j = i + 1
            while True:
                j = sql.find(close, j)
                if j < 0:
                    raise UnsafeQueryError("literal ou identificador não fechado")
                if close != "]" and sql.startswith(close * 2, j):
                    j += 2
                    continue
                if close == "]" and sql.startswith("]]", j):
                    j += 2
                    continue
                break
            out.append(" _ ")
            i = j + 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def assert_read_only(sql: str) -> str:
    """Devolve `sql` se for leitura simples; caso contrário levanta `UnsafeQueryError`."""
    if not isinstance(sql, str) or not sql.strip():
        raise UnsafeQueryError("consulta vazia")
    flat = _neutralize(sql).strip()
    body = flat[:-1].strip() if flat.endswith(";") else flat
    if ";" in body:
        raise UnsafeQueryError("apenas uma instrução por consulta")
    first = re.match(r"\(*\s*([A-Za-z]+)", body)
    if not first or first.group(1).upper() not in {"SELECT", "WITH"}:
        raise UnsafeQueryError("a consulta deve começar com SELECT ou WITH")
    hit = _FORBIDDEN_RE.search(body)
    if hit:
        raise UnsafeQueryError(f"termo não permitido em consulta somente leitura: {hit.group(0).upper()}")
    return sql


_SOURCE_RE = re.compile(r"\b(?:FROM|JOIN)\s+([A-Za-z0-9_.#@]+)", re.I)
_CATALOG_PREFIXES = ("information_schema.", "sys.")


def assert_catalog_only(sql: str) -> str:
    """Aceita só leitura cujas fontes são views de catálogo (`INFORMATION_SCHEMA.*`, `sys.*`): metadados, sem dados de negócio."""
    assert_read_only(sql)
    sources = _SOURCE_RE.findall(_neutralize(sql))
    if not sources:
        raise UnsafeQueryError("consulta de catálogo sem FROM")
    bad = [s for s in sources if not s.lower().startswith(_CATALOG_PREFIXES)]
    if bad:
        raise UnsafeQueryError("consulta de catálogo só pode ler INFORMATION_SCHEMA e sys")
    return sql
