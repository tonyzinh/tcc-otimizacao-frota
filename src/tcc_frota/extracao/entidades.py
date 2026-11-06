"""Entidades extraíveis da V1 Viagens: consulta, esquema de saída, chaves e tratamento de privacidade.

Cada entidade devolve linhas já com `event_time` (quando ocorreu, no fuso da fonte), `available_at`
(quando passou a existir para o planejador; proxy declarado) e `ingested_at` (UTC, na extração).
Identificadores são pseudonimizados (sal local fora do Git); coordenadas de passageiro são arredondadas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from tcc_frota.extracao.filtro import FiltroV1

COORD_CASAS = 3  # ~110 m: arredondamento de coordenadas de passageiro (regra de privacidade)
_CAB = {"event_time": "timestamp", "available_at": "timestamp", "ingested_at": "timestamp_utc"}


@dataclass(frozen=True)
class EntidadeSql:
    nome: str
    banco: str
    sql: str  # parâmetros posicionais: ver `parametros`
    colunas: dict[str, str]  # coluna de saída -> tipo (string, int64, float64, bool, timestamp)
    chave: tuple[str, ...]
    evento: str  # coluna que vira event_time
    disponivel: str | None  # coluna que vira available_at (None = igual a event_time)
    pseudo: tuple[str, ...] = ()
    coords: tuple[str, ...] = ()
    snapshot: bool = False  # sem janela: foto do estado na extração
    casas: int = COORD_CASAS
    extra_params: tuple = ()  # parâmetros adicionais após região/janela (ex.: grupo Cobli)
    limites: str = ""
    tipo: Literal["sql"] = "sql"

    def parametros(self, f: FiltroV1, ini: str, fim: str) -> tuple:
        if self.snapshot:
            return (f.regiao,)
        if self.extra_params:
            return (ini, fim, *self.extra_params)
        if "DATEADD" in self.sql:  # coorte (região, janela±7d) e depois o filtro da própria janela
            return (f.regiao, ini, fim, ini, fim)
        return (f.regiao, ini, fim)


@dataclass(frozen=True)
class EntidadeEs:
    nome: str
    indice: str  # padrão com {aaaamm}
    campo_tempo: str
    colunas: dict[str, str]
    chave: tuple[str, ...]
    limites: str = ""
    pseudo: tuple[str, ...] = ()
    tipo: Literal["es"] = "es"
    extras: dict = field(default_factory=dict)


SEM_PRIME = "({a}.TX_MODELO_SOLICITACAO IS NULL OR {a}.TX_MODELO_SOLICITACAO <> 'Prime')"  # Prime fora (R-04)


def _servicos(f: FiltroV1) -> str:
    return f.servicos_sql


def sql_solicitacao(f: FiltroV1) -> str:
    return (
        "SELECT CD_SOLICITACAO, CD_PASSAGEIRO, CD_MOTORISTA, CD_VEICULO, CD_TIPO_SERVICO, CD_REGIAO, TX_STATUS, "
        "DT_REGISTRO, DT_INICIO_REALIZADA, DT_FIM_REALIZADA, "
        "TX_ORIGEM_LAT, TX_ORIGEM_LNG, TX_DESTINO_LAT, TX_DESTINO_LNG, TX_DESTINOREAL_LAT, TX_DESTINOREAL_LNG, "
        "TX_H3INDEX_ORIGEM, TX_H3INDEX_DESTINO, TX_H3INDEX_DESTINO_REAL, TX_H3INDEX_REPOSICIONAMENTO_REAL, "
        "NU_DISTPERCORRIDA, NU_DR_REAL, NU_DISTANCIA_ACEITE_CHEGUEI, NU_TEMPOPARADO, DE_TEMPO_ESPERA_PASSAGEIRO, "
        "CD_SOLICITACAO_RETRACAMENTO, CD_AGENDAMENTO, TX_TP_SOLICITACAO, TX_MODELO_SOLICITACAO, TX_TIPO_PRIME, "
        "EM_FIM_TURNO, LEGADO, DT_REGISTRO_ATUALIZACAO "
        f"FROM dbo.APP_SOLICITACAO_HIST WHERE CD_REGIAO = ? AND CD_TIPO_SERVICO IN ({_servicos(f)}) "
        f"AND {SEM_PRIME.format(a='APP_SOLICITACAO_HIST')} AND DT_REGISTRO >= ? AND DT_REGISTRO < ?"
    )


def _coorte(f: FiltroV1, alias: str) -> str:
    """Motoristas com ao menos uma solicitação V1 Viagens na região, em ±7 dias da janela (coorte da operação)."""
    return (
        f"EXISTS (SELECT 1 FROM dbo.APP_SOLICITACAO_HIST s WHERE s.CD_MOTORISTA = {alias}.CD_MOTORISTA "
        f"AND s.CD_REGIAO = ? AND s.CD_TIPO_SERVICO IN ({_servicos(f)}) AND {SEM_PRIME.format(a='s')} "
        "AND s.DT_REGISTRO >= DATEADD(day, -7, ?) AND s.DT_REGISTRO < DATEADD(day, 7, ?))"
    )


_LIM_COORTE = (
    "Sem campo de região na tabela: coorte = motoristas com solicitação V1 Viagens (região 1, serviços V1) em ±7 dias; "
    "motorista que também opere em outra região/produto na mesma semana não é separável com segurança."
)


def entidades_sql(f: FiltroV1) -> dict[str, EntidadeSql]:
    solic_cols = {
        "cd_solicitacao": "int64", "cd_passageiro": "string", "cd_motorista": "string", "cd_veiculo": "string",
        "cd_tipo_servico": "int64", "cd_regiao": "int64", "tx_status": "string",
        "dt_registro": "timestamp", "dt_inicio_realizada": "timestamp", "dt_fim_realizada": "timestamp",
        "tx_origem_lat": "float64", "tx_origem_lng": "float64", "tx_destino_lat": "float64", "tx_destino_lng": "float64",
        "tx_destinoreal_lat": "float64", "tx_destinoreal_lng": "float64",
        "tx_h3index_origem": "string", "tx_h3index_destino": "string", "tx_h3index_destino_real": "string",
        "tx_h3index_reposicionamento_real": "string",
        "nu_distpercorrida": "int64", "nu_dr_real": "int64", "nu_distancia_aceite_cheguei": "int64",
        "nu_tempoparado": "int64", "de_tempo_espera_passageiro": "float64",
        "cd_solicitacao_retracamento": "int64", "cd_agendamento": "int64", "tx_tp_solicitacao": "string",
        "tx_modelo_solicitacao": "string", "tx_tipo_prime": "string", "em_fim_turno": "bool", "legado": "bool",
        "dt_registro_atualizacao": "timestamp",
    }
    solic_cols = {k.lower(): v for k, v in solic_cols.items()}
    out: dict[str, EntidadeSql] = {}
    out["solicitacao"] = EntidadeSql(
        "solicitacao", "ODS", sql_solicitacao(f), {**_CAB, **solic_cols}, ("cd_solicitacao",), "dt_registro", "dt_registro_atualizacao",
        pseudo=("cd_passageiro", "cd_motorista", "cd_veiculo"),
        coords=("tx_origem_lat", "tx_origem_lng", "tx_destino_lat", "tx_destino_lng", "tx_destinoreal_lat", "tx_destinoreal_lng"),
        limites="dt_registro é proxy da criação; uma linha por solicitação no ODS (estado final, sem a cadeia de status); "
        "NU_DR_REAL/NU_DISTPERCORRIDA conforme RN; valores monetários não extraídos.",
    )
    out["status_solicitacao"] = EntidadeSql(
        "status_solicitacao", "ODS",
        "SELECT l.CD_LOG_STATUS_SOLICITACAO, l.CD_SOLICITACAO, l.DT_REGISTRO, l.TX_STATUS, l.CD_MOTORISTA, l.LEGADO "
        "FROM dbo.APP_LOG_STATUS_SOLICITACAO l JOIN dbo.APP_SOLICITACAO_HIST s ON s.CD_SOLICITACAO = l.CD_SOLICITACAO "
        f"WHERE s.CD_REGIAO = ? AND s.CD_TIPO_SERVICO IN ({_servicos(f)}) AND {SEM_PRIME.format(a='s')} AND s.DT_REGISTRO >= ? AND s.DT_REGISTRO < ?",
        {**_CAB, "cd_log_status_solicitacao": "int64", "cd_solicitacao": "int64", "dt_registro": "timestamp",
         "tx_status": "string", "cd_motorista": "string", "legado": "bool"},
        ("cd_log_status_solicitacao",), "dt_registro", None, pseudo=("cd_motorista",),
        limites="Lote por data de criação da solicitação (não do evento); eventos de uma solicitação podem cair no dia seguinte.",
    )
    out["jornada_motorista"] = EntidadeSql(
        "jornada_motorista", "ODS",
        "SELECT j.CD_JORNADA_MOTORISTA, j.CD_MOTORISTA, j.DT_REGISTRO, j.DT_INICIO_ESTIMADO, j.DT_FIM_ESTIMADO, "
        "j.DT_INICIO_REALIZADO, j.DT_FIM_REALIZADO, j.CD_TURNO_TRABALHO, j.CD_GRUPO_TURNO, j.CD_LOCAL_FIM_TURNO "
        "FROM dbo.APP_JORNADA_MOTORISTA j WHERE " + _coorte(f, "j") + " "
        "AND COALESCE(j.DT_INICIO_REALIZADO, j.DT_INICIO_ESTIMADO, j.DT_REGISTRO) >= ? "
        "AND COALESCE(j.DT_INICIO_REALIZADO, j.DT_INICIO_ESTIMADO, j.DT_REGISTRO) < ?",
        {**_CAB, "cd_jornada_motorista": "int64", "cd_motorista": "string", "dt_registro": "timestamp",
         "dt_inicio_estimado": "timestamp", "dt_fim_estimado": "timestamp", "dt_inicio_realizado": "timestamp",
         "dt_fim_realizado": "timestamp", "cd_turno_trabalho": "int64", "cd_grupo_turno": "int64", "cd_local_fim_turno": "int64"},
        ("cd_jornada_motorista",), "dt_registro", None, pseudo=("cd_motorista",), limites=_LIM_COORTE,
    )
    out["log_status_motorista"] = EntidadeSql(
        "log_status_motorista", "ODS",
        "SELECT l.CD_LOG_STATUS_MOTORISTA, l.CD_MOTORISTA, l.CD_MOTIVO, l.TX_STATUS, l.BL_LOGIN, l.DT_REGISTRO, l.CD_VEICULO "
        "FROM dbo.APP_LOG_STATUS_MOTORISTA l WHERE " + _coorte(f, "l") + " AND l.DT_REGISTRO >= ? AND l.DT_REGISTRO < ?",
        {**_CAB, "cd_log_status_motorista": "int64", "cd_motorista": "string", "cd_motivo": "int64", "tx_status": "string",
         "bl_login": "bool", "dt_registro": "timestamp", "cd_veiculo": "string"},
        ("cd_log_status_motorista",), "dt_registro", None, pseudo=("cd_motorista", "cd_veiculo"),
        limites=_LIM_COORTE + " Semântica dos códigos de status é enum inferido (não confirmado).",
    )
    out["reposicionamento"] = EntidadeSql(
        "reposicionamento", "ODS",
        "SELECT r.CD_REPOSICIONAMENTO_MOTORISTA, r.DT_REGISTRO, r.CD_MOTORISTA, r.TX_ORIGEM_LAT, r.TX_ORIGEM_LNG, "
        "r.TX_DESTINO_LAT, r.TX_DESTINO_LNG, r.TX_DESTINO_H3INDEX, r.TX_ORIGEM_REAL_LAT, r.TX_ORIGEM_REAL_LNG, "
        "r.TX_DESTINO_REAL_LAT, r.TX_DESTINO_REAL_LNG, r.DT_ACEITE, r.DT_RECUSA, r.DT_FIM, r.NU_METROS_PERCORRIDOS "
        "FROM dbo.APP_REPOSICIONAMENTO_MOTORISTA r WHERE " + _coorte(f, "r") + " AND r.DT_REGISTRO >= ? AND r.DT_REGISTRO < ?",
        {**_CAB, "cd_reposicionamento_motorista": "int64", "dt_registro": "timestamp", "cd_motorista": "string",
         "tx_origem_lat": "float64", "tx_origem_lng": "float64", "tx_destino_lat": "float64", "tx_destino_lng": "float64",
         "tx_destino_h3index": "string", "tx_origem_real_lat": "float64", "tx_origem_real_lng": "float64",
         "tx_destino_real_lat": "float64", "tx_destino_real_lng": "float64", "dt_aceite": "timestamp",
         "dt_recusa": "timestamp", "dt_fim": "timestamp", "nu_metros_percorridos": "int64"},
        ("cd_reposicionamento_motorista",), "dt_registro", None, pseudo=("cd_motorista",),
        limites=_LIM_COORTE + " Posições são de motorista (não de passageiro): mantidas sem arredondamento.",
    )
    out["veiculo"] = EntidadeSql(
        "veiculo", "ODS",
        "SELECT CD_VEICULO, CD_MODELO_VEICULO, CD_REGIAO, CD_TIPO_FROTA, DT_REGISTRO, DT_DESATIVACAO, TX_STATUS, "
        "BL_EM_OPERACAO, DT_ULTIMA_ATUALIZACAO, DT_REGISTRO_ATUALIZACAO, TX_SETOR, TX_TIPO_ESTOQUE "
        "FROM dbo.APP_VEICULO WHERE CD_REGIAO = ?",
        {**_CAB, "cd_veiculo": "string", "cd_modelo_veiculo": "int64", "cd_regiao": "int64", "cd_tipo_frota": "int64",
         "dt_registro": "timestamp", "dt_desativacao": "timestamp", "tx_status": "string", "bl_em_operacao": "bool",
         "dt_ultima_atualizacao": "timestamp", "dt_registro_atualizacao": "timestamp", "tx_setor": "string",
         "tx_tipo_estoque": "string"},
        ("cd_veiculo",), "dt_registro", "dt_registro_atualizacao", pseudo=("cd_veiculo",), snapshot=True,
        limites="Foto do estado na extração (sem histórico); TX_STATUS/DT_DESATIVACAO são posteriores à janela: "
        "não usar como informação disponível no corte D+1. Placa e chassi não extraídos.",
    )
    out["telemetria_cobli"] = EntidadeSql(
        "telemetria_cobli", "ODS",
        "SELECT DEVICE_ID, VEHICLE_ID, TYPE, DRIVER_ID, LICENSE_PLATE, START_ADDRESS_LATITUDE, START_ADDRESS_LONGITUDE, "
        "START_ADDRESS_DATETIME, END_ADDRESS_LATITUDE, END_ADDRESS_LONGITUDE, END_ADDRESS_DATETIME, DISTANCE_IN_METERS, "
        "DURATION_IN_MILLISECONDS, IDLE_TIME_DURATION_IN_MILLISECONDS "
        "FROM dbo.COBLI_TELEMETRIA_VIAGENS WHERE START_ADDRESS_DATETIME >= ? AND START_ADDRESS_DATETIME < ? AND VEHICLE_GROUP = ?",
        {**_CAB, "device_id": "string", "vehicle_id": "string", "type": "string", "driver_id": "string", "license_plate": "string",
         "start_address_latitude": "float64", "start_address_longitude": "float64", "start_address_datetime": "timestamp",
         "end_address_latitude": "float64", "end_address_longitude": "float64", "end_address_datetime": "timestamp",
         "distance_in_meters": "float64", "duration_in_milliseconds": "float64", "idle_time_duration_in_milliseconds": "float64"},
        ("device_id", "type", "start_address_datetime"), "start_address_datetime", "end_address_datetime",
        pseudo=("device_id", "vehicle_id", "driver_id", "license_plate"),
        coords=("start_address_latitude", "start_address_longitude", "end_address_latitude", "end_address_longitude"),
        casas=4, extra_params=("Operação",),
        limites="Filtro por VEHICLE_GROUP = 'Operação' (sem campo de região): validado em 10/03/2026 (106 de 113 placas com corrida V1 da região 1); "
        "o grupo 'Operação Prime' (14 de 16 placas com corrida V1 região 1) e 'Operação V1 VIX CAM' (4 de 4) ficam FORA, pendentes de decisão. "
        "Registra só início/fim de viagens e paradas (type trips/stops), não a trajetória ponto a ponto. available_at = fim do trecho. "
        "Nome do motorista não extraído; coordenadas de extremidade (endereços de embarque/desembarque) com 4 casas.",
    )
    return out


def entidades_es() -> dict[str, EntidadeEs]:
    return {
        "posicao_ofertas": EntidadeEs(
            "posicao_ofertas", "indexofertamotoristaelasticmodel-{aaaamm}", "dataHora",
            {**_CAB, "doc_codigo": "string", "evento_dataHora": "timestamp", "cd_motorista": "string", "cd_veiculo_pseudo": "string",
             "status": "int64", "latitude": "float64", "longitude": "float64", "h3_index": "string", "accuracy": "float64",
             "passageiro_embarcado": "bool", "data_posicao_gps": "timestamp", "data_atualizacao": "timestamp",
             "codigo_proxima_solicitacao": "int64", "codigo_solicitacao": "int64", "distancia_restante": "int64",
             "tempo_segundos_viagem_restante": "int64", "servicos": "string", "codigo_regiao": "int64"},
            ("doc_codigo", "cd_motorista"),
            limites="Foto do app a cada ~2 min por região; lista de veículos ofertados (não todos os online); status é enum inferido. "
            "Nome, telefone, login, playerId, placa em claro e foto não extraídos.",
        ),
        "sumario_ofertas": EntidadeEs(
            "sumario_ofertas", "indexsumarioofertamotorista-{aaaamm}", "dataHora",
            {**_CAB, "doc_codigo": "string", "codigo_regiao": "int64", "qtd_a_caminho": "int64", "qtd_aproveitamento": "int64",
             "qtd_com_passageiro": "int64", "qtd_indisponivel": "int64", "qtd_offline": "int64", "qtd_online": "int64",
             "qtd_selecionado": "int64"},
            ("doc_codigo",),
            limites="Contagem agregada por região, sem separar serviço: pode incluir motoristas de serviços não V1 na região 1.",
        ),
        "reposicionamento_sugerido": EntidadeEs(
            "reposicionamento_sugerido", "indexdriversfuture", "dataRegistro",
            {**_CAB, "doc_codigo": "string", "regiao_id": "int64", "user_id": "string", "h3": "string", "mode": "string",
             "id_motivo": "int64", "descricao_motivo": "string", "origem_lat": "float64", "origem_lng": "float64",
             "codigo_solicitacao": "int64", "reposicionamento_desligado": "bool", "distancia": "int64"},
            ("doc_codigo",), pseudo=("user_id",),
            limites="Semântica de mode/idMotivo não confirmada; é sugestão/registro do sistema, não deslocamento executado.",
        ),
    }
