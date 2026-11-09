"""Entidades extraíveis da V1 Viagens: consulta, esquema de saída, chaves e tratamento de privacidade.

Cada entidade devolve linhas já com `event_time` (quando ocorreu, no fuso da fonte), `known_at`
(quando o dado passou a estar disponível ao sistema: DESCONHECIDO = nulo, salvo evidência; a hipótese de acesso fica em config/hipoteses_tempo.yaml) e `extraido_em` (UTC, momento da extração local; NÃO é ingestão histórica).
Identificadores são pseudonimizados (sal local fora do Git); coordenadas de passageiro são arredondadas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from tcc_frota.data.extraction.filtro import FiltroV1

COORD_CASAS = 3  # ~110 m: arredondamento de coordenadas de passageiro (regra de privacidade)
_CAB = {"event_time": "timestamp", "known_at": "timestamp", "extraido_em": "timestamp_utc"}


@dataclass(frozen=True)
class EntidadeSql:
    nome: str
    banco: str
    sql: str  # parâmetros posicionais: ver `parametros`
    colunas: dict[str, str]  # coluna de saída -> tipo (string, int64, float64, bool, timestamp)
    chave: tuple[str, ...]
    evento: str  # coluna que vira event_time
    disponivel: str | None  # (reservado) coluna de disponibilidade comprovada; hoje nenhuma fonte a comprova, known_at fica nulo
    pseudo: tuple[str, ...] = ()
    coords: tuple[str, ...] = ()
    snapshot: bool = False  # sem janela: foto do estado na extração
    casas: int = COORD_CASAS
    extra_params: tuple = ()  # parâmetros adicionais após região/janela (ex.: grupo Cobli)
    coluna_lote: str | None = None  # se definida, permite ler VÁRIOS dias numa consulta e repartir por esta coluna (dia local)
    deslocamento_janela_h: int = 0  # relógio da fonte = local + N h (ex.: Cobli em UTC => 3): a consulta usa o dia local
    janela_livre: bool = False  # vigência/intervalo: não rejeita por event_time fora do dia (a consulta já filtra)
    plano_params: tuple[str, ...] = ()  # se definido, ordem explícita dos parâmetros: "regiao", "ini", "fim"
    limites: str = ""
    tipo: Literal["sql"] = "sql"

    def parametros(self, f: FiltroV1, ini: str, fim: str) -> tuple:
        if self.plano_params:
            valores = {"regiao": f.regiao, "ini": ini, "fim": fim}
            return tuple(valores[t] for t in self.plano_params)
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


def _coorte_condutor(f: FiltroV1, alias: str, coluna: str = "CD_MOTORISTA") -> str:
    """Condutores (família de ID da jornada) vinculados a veículos que atenderam V1 Viagens em ±7 dias da janela.

    A jornada usa `CD_CONDUTOR` (ponte `APP_VEICULO_CONDUTOR`), não o `CD_MOTORISTA` das solicitações: 0 de 168 em comum em 10/03/2026.
    """
    return (
        f"EXISTS (SELECT 1 FROM dbo.APP_VEICULO_CONDUTOR vc WHERE vc.CD_CONDUTOR = {alias}.{coluna} AND EXISTS ("
        f"SELECT 1 FROM dbo.APP_SOLICITACAO_HIST s WHERE s.CD_VEICULO = vc.CD_VEICULO AND s.CD_REGIAO = ? "
        f"AND s.CD_TIPO_SERVICO IN ({_servicos(f)}) AND {SEM_PRIME.format(a='s')} "
        "AND s.DT_REGISTRO >= DATEADD(day, -7, ?) AND s.DT_REGISTRO < DATEADD(day, 7, ?)))"
    )


_LIM_COORTE = (
    "Sem campo de região na tabela: coorte = motoristas com solicitação V1 Viagens (região 1, serviços V1) em ±7 dias; "
    "motorista que também opere em outra região/produto na mesma semana não é separável com segurança."
)


def entidades_sql(f: FiltroV1) -> dict[str, EntidadeSql]:
    solic_cols = {
        "cd_solicitacao": "int64",
        "cd_passageiro": "string",
        "cd_motorista": "string",
        "cd_veiculo": "string",
        "cd_tipo_servico": "int64",
        "cd_regiao": "int64",
        "tx_status": "string",
        "dt_registro": "timestamp",
        "dt_inicio_realizada": "timestamp",
        "dt_fim_realizada": "timestamp",
        "tx_origem_lat": "float64",
        "tx_origem_lng": "float64",
        "tx_destino_lat": "float64",
        "tx_destino_lng": "float64",
        "tx_destinoreal_lat": "float64",
        "tx_destinoreal_lng": "float64",
        "tx_h3index_origem": "string",
        "tx_h3index_destino": "string",
        "tx_h3index_destino_real": "string",
        "tx_h3index_reposicionamento_real": "string",
        "nu_distpercorrida": "int64",
        "nu_dr_real": "int64",
        "nu_distancia_aceite_cheguei": "int64",
        "nu_tempoparado": "int64",
        "de_tempo_espera_passageiro": "float64",
        "cd_solicitacao_retracamento": "int64",
        "cd_agendamento": "int64",
        "tx_tp_solicitacao": "string",
        "tx_modelo_solicitacao": "string",
        "tx_tipo_prime": "string",
        "em_fim_turno": "bool",
        "legado": "bool",
        "dt_registro_atualizacao": "timestamp",
    }
    solic_cols = {k.lower(): v for k, v in solic_cols.items()}
    out: dict[str, EntidadeSql] = {}
    out["solicitacao"] = EntidadeSql(
        "solicitacao",
        "ODS",
        sql_solicitacao(f),
        {**_CAB, **solic_cols},
        ("cd_solicitacao",),
        "dt_registro",
        "dt_registro_atualizacao",
        pseudo=("cd_passageiro", "cd_motorista", "cd_veiculo"),
        coluna_lote="dt_registro",
        coords=("tx_origem_lat", "tx_origem_lng", "tx_destino_lat", "tx_destino_lng", "tx_destinoreal_lat", "tx_destinoreal_lng"),
        limites="dt_registro é proxy da criação; uma linha por solicitação no ODS (estado final, sem a cadeia de status); "
        "NU_DR_REAL/NU_DISTPERCORRIDA conforme RN; valores monetários não extraídos.",
    )
    out["status_solicitacao"] = EntidadeSql(
        "status_solicitacao",
        "ODS",
        "SELECT l.CD_LOG_STATUS_SOLICITACAO, l.CD_SOLICITACAO, l.DT_REGISTRO, l.TX_STATUS, l.CD_MOTORISTA, l.LEGADO, s.DT_REGISTRO AS DT_SOLICITACAO "
        "FROM dbo.APP_LOG_STATUS_SOLICITACAO l JOIN dbo.APP_SOLICITACAO_HIST s ON s.CD_SOLICITACAO = l.CD_SOLICITACAO "
        f"WHERE s.CD_REGIAO = ? AND s.CD_TIPO_SERVICO IN ({_servicos(f)}) AND {SEM_PRIME.format(a='s')} AND s.DT_REGISTRO >= ? AND s.DT_REGISTRO < ?",
        {
            **_CAB,
            "cd_log_status_solicitacao": "int64",
            "cd_solicitacao": "int64",
            "dt_registro": "timestamp",
            "tx_status": "string",
            "cd_motorista": "string",
            "legado": "bool",
            "dt_solicitacao": "timestamp",
        },
        ("cd_log_status_solicitacao",),
        "dt_registro",
        None,
        pseudo=("cd_motorista",),
        coluna_lote="dt_solicitacao",
        limites="Lote por data de criação da solicitação (não do evento); eventos de uma solicitação podem cair no dia seguinte.",
    )
    out["jornada_motorista"] = EntidadeSql(
        "jornada_motorista",
        "ODS",
        "SELECT j.CD_JORNADA_MOTORISTA, j.CD_MOTORISTA AS CD_CONDUTOR, j.DT_REGISTRO, j.DT_INICIO_ESTIMADO, j.DT_FIM_ESTIMADO, "
        "j.DT_INICIO_REALIZADO, j.DT_FIM_REALIZADO, j.CD_TURNO_TRABALHO, j.CD_GRUPO_TURNO, j.CD_LOCAL_FIM_TURNO "
        "FROM dbo.APP_JORNADA_MOTORISTA j WHERE " + _coorte_condutor(f, "j") + " "
        "AND COALESCE(j.DT_INICIO_REALIZADO, j.DT_INICIO_ESTIMADO, j.DT_REGISTRO) >= ? "
        "AND COALESCE(j.DT_INICIO_REALIZADO, j.DT_INICIO_ESTIMADO, j.DT_REGISTRO) < ?",
        {
            **_CAB,
            "cd_jornada_motorista": "int64",
            "cd_condutor": "string",
            "dt_registro": "timestamp",
            "dt_inicio_estimado": "timestamp",
            "dt_fim_estimado": "timestamp",
            "dt_inicio_realizado": "timestamp",
            "dt_fim_realizado": "timestamp",
            "cd_turno_trabalho": "int64",
            "cd_grupo_turno": "int64",
            "cd_local_fim_turno": "int64",
        },
        ("cd_jornada_motorista",),
        "dt_registro",
        None,
        pseudo=("cd_condutor",),
        limites="Jornada é por CONDUTOR (CD_CONDUTOR), família de ID distinta do motorista das solicitações; coorte = condutores vinculados "
        "(APP_VEICULO_CONDUTOR) a veículos com solicitação V1 em ±7 dias. Condutor de veículo compartilhado com outro produto não é separável. "
        "Jornada registrada ≠ presença efetiva ≠ disponibilidade (DT_*_REALIZADO é janela de atividade registrada, não escala).",
    )
    out["log_status_motorista"] = EntidadeSql(
        "log_status_motorista",
        "ODS",
        "SELECT l.CD_LOG_STATUS_MOTORISTA, l.CD_MOTORISTA, l.CD_MOTIVO, l.TX_STATUS, l.BL_LOGIN, l.DT_REGISTRO, l.CD_VEICULO, l.CD_VEICULO_CONDUTOR "
        "FROM dbo.APP_LOG_STATUS_MOTORISTA l WHERE " + _coorte(f, "l") + " AND l.DT_REGISTRO >= ? AND l.DT_REGISTRO < ?",
        {
            **_CAB,
            "cd_log_status_motorista": "int64",
            "cd_motorista": "string",
            "cd_motivo": "int64",
            "tx_status": "string",
            "bl_login": "bool",
            "dt_registro": "timestamp",
            "cd_veiculo": "string",
            "cd_veiculo_condutor": "string",
        },
        ("cd_log_status_motorista",),
        "dt_registro",
        None,
        pseudo=("cd_motorista", "cd_veiculo", "cd_veiculo_condutor"),
        limites=_LIM_COORTE + " Semântica dos códigos de status é enum inferido (não confirmado).",
    )
    out["reposicionamento"] = EntidadeSql(
        "reposicionamento",
        "ODS",
        "SELECT r.CD_REPOSICIONAMENTO_MOTORISTA, r.DT_REGISTRO, r.CD_MOTORISTA, r.TX_ORIGEM_LAT, r.TX_ORIGEM_LNG, "
        "r.TX_DESTINO_LAT, r.TX_DESTINO_LNG, r.TX_DESTINO_H3INDEX, r.TX_ORIGEM_REAL_LAT, r.TX_ORIGEM_REAL_LNG, "
        "r.TX_DESTINO_REAL_LAT, r.TX_DESTINO_REAL_LNG, r.DT_ACEITE, r.DT_RECUSA, r.DT_FIM, r.NU_METROS_PERCORRIDOS "
        "FROM dbo.APP_REPOSICIONAMENTO_MOTORISTA r WHERE " + _coorte(f, "r") + " AND r.DT_REGISTRO >= ? AND r.DT_REGISTRO < ?",
        {
            **_CAB,
            "cd_reposicionamento_motorista": "int64",
            "dt_registro": "timestamp",
            "cd_motorista": "string",
            "tx_origem_lat": "float64",
            "tx_origem_lng": "float64",
            "tx_destino_lat": "float64",
            "tx_destino_lng": "float64",
            "tx_destino_h3index": "string",
            "tx_origem_real_lat": "float64",
            "tx_origem_real_lng": "float64",
            "tx_destino_real_lat": "float64",
            "tx_destino_real_lng": "float64",
            "dt_aceite": "timestamp",
            "dt_recusa": "timestamp",
            "dt_fim": "timestamp",
            "nu_metros_percorridos": "int64",
        },
        ("cd_reposicionamento_motorista",),
        "dt_registro",
        None,
        pseudo=("cd_motorista",),
        limites=_LIM_COORTE + " Posições são de motorista (não de passageiro): mantidas sem arredondamento.",
    )
    out["veiculo"] = EntidadeSql(
        "veiculo",
        "ODS",
        "SELECT CD_VEICULO, CD_MODELO_VEICULO, CD_REGIAO, CD_TIPO_FROTA, DT_REGISTRO, DT_DESATIVACAO, TX_STATUS, "
        "BL_EM_OPERACAO, DT_ULTIMA_ATUALIZACAO, DT_REGISTRO_ATUALIZACAO, TX_SETOR, TX_TIPO_ESTOQUE, "
        "TX_PLACA "
        "FROM dbo.APP_VEICULO WHERE CD_REGIAO = ?",
        {
            **_CAB,
            "cd_veiculo": "string",
            "cd_modelo_veiculo": "int64",
            "cd_regiao": "int64",
            "cd_tipo_frota": "int64",
            "dt_registro": "timestamp",
            "dt_desativacao": "timestamp",
            "tx_status": "string",
            "bl_em_operacao": "bool",
            "dt_ultima_atualizacao": "timestamp",
            "dt_registro_atualizacao": "timestamp",
            "tx_setor": "string",
            "tx_tipo_estoque": "string",
            "tx_placa": "string",
        },
        ("cd_veiculo",),
        "dt_registro",
        "dt_registro_atualizacao",
        pseudo=("cd_veiculo", "tx_placa"),
        snapshot=True,
        limites="Foto do estado na extração (sem histórico); TX_STATUS/DT_DESATIVACAO são posteriores à janela: "
        "não usar como informação disponível no corte D+1. Placa só como pseudônimo (ponte ODS↔ES↔Cobli: 117 de 117 placas Cobli de 10/03/2026 casam com TX_PLACA); IDs de integração Cobli não casam (0) e não foram extraídos; chassi não extraído.",
    )
    out["veiculo_condutor"] = EntidadeSql(
        "veiculo_condutor",
        "ODS",
        "SELECT vc.CD_VEICULO_CONDUTOR, vc.CD_VEICULO, vc.CD_CONDUTOR, vc.DT_CRIACAO, vc.DT_FIM FROM dbo.APP_VEICULO_CONDUTOR vc "
        "WHERE EXISTS (SELECT 1 FROM dbo.APP_SOLICITACAO_HIST s WHERE s.CD_VEICULO = vc.CD_VEICULO AND s.CD_REGIAO = ? "
        f"AND s.CD_TIPO_SERVICO IN ({_servicos(f)}) AND {SEM_PRIME.format(a='s')} "
        "AND s.DT_REGISTRO >= DATEADD(day, -7, ?) AND s.DT_REGISTRO < DATEADD(day, 7, ?)) "
        "AND vc.DT_CRIACAO < ? AND (vc.DT_FIM IS NULL OR vc.DT_FIM >= ?)",
        {
            **_CAB,
            "cd_veiculo_condutor": "string",
            "cd_veiculo": "string",
            "cd_condutor": "string",
            "dt_criacao": "timestamp",
            "dt_fim": "timestamp",
        },
        ("cd_veiculo_condutor",),
        "dt_criacao",
        "dt_criacao",
        pseudo=("cd_veiculo_condutor", "cd_veiculo", "cd_condutor"),
        janela_livre=True,
        plano_params=("regiao", "ini", "fim", "fim", "ini"),
        limites="Vínculo veículo-condutor com vigência (DT_CRIACAO..DT_FIM) válido em algum instante da janela, para veículos com solicitação V1 em ±7 dias. "
        "Ponte entre a família do motorista (log de status, via CD_VEICULO_CONDUTOR) e a do condutor (jornada). Vigência não prova quem dirigiu.",
    )
    out["compromissos_externos"] = EntidadeSql(
        "compromissos_externos",
        "ODS",
        "WITH v AS (SELECT DISTINCT x.CD_VEICULO FROM dbo.APP_SOLICITACAO_HIST x WHERE x.CD_REGIAO = ? "
        f"AND x.CD_TIPO_SERVICO IN ({_servicos(f)}) AND {SEM_PRIME.format(a='x')} AND x.CD_VEICULO IS NOT NULL "
        "AND x.DT_REGISTRO >= DATEADD(day, -7, ?) AND x.DT_REGISTRO < DATEADD(day, 7, ?)) "
        "SELECT s.CD_SOLICITACAO, s.CD_VEICULO, "
        "CASE WHEN s.TX_MODELO_SOLICITACAO = 'Prime' THEN 'prime' WHEN s.CD_REGIAO <> ? THEN 'outra_regiao' ELSE 'outro_servico' END AS TX_CATEGORIA, "
        "s.TX_STATUS, s.DT_REGISTRO, s.DT_INICIO_REALIZADA, s.DT_FIM_REALIZADA, s.TX_ORIGEM_LAT, s.TX_ORIGEM_LNG, "
        "s.TX_DESTINOREAL_LAT, s.TX_DESTINOREAL_LNG FROM dbo.APP_SOLICITACAO_HIST s JOIN v ON v.CD_VEICULO = s.CD_VEICULO "
        f"WHERE NOT (s.CD_REGIAO = ? AND s.CD_TIPO_SERVICO IN ({_servicos(f)}) AND {SEM_PRIME.format(a='s')}) "
        "AND s.DT_REGISTRO >= DATEADD(day, -7, ?) AND s.DT_REGISTRO < ? "
        "AND s.DT_INICIO_REALIZADA IS NOT NULL AND s.DT_INICIO_REALIZADA >= ? AND s.DT_INICIO_REALIZADA < ?",
        {
            **_CAB,
            "cd_solicitacao": "int64",
            "cd_veiculo": "string",
            "tx_categoria": "string",
            "tx_status": "string",
            "dt_registro": "timestamp",
            "dt_inicio_realizada": "timestamp",
            "dt_fim_realizada": "timestamp",
            "tx_origem_lat": "float64",
            "tx_origem_lng": "float64",
            "tx_destinoreal_lat": "float64",
            "tx_destinoreal_lng": "float64",
        },
        ("cd_solicitacao",),
        "dt_inicio_realizada",
        "dt_registro",
        pseudo=("cd_veiculo",),
        coords=("tx_origem_lat", "tx_origem_lng", "tx_destinoreal_lat", "tx_destinoreal_lng"),
        plano_params=("regiao", "ini", "fim", "regiao", "regiao", "ini", "fim", "ini", "fim"),
        limites="COMPROMISSO EXTERNO (condição de disponibilidade, NÃO demanda-alvo): corridas realizadas, de veículos que atenderam V1 Viagens "
        "em ±7 dias, que NÃO são V1 Viagens sem Prime (Prime, outro serviço, outra região). Mínimo para representar indisponibilidade: veículo "
        "pseudonimizado, categoria, horários, origem (onde o veículo precisa estar) e destino real (posição de liberação), com 3 casas; sem "
        "passageiro, motorista ou valores. dt_registro é a criação do compromisso na fonte, usada só como hipótese de conhecimento (known_at segue nulo; imediata ≈ início, agendada pode ser "
        "anterior): o planejador só pode conhecê-lo a partir daí. Não entra em demanda, atendimento nem KM vazio; só bloqueia o veículo. "
        "Cobre apenas o que está em APP_SOLICITACAO_HIST registrado até 7 dias antes do início (agendamento mais antigo escapa); "
        "outros usos do veículo (Aluguel, manutenção) NÃO estão aqui.",
    )
    out["telemetria_cobli"] = EntidadeSql(
        "telemetria_cobli",
        "ODS",
        "SELECT VEHICLE_GROUP, DEVICE_ID, VEHICLE_ID, TYPE, DRIVER_ID, LICENSE_PLATE, START_ADDRESS_LATITUDE, START_ADDRESS_LONGITUDE, "
        "START_ADDRESS_DATETIME, END_ADDRESS_LATITUDE, END_ADDRESS_LONGITUDE, END_ADDRESS_DATETIME, DISTANCE_IN_METERS, "
        "DURATION_IN_MILLISECONDS, IDLE_TIME_DURATION_IN_MILLISECONDS "
        "FROM dbo.COBLI_TELEMETRIA_VIAGENS WHERE START_ADDRESS_DATETIME >= ? AND START_ADDRESS_DATETIME < ? AND VEHICLE_GROUP IN (?, ?)",
        {
            **_CAB,
            "vehicle_group": "string",
            "device_id": "string",
            "vehicle_id": "string",
            "type": "string",
            "driver_id": "string",
            "license_plate": "string",
            "start_address_latitude": "float64",
            "start_address_longitude": "float64",
            "start_address_datetime": "timestamp",
            "end_address_latitude": "float64",
            "end_address_longitude": "float64",
            "end_address_datetime": "timestamp",
            "distance_in_meters": "float64",
            "duration_in_milliseconds": "float64",
            "idle_time_duration_in_milliseconds": "float64",
        },
        ("device_id", "type", "start_address_datetime"),
        "start_address_datetime",
        "end_address_datetime",
        pseudo=("device_id", "vehicle_id", "driver_id", "license_plate"),
        coords=("start_address_latitude", "start_address_longitude", "end_address_latitude", "end_address_longitude"),
        casas=4,
        extra_params=("Operação", "Operação V1 VIX CAM"),
        deslocamento_janela_h=3,
        coluna_lote="start_address_datetime",
        janela_livre=True,
        limites="Filtro por VEHICLE_GROUP IN ('Operação', 'Operação V1 VIX CAM') (sem campo de região; o segundo entra para ser INVESTIGADO, a coluna vehicle_group permite separá-lo; não prova que todo o grupo pertence ao estudo): validado em 10/03/2026 (106 de 113 placas com corrida V1 da região 1); "
        "o grupo 'Operação Prime' (14 de 16 placas com corrida V1 região 1) e 'Operação V1 VIX CAM' (4 de 4) ficam FORA, pendentes de decisão. "
        "Registra só início/fim de viagens e paradas (type trips/stops), não a trajetória ponto a ponto. known_at é desconhecido (o fim do trecho é só o evento). RELÓGIO: evidência de 10/03/2026 indica UTC (conciliação por placa melhora de 39% para 73% de corridas com par ao subtrair 3 h; mediana de 61 m entre fim do trecho e destino): event_time fica NA HORA DA FONTE (UTC), e o dia do lote é o dia LOCAL (janela deslocada em +3 h). "
        "Nome do motorista não extraído; coordenadas de extremidade (endereços de embarque/desembarque) com 4 casas.",
    )
    return out


def entidades_es() -> dict[str, EntidadeEs]:
    return {
        "posicao_ofertas": EntidadeEs(
            "posicao_ofertas",
            "indexofertamotoristaelasticmodel-{aaaamm}",
            "dataHora",
            {
                **_CAB,
                "doc_codigo": "string",
                "cd_motorista": "string",
                "cd_veiculo_pseudo": "string",
                "status": "int64",
                "latitude": "float64",
                "longitude": "float64",
                "h3_index": "string",
                "accuracy": "float64",
                "passageiro_embarcado": "bool",
                "gps_observado_em": "timestamp",
                "ultima_atualizacao_em": "timestamp",
                "codigo_proxima_solicitacao": "int64",
                "codigo_solicitacao": "int64",
                "distancia_restante": "int64",
                "tempo_segundos_viagem_restante": "int64",
                "servicos": "string",
                "codigo_regiao": "int64",
            },
            ("doc_codigo", "cd_motorista"),
            limites="Foto do app a cada ~2 min por região; lista de veículos ofertados (não todos os online); status é enum inferido. "
            "Nome, telefone, login, playerId, placa em claro e foto não extraídos.",
        ),
        "sumario_ofertas": EntidadeEs(
            "sumario_ofertas",
            "indexsumarioofertamotorista-{aaaamm}",
            "dataHora",
            {
                **_CAB,
                "doc_codigo": "string",
                "codigo_regiao": "int64",
                "qtd_a_caminho": "int64",
                "qtd_aproveitamento": "int64",
                "qtd_com_passageiro": "int64",
                "qtd_indisponivel": "int64",
                "qtd_offline": "int64",
                "qtd_online": "int64",
                "qtd_selecionado": "int64",
            },
            ("doc_codigo",),
            limites="Contagem agregada por região, sem separar serviço: pode incluir motoristas de serviços não V1 na região 1.",
        ),
        "reposicionamento_sugerido": EntidadeEs(
            "reposicionamento_sugerido",
            "indexdriversfuture",
            "dataRegistro",
            {
                **_CAB,
                "doc_codigo": "string",
                "regiao_id": "int64",
                "user_id": "string",
                "h3": "string",
                "mode": "string",
                "id_motivo": "int64",
                "descricao_motivo": "string",
                "origem_lat": "float64",
                "origem_lng": "float64",
                "codigo_solicitacao": "int64",
                "reposicionamento_desligado": "bool",
                "distancia": "int64",
            },
            ("doc_codigo",),
            pseudo=("user_id",),
            limites="Semântica de mode/idMotivo não confirmada; é sugestão/registro do sistema, não deslocamento executado.",
        ),
    }
