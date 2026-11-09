"""Entradas do simulador a partir dos lotes do esquema 2 (V1 Viagens). Validação TÉCNICA do fluxo, não resultado científico.

Hipóteses (todas declaradas no manifesto da execução):
  - pedido = solicitação V1 com dt_registro no dia (proxy da criação; RN024 pendente); destino = destino real, senão o solicitado;
    duração da viagem = realizada, senão mediana do dia.
  - motorista online = presente nas ofertas do ES (posicao_ofertas); sessão = presença contínua com lacuna <= `gap_sessao_s`.
    Status/enum do ES NÃO é usado como "livre" (enum inferido).
  - posição inicial: condição A (ver posicao_inicial.py); a observação é a do próprio ES.
  - compromisso externo = corrida fora do universo (compromissos_externos) atribuída ao motorista pela placa (veículo -> placa -> ES);
    placa com mais de um motorista no dia não é atribuída (contada).
Tempos: segundos desde a meia-noite local do dia (ODS local; ES convertido do offset; ver analise/tempo.py).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from tcc_frota.data import availability as disp
from tcc_frota.data.initial_position import Observacao, construir_sessoes
from tcc_frota.data.time_utils import LOCAL
from tcc_frota.domain.entities import SimDriver, SimRequest

CADENCIA_ES_S = 120.0  # cadência aproximada dos snapshots (evidência indireta); fim de sessão = último snapshot + cadência


def _ler(raiz: Path, fonte: str, ent: str, dia: str, colunas: list[str] | None = None) -> pd.DataFrame | None:
    p = raiz / fonte / ent / f"dt={dia}" / "part-000.parquet"
    return pd.read_parquet(p, columns=colunas) if p.exists() else None


def _seg(ts: pd.Series, dia: pd.Timestamp, es: bool = False) -> pd.Series:
    if es:
        ts = ts.dt.tz_convert(LOCAL).dt.tz_localize(None)
    return (ts - dia).dt.total_seconds()


def _pedidos_de(s: pd.DataFrame, d0: pd.Timestamp, janela_s: tuple[float, float]) -> list[SimRequest]:
    """Solicitações do dia -> pedidos do simulador (destino real, senão o solicitado; duração realizada, senão a mediana do dia)."""
    real = (s.dt_fim_realizada - s.dt_inicio_realizada).dt.total_seconds()
    mediana = float(real[real > 0].median()) if (real > 0).any() else 600.0
    trip = real.where(real > 0, mediana)
    dlat = s.tx_destinoreal_lat.fillna(s.tx_destino_lat).fillna(s.tx_origem_lat)
    dlon = s.tx_destinoreal_lng.fillna(s.tx_destino_lng).fillna(s.tx_origem_lng)
    t = _seg(s.dt_registro, d0)
    return [
        SimRequest(int(c), float(tt), float(a), float(b), float(c2), float(d), float(tr), None, False, int(tt // 3600), "")
        for c, tt, a, b, c2, d, tr in zip(s.cd_solicitacao, t, s.tx_origem_lat, s.tx_origem_lng, dlat, dlon, trip, strict=True)
        if janela_s[0] <= tt < janela_s[1]
    ]


def pedidos_do_dia(
    raiz: Path, dia: str, tipos: tuple[str, ...] = ("TempoReal",), janela_s: tuple[float, float] = (0.0, 86400.0)
) -> list[SimRequest]:
    """Só os pedidos do dia (mesma regra de `montar`), sem frota nem compromissos: pseudodias de treino dos planejadores."""
    sol = _ler(raiz, "ods", "solicitacao", dia)
    if sol is None:
        return []
    d0 = pd.Timestamp(dia)
    s = sol.dropna(subset=["dt_registro", "tx_origem_lat", "tx_origem_lng"])
    s = s[(s.dt_registro >= d0) & (s.dt_registro < d0 + pd.Timedelta(days=1)) & s.tx_tp_solicitacao.isin(tipos)]
    return sorted(_pedidos_de(s, d0, janela_s), key=lambda r: (r.t, r.rid))


def montar(
    raiz: Path,
    dia: str,
    *,
    cenario: str = "E",
    gap_sessao_s: float = disp.GAP_MAX_S,
    max_idade_s: float = 1800.0,
    janela_s: tuple[float, float] = (0.0, 86400.0),
    tipos_incluidos: tuple[str, ...] = ("TempoReal",),
    deduplicar_tentativas: bool = False,
    com_compromissos: bool = True,
    gap_ponte_s: float = 1200.0,
) -> tuple[list[SimRequest], list[SimDriver], dict, dict]:
    d0 = pd.Timestamp(dia)
    sol = _ler(raiz, "ods", "solicitacao", dia)
    ofe = _ler(
        raiz,
        "es",
        "posicao_ofertas",
        dia,
        ["cd_motorista", "cd_veiculo_pseudo", "latitude", "longitude", "event_time", "gps_observado_em", "status", "codigo_solicitacao"],
    )
    com = _ler(raiz, "ods", "compromissos_externos", dia)
    vei = _ler(raiz, "ods", "veiculo", "snapshot", ["cd_veiculo", "tx_placa"])
    faltando = [n for n, x in (("solicitacao", sol), ("posicao_ofertas", ofe), ("veiculo", vei)) if x is None]
    if faltando:
        raise FileNotFoundError(f"entidades ausentes para {dia}: {faltando}")
    rel: dict = {"dia": dia, "tipo": "simulacao", "validado_empiricamente": False}

    # pedidos: universo = TODAS as solicitações do dia com origem; recortes só por TIPO (agendamento não tem modelo no despacho
    # imediato), explícitos e contados. Cancelados/não atendidos permanecem como demanda.
    s0 = sol.dropna(subset=["dt_registro", "tx_origem_lat", "tx_origem_lng"]).copy()
    s0 = s0[(s0.dt_registro >= d0) & (s0.dt_registro < d0 + pd.Timedelta(days=1))]
    s = s0[s0.tx_tp_solicitacao.isin(tipos_incluidos)].copy()
    rel["pedidos_excluidos_por_tipo"] = s0[~s0.tx_tp_solicitacao.isin(tipos_incluidos)].tx_tp_solicitacao.value_counts().to_dict()
    if deduplicar_tentativas:  # cenário de sensibilidade: mesmo passageiro, <=10 min, origem <=150 m -> mantém a primeira
        s = s.sort_values(["cd_passageiro", "dt_registro"])
        manter, ult = [], {}
        for r in s.itertuples():
            u = ult.get(r.cd_passageiro)
            rep = (
                u is not None
                and (r.dt_registro - u[0]).total_seconds() <= 600
                and max(abs(r.tx_origem_lat - u[1]) * 111_000, abs(r.tx_origem_lng - u[2]) * 105_000) <= 150
            )
            manter.append(not rep)
            if not rep:
                ult[r.cd_passageiro] = (r.dt_registro, r.tx_origem_lat, r.tx_origem_lng)
            else:
                ult[r.cd_passageiro] = (r.dt_registro, u[1], u[2])
        rel["pedidos_removidos_como_nova_tentativa"] = int(len(s) - sum(manter))
        s = s[pd.Series(manter, index=s.index)]
    reqs = _pedidos_de(s, d0, janela_s)
    rel["pedidos"] = len(reqs)
    rel["pedidos_sem_coordenada_descartados"] = int(len(sol) - len(s0))
    rel["pedidos_com_desfecho"] = s.tx_status.value_counts().to_dict()
    rel["definicao_universo"] = (
        "todas as solicitações V1 com origem no dia, tipos " + ",".join(tipos_incluidos) + "; sem excluir canceladas/não atendidas"
    )

    # presença no feed -> evidências e cenário de disponibilidade
    o = ofe.dropna(subset=["cd_motorista", "latitude", "longitude"]).copy()
    o["t"] = _seg(o.event_time, d0, es=True)
    rel["snapshots_es_sem_horario_descartados"] = int(o.t.isna().sum())
    o = o.dropna(subset=["t"]).sort_values(["cd_motorista", "t"])
    runs = disp.runs_es(o, d0, gap_sessao_s)
    rel["unicidade_de_recursos"] = disp.trocas_de_recurso(o) | {"resolucao": None}
    runs, info_u = disp.resolver_unicidade(runs)
    rel["unicidade_de_recursos"]["resolucao"] = info_u
    runs, info_i = disp.aparar_inicio_ocupado(runs, gap_sessao_s)
    rel["inicializacao_viagens_em_andamento"] = info_i
    jornadas = disp.cenario_evidencia_restrita(runs, gap_sessao_s)
    rel["cenario_disponibilidade"] = cenario
    if cenario == "J":
        jr, info = jornadas_registradas(raiz, dia, o, vei)
        jornadas, info_j = disp.cenario_jornada(runs, jr, gap_ponte_s=gap_ponte_s, gap_max_s=gap_sessao_s)
        rel["jornada_registrada"] = info | {"regra_J": info_j}
    elif cenario != "E":
        raise ValueError("cenário de disponibilidade desconhecido (E ou J)")
    rel["evidencias"] = disp.resumo_evidencias(pd.concat([runs, disp.lacunas_desconhecidas(runs)], ignore_index=True))
    obs: dict[str, list[Observacao]] = {
        did: [
            Observacao(float(x), float(la), float(lo), "es.posicao_ofertas") for x, la, lo in zip(g.t, g.latitude, g.longitude, strict=True)
        ]
        for did, g in o.groupby("cd_motorista")
    }
    sessoes, cob = construir_sessoes(jornadas, obs, max_idade_s=max_idade_s)
    rel["condicao_inicial"] = cob
    rel["motoristas_online_es"] = len(jornadas)

    # compromissos externos -> motorista via placa
    compromissos: dict[str, list[tuple]] = {}
    nao_atribuidos = 0
    if com_compromissos and com is not None and len(com):
        placa_de = dict(zip(vei.cd_veiculo, vei.tx_placa, strict=False))
        mot_por_placa = o.groupby("cd_veiculo_pseudo").cd_motorista.unique()
        for r in com.dropna(subset=["dt_inicio_realizada", "dt_fim_realizada", "tx_destinoreal_lat"]).itertuples():
            placa = placa_de.get(r.cd_veiculo)
            ms = mot_por_placa.get(placa) if placa is not None else None
            if ms is None or len(ms) != 1:
                nao_atribuidos += 1
                continue
            a, b = (r.dt_inicio_realizada - d0).total_seconds(), (r.dt_fim_realizada - d0).total_seconds()
            if b > a:
                o_lat, o_lng = r.tx_origem_lat, r.tx_origem_lng
                compromissos.setdefault(ms[0], []).append(
                    (
                        a,
                        b,
                        float(r.tx_destinoreal_lat),
                        float(r.tx_destinoreal_lng),
                        None if pd.isna(o_lat) else float(o_lat),
                        None if pd.isna(o_lng) else float(o_lng),
                    )
                )
    v1 = {r.rid for r in reqs}
    rel["compromissos_que_sao_pedidos_v1_simulados (deve ser 0)"] = (
        int(com.cd_solicitacao.isin(v1).sum()) if com is not None and len(com) else 0
    )
    rel["compromissos_atribuidos"] = int(sum(len(v) for v in compromissos.values()))
    rel["compromissos_nao_atribuidos_por_placa"] = nao_atribuidos
    origens: dict[tuple[str, int], tuple[float, float]] = {}
    drivers = []
    for did, v in sorted(sessoes.items()):
        lst = sorted(compromissos.get(did, ()), key=lambda x: x[:4])
        for i, x in enumerate(lst):
            if x[4] is not None and x[5] is not None:
                origens[(did, i)] = (x[4], x[5])
        drivers.append(SimDriver(did, tuple(sorted(v)), tuple(x[:4] for x in lst)))
    rel["motoristas_simulados"] = len(drivers)
    rel["hipoteses"] = {
        "gap_sessao_s": gap_sessao_s,
        "max_idade_s": max_idade_s,
        "online": "presente em posicao_ofertas (status/enum não usado como livre)",
        "pedido": "dt_registro como proxy da criação (RN024 pendente)",
        "compromissos": "conhecidos pelo despacho do simulador desde o início (hipótese; known_at desconhecido)",
    }
    return sorted(reqs, key=lambda r: (r.t, r.rid)), drivers, rel, origens


def origens_por_motorista(drivers, origens: dict[tuple[str, int], tuple[float, float]]) -> dict[str, list]:
    """`commit_origins` do simulador: origem de cada compromisso na ordem de `sorted(d.commitments)`; None = desconhecida."""
    return {d.did: [origens.get((d.did, i)) for i in range(len(d.commitments))] for d in drivers}


def jornadas_registradas(raiz: Path, dia: str, o: pd.DataFrame, vei: pd.DataFrame) -> tuple[dict[str, list[tuple[float, float]]], dict]:
    """Jornada REGISTRADA (por condutor) levada ao motorista via vínculo vigente -> veículo -> placa -> motorista do feed no dia.

    Hipótese de ponte (vínculo cadastral não prova quem dirigiu); ambiguidades (placa com 2+ motoristas, condutor com 0 ou 2+ veículos
    vigentes) NÃO são resolvidas: são contadas e a jornada é descartada. A parte do dia anterior de jornadas que cruzam a meia-noite
    não é carregada (lote do dia anterior) e é contada como limitação.
    """
    d0 = pd.Timestamp(dia)
    jor = _ler(raiz, "ods", "jornada_motorista", dia)
    vc = _ler(raiz, "ods", "veiculo_condutor", dia)
    info: dict = {"disponivel": jor is not None and vc is not None}
    if not info["disponivel"]:
        return {}, info
    placa_de = dict(zip(vei.cd_veiculo, vei.tx_placa, strict=False))
    mot_por_placa = o.groupby("cd_veiculo_pseudo").cd_motorista.unique()
    out: dict[str, list[tuple[float, float]]] = {}
    cont = {
        "jornadas": 0,
        "sem_horario": 0,
        "sem_vinculo_vigente": 0,
        "varios_veiculos": 0,
        "placa_sem_motorista_no_feed": 0,
        "placa_com_varios_motoristas": 0,
        "usadas": 0,
    }
    for r in jor.itertuples():
        cont["jornadas"] += 1
        if pd.isna(r.dt_inicio_realizado):
            cont["sem_horario"] += 1
            continue
        fim = (
            r.dt_fim_realizado
            if pd.notna(r.dt_fim_realizado)
            else min(r.dt_inicio_realizado + pd.Timedelta(hours=12), d0 + pd.Timedelta(days=1))
        )
        v = vc[
            (vc.cd_condutor == r.cd_condutor)
            & (vc.dt_criacao <= r.dt_inicio_realizado)
            & (vc.dt_fim.isna() | (vc.dt_fim > r.dt_inicio_realizado))
        ]
        if v.empty:
            cont["sem_vinculo_vigente"] += 1
            continue
        if v.cd_veiculo.nunique() > 1:
            cont["varios_veiculos"] += 1
            continue
        placa = placa_de.get(v.cd_veiculo.iloc[0])
        ms = mot_por_placa.get(placa) if placa is not None else None
        if ms is None:
            cont["placa_sem_motorista_no_feed"] += 1
            continue
        if len(ms) > 1:
            cont["placa_com_varios_motoristas"] += 1
            continue
        a, b = (r.dt_inicio_realizado - d0).total_seconds(), (fim - d0).total_seconds()
        a, b = max(a, 0.0), min(b, 86400.0)
        if b > a:
            out.setdefault(ms[0], []).append((a, b))
            cont["usadas"] += 1
    info.update(cont)
    return out, info
