"""Regras de limpeza da v2, puras e testadas (RN003, RN004, RN020, RN023, RN027).

Cada regra aqui tem equivalente nos notebooks `nb_slv_*_v2`. Mudanças devem ser feitas nos dois
lugares e cobertas por `tests/unit/test_v2_rules.py`.
"""
from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Sao_Paulo")

# Caixa aproximada da Grande Vitória (RN002 segue pendente para a fronteira exata).
BOX_LAT = (-20.6, -20.0)
BOX_LON = (-40.6, -40.0)

# `tX_DURACAO` está em ticks de 100 ns (.NET): razão mediana 1,0e7 contra fim − início (março/2026).
DURATION_TICKS_PER_SECOND = 10_000_000


@dataclass(frozen=True)
class StatusTreatment:
    grupo: str
    demanda: bool
    aceito: bool
    descricao: str


# Tabela de tratamento de status (RN004). A causa de cada desfecho não é atribuída.
STATUS_TREATMENT: dict[str, StatusTreatment] = {
    "CorridaEncerrada": StatusTreatment("atendida", True, True, "corrida concluída"),
    "CorridaCanceladaSolicitantePosAceite": StatusTreatment(
        "cancelada_pos_aceite_solicitante", True, True, "motorista aceitou; solicitante cancelou depois"),
    "CorridaCanceladaMotoristaPosAceite": StatusTreatment(
        "cancelada_pos_aceite_motorista", True, True, "motorista aceitou e cancelou depois"),
    "NaoAtendida": StatusTreatment("nao_atendida", True, False, "nenhum motorista aceitou"),
    "LimiteEsperaAtingido": StatusTreatment("nao_atendida_limite_espera", True, False,
                                            "tempo limite de espera atingido sem aceite"),
    "CorridaCanceladaSolicitante": StatusTreatment("cancelada_solicitante_pre_aceite", True, False,
                                                   "solicitante desistiu antes do aceite"),
    "PagamentoRejeitado": StatusTreatment("nao_demanda_pagamento", False, False,
                                          "pagamento rejeitado; não chega ao despacho"),
    "CorridaCanceladaOperador": StatusTreatment("nao_demanda_operador", False, False,
                                                "cancelada pela operação"),
    "Retracamento": StatusTreatment("nao_demanda_retracamento", False, False,
                                    "retraçamento; semântica não homologada"),
    "CorridaCanceladaAgendamento": StatusTreatment("nao_demanda_agendamento_cancelado", False, False,
                                                   "agendamento cancelado"),
    "CorridaIniciada": StatusTreatment("transitorio_sem_desfecho", False, False, "estado não final no extrato"),
    "CondutorACaminho": StatusTreatment("transitorio_sem_desfecho", False, False, "estado não final no extrato"),
    "CondutorChegou": StatusTreatment("transitorio_sem_desfecho", False, False, "estado não final no extrato"),
    "AguardandoCondutor": StatusTreatment("transitorio_sem_desfecho", False, False, "estado não final no extrato"),
}
UNKNOWN_STATUS = StatusTreatment("desconhecido", False, False, "status fora da tabela de tratamento")

# Enum de `ofertaList.status`, conferido contra os sumários (DT010).
DRIVER_STATES = {1: "ONLINE", 3: "EM_CORRIDA", 4: "SELECIONADO", 5: "INDISPONIVEL"}
WORKING_STATES = frozenset({1, 3, 4})

_TS = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d+))?(Z|[+-]\d\d:\d\d)$")


def treatment(status: str | None) -> StatusTreatment:
    return STATUS_TREATMENT.get(status or "", UNKNOWN_STATUS)


def parse_ts(value: str | None) -> datetime | None:
    """Carimbo ISO com 0–7 casas decimais e offset obrigatório, convertido a America/Sao_Paulo."""
    if value is None or value == "":
        return None
    match = _TS.match(value)
    if match is None:
        raise ValueError(f"carimbo fora do formato esperado: {value[:40]!r}")
    base, fraction, offset = match.groups()
    offset = "+00:00" if offset == "Z" else offset
    text = base + (("." + (fraction + "000000")[:6]) if fraction else "") + offset
    return datetime.fromisoformat(text).astimezone(TZ)


def coordinate(value: object) -> float | None:
    if value is None or value == "":
        return None
    number = float(value)
    return number if number == number else None


def in_box(lat: float | None, lon: float | None) -> bool:
    return (lat is not None and lon is not None and BOX_LAT[0] <= lat <= BOX_LAT[1]
            and BOX_LON[0] <= lon <= BOX_LON[1])


def round3(value: float | None) -> float | None:
    """Coordenada de passageiro com 3 casas (~110 m) da Silver em diante."""
    return None if value is None else round(value, 3)


def is_immediate(source: dict) -> bool:
    """Imediata = sem `dT_AGENDAMENTO`. `tX_TP_SOLICITACAO == TempoReal` inclui agendadas."""
    return source.get("dT_AGENDAMENTO") in (None, "")


def demand_time_basis(source: dict) -> tuple[str, datetime | None]:
    if is_immediate(source):
        return "dT_REGISTRO", parse_ts(source.get("dT_REGISTRO"))
    return "dT_AGENDAMENTO", parse_ts(source.get("dT_AGENDAMENTO"))


def trip_seconds(ticks: object) -> float | None:
    if ticks in (None, ""):
        return None
    seconds = float(ticks) / DURATION_TICKS_PER_SECOND
    return seconds if seconds > 0 else None


def times_ordered(registro, aceite, chegada, inicio, fim) -> bool:
    """Marcos presentes em ordem não decrescente; ausência não conta como desordem."""
    present = [t for t in (registro, aceite, chegada, inicio, fim) if t is not None]
    return all(a <= b for a, b in zip(present, present[1:]))


def load_salt(path: str | Path | None = None) -> str:
    """Sal da pseudonimização: variável `TCC_PSEUDO_SALT` ou arquivo local ignorado pelo Git."""
    salt = os.getenv("TCC_PSEUDO_SALT", "")
    if not salt:
        candidate = Path(path) if path else Path(__file__).resolve().parents[3] / "data" / ".pseudo_salt"
        if candidate.is_file():
            salt = candidate.read_text(encoding="utf-8").strip()
    if len(salt) < 16:
        raise PermissionError("defina TCC_PSEUDO_SALT ou data/.pseudo_salt (>= 16 caracteres, fora do Git)")
    return salt


def pseudonym(identifier: object, salt: str) -> str | None:
    """SHA-256 salgado, truncado em 16 hex. É pseudonimização, não anonimização."""
    if identifier in (None, ""):
        return None
    if len(salt) < 16:
        raise ValueError("sal curto demais")
    return hashlib.sha256(f"{salt}:{identifier}".encode()).hexdigest()[:16]


def h3_cell(lat: float | None, lon: float | None, resolution: int) -> str | None:
    if lat is None or lon is None:
        return None
    import h3

    return h3.latlng_to_cell(lat, lon, resolution)
