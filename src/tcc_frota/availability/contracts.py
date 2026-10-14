"""Contratos mínimos; nomes de colunas observados não validam sua semântica."""
from __future__ import annotations

from dataclasses import dataclass
from os.path import normcase
from pathlib import Path


@dataclass(frozen=True)
class SourceContract:
    name: str
    required: tuple[str, ...]
    time_columns: tuple[str, ...]
    key: str | None = None


CONTRACTS = (
    SourceContract("corridas_v1", ("CD_SOLICITACAO", "CD_VEICULO", "DT_INICIO_REALIZADA", "DT_FIM_REALIZADA", "TX_STATUS"), ("DT_REGISTRO", "DT_INICIO_REALIZADA", "DT_FIM_REALIZADA"), "CD_SOLICITACAO"),
    SourceContract("eventos_status_motoristas", ("CD_LOG_STATUS_MOTORISTA", "CD_VEICULO", "inicio_evento", "fim_evento", "qualidade_relacionamento"), ("inicio_evento", "fim_evento"), "CD_LOG_STATUS_MOTORISTA"),
    SourceContract("jornadas_motoristas", ("CD_JORNADA_MOTORISTA", "DT_INICIO_ESTIMADO", "DT_FIM_ESTIMADO", "DT_INICIO_REALIZADO", "DT_FIM_REALIZADO"), ("DT_INICIO_ESTIMADO", "DT_INICIO_REALIZADO", "DT_FIM_REALIZADO")),
    SourceContract("jornadas_corridas", ("CD_JORNADA_MOTORISTA", "CD_SOLICITACAO", "DT_INICIO_REALIZADA", "DT_FIM_REALIZADA"), ("DT_INICIO_REALIZADA", "DT_FIM_REALIZADA")),
    SourceContract("reposicionamentos", ("CD_REPOSICIONAMENTO_MOTORISTA", "CD_MOTORISTA", "DT_ACEITE", "DT_RECUSA", "DT_FIM"), ("DT_REGISTRO", "DT_ACEITE", "DT_FIM"), "CD_REPOSICIONAMENTO_MOTORISTA"),
    SourceContract("cobli_eventos", ("VEHICLE_ID", "TYPE", "START_ADDRESS_DATETIME", "END_ADDRESS_DATETIME"), ("START_ADDRESS_DATETIME", "END_ADDRESS_DATETIME")),
    SourceContract("veiculos", ("CD_VEICULO", "BL_EM_OPERACAO", "DT_DESATIVACAO"), ("DT_REGISTRO", "DT_DESATIVACAO"), "CD_VEICULO"),
    SourceContract("historico_veiculos", ("CD_HISTORICO_VEICULO", "DT_REGISTRO", "TX_STATUS"), ("DT_REGISTRO", "DT_PREVISAO_TERMINO"), "CD_HISTORICO_VEICULO"),
    SourceContract("agendamentos", ("ID_AGENDAMENTO", "CD_SOLICITACAO", "DT_AGENDAMENTO", "AG_STATUS"), ("DT_REGISTRO", "DT_AGENDAMENTO", "DT_DISTRIBUICAO"), "ID_AGENDAMENTO"),
)


def locate_source(root: Path, name: str) -> list[Path]:
    """Localiza CSVs atuais e Parquets futuros, inclusive partições ano/mês."""
    paths: list[Path] = []
    for suffix in ("csv", "parquet"):
        for candidate in (root / f"{name}.{suffix}", root / f"{name.upper()}.{suffix}"):
            if candidate.is_file():
                paths.append(candidate)
    directory = root / name
    if directory.is_dir():
        paths.extend(path for suffix in ("csv", "parquet") for path in directory.rglob(f"*.{suffix}") if path.is_file())
    unique: dict[str, Path] = {}
    for path in paths:
        unique.setdefault(normcase(str(path.resolve())), path)
    return sorted(unique.values())


def inventory(root: Path) -> list[dict[str, object]]:
    return [
        {"dataset": contract.name, "files": len(files), "formats": sorted({path.suffix.lstrip(".") for path in files}), "status": "PRESENTE" if files else "AUSENTE"}
        for contract in CONTRACTS
        for files in (locate_source(root, contract.name),)
    ]
