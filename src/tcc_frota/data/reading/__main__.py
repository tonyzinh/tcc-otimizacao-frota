"""`python -m tcc_frota.data.reading ping` verifica as conexões sem ler dados de negócio."""

from __future__ import annotations

import json
import sys

from tcc_frota.data.reading import ElasticReader, SqlServerReader
from tcc_frota.data.reading.sql_server import DATABASES


def main(argv: list[str]) -> int:
    if argv[:1] != ["ping"]:
        print("uso: python -m tcc_frota.data.reading ping [sql|es|todos]", file=sys.stderr)
        return 2
    target = argv[1] if len(argv) > 1 else "todos"
    result: dict[str, object] = {}
    status = 0
    if target in {"sql", "todos"}:
        for db in DATABASES:
            try:
                with SqlServerReader.from_env(db) as reader:
                    result[f"sql_{db}"] = reader.ping()
            except Exception as exc:  # relatório de diagnóstico
                result[f"sql_{db}"] = {"ok": False, "erro": f"{type(exc).__name__}: {exc}"}
                status = 1
    if target in {"es", "todos"}:
        try:
            result["elasticsearch"] = ElasticReader.from_env().ping()
        except Exception as exc:
            result["elasticsearch"] = {"ok": False, "erro": f"{type(exc).__name__}: {exc}"}
            status = 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return status


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
