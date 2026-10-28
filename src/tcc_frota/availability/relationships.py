"""Cobertura de chaves entre extratos; coincidência de ID não valida vínculo temporal."""

from __future__ import annotations

from pathlib import Path

from tcc_frota.availability.contracts import locate_source
from tcc_frota.availability.diagnostics import missing_value
from tcc_frota.availability.io import iter_rows


def _keys(root: Path, dataset: str, column: str) -> set[str] | None:
    paths = locate_source(root, dataset)
    if not paths:
        return None
    result: set[str] = set()
    for path in paths:
        for row in iter_rows(path, (column,)):
            if not missing_value(row[column]):
                result.add(str(row[column]).strip())
    return result


def relationship_coverage(root: Path) -> list[dict[str, object]]:
    comparisons = (
        ("eventos_status_motoristas", "CD_JORNADA_MOTORISTA", "jornadas_motoristas", "CD_JORNADA_MOTORISTA"),
        ("jornadas_corridas", "CD_SOLICITACAO", "corridas_v1", "CD_SOLICITACAO"),
        ("agendamentos", "CD_SOLICITACAO", "corridas_v1", "CD_SOLICITACAO"),
        ("cobli_eventos", "placa", "veiculos", "placa"),
    )
    cache: dict[tuple[str, str], set[str] | None] = {}
    results: list[dict[str, object]] = []
    for left_name, left_key, right_name, right_key in comparisons:
        for pair in ((left_name, left_key), (right_name, right_key)):
            if pair not in cache:
                cache[pair] = _keys(root, *pair)
        left = cache[(left_name, left_key)]
        right = cache[(right_name, right_key)]
        if left is None or right is None:
            results.append({"left": left_name, "right": right_name, "status": "FONTE_AUSENTE"})
            continue
        results.append(
            {
                "left": left_name,
                "right": right_name,
                "left_distinct": len(left),
                "right_distinct": len(right),
                "overlap_distinct": len(left & right),
                "left_only_distinct": len(left - right),
                "right_only_distinct": len(right - left),
                "interpretation": "coincidência de chave apenas; validade temporal e semântica não verificadas",
            }
        )
    return results
