"""Leitura local sequencial sem materializar os extratos completos."""

from __future__ import annotations

import csv
from collections.abc import Iterator
from pathlib import Path
from typing import Any


def _csv_encoding(path: Path) -> str:
    with path.open("rb") as stream:
        head = stream.read(65536)
    try:
        head.decode("utf-8-sig")
        return "utf-8-sig"
    except UnicodeDecodeError:
        return "cp1252"


def source_schema(path: Path) -> dict[str, str]:
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding=_csv_encoding(path), newline="") as stream:
            header = next(csv.reader(stream), [])
        return dict.fromkeys(header, "csv_text")
    if path.suffix.lower() == ".parquet":
        import pyarrow.parquet as pq

        return {field.name: str(field.type) for field in pq.read_schema(path)}
    raise ValueError("formato de entrada não suportado")


def iter_rows(path: Path, columns: tuple[str, ...] | None = None) -> Iterator[dict[str, Any]]:
    """Parquet em batches; CSV em linhas. Falha se faltar coluna solicitada."""
    schema = source_schema(path)
    selected = columns or tuple(schema)
    missing = set(selected) - set(schema)
    if missing:
        raise ValueError(f"colunas ausentes: {sorted(missing)}")
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding=_csv_encoding(path), newline="") as stream:
            for row in csv.DictReader(stream):
                yield {name: row[name] for name in selected}
        return
    import pyarrow.parquet as pq

    reader = pq.ParquetFile(path)
    for batch in reader.iter_batches(batch_size=65536, columns=list(selected)):
        values = batch.to_pydict()
        for index in range(batch.num_rows):
            yield {name: values[name][index] for name in selected}
