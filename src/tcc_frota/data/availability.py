"""Tabela de evidências de disponibilidade e cenários explícitos (sensibilidade, NÃO limites garantidos).

Princípios:
  - presença no feed de ofertas é observação condicionada ao processo de oferta: não é cadastro da frota disponível, e a ausência
    de oferta não prova indisponibilidade;
  - "desconhecido" nunca vira "livre" automaticamente; cenários que o façam são rotulados como hipótese;
  - o histórico V1 (viagens observadas) explica estados reais na RECONSTRUÇÃO; na SIMULAÇÃO de uma política, a ocupação vem das
    viagens atribuídas pelo próprio simulador, nunca das viagens históricas (sem bloqueio duplo);
  - jornada registrada e compromissos externos são entradas comuns aos cenários, com natureza declarada.

Tempos: segundos desde a meia-noite local do dia; ES convertido do offset (analise/tempo.py).
"""

from __future__ import annotations

import pandas as pd

CADENCIA_ES_S = 120.0
GAP_MAX_S = 3 * CADENCIA_ES_S  # até 3 snapshots perdidos seguidos ainda contam como presença contínua
ESTADOS = ("ocupado_com_evidencia", "presente_sem_viagem_es", "em_jornada_registrada", "desconhecido")

#            fonte -> (o que permite afirmar, o que permanece desconhecido)
FONTES = {
    "es.posicao_ofertas": (
        "o veículo/motorista constava do processo de oferta no instante (snapshot a cada ~120 s, 16-86 veículos); com status 3 e "
        "solicitação associada, estava em viagem; posição GPS com horário",
        "se estava livre (enum de status é inferido); ausência não prova indisponibilidade; não é cadastro da frota",
    ),
    "ods.jornada_motorista": (
        "janela de atividade REGISTRADA para o condutor (início/fim realizados)",
        "pausas, quem dirigiu cada veículo, disponibilidade a cada instante; vínculo veículo-condutor é cadastral e pode divergir",
    ),
    "ods.log_status_motorista": (
        "eventos de status/login do motorista (família de ID do motorista)",
        "semântica de bl_login/tx_status não confirmada; CD_VEICULO_CONDUTOR vem vazio na fonte",
    ),
    "ods.solicitacao": (
        "viagens V1 observadas (aceite, início, fim, destino real): ocupação histórica",
        "só vale para reconstrução; na simulação, a ocupação é a do simulador",
    ),
    "ods.compromissos_externos": (
        "corridas fora do universo V1 (outro serviço/região) que ocuparam o veículo, com origem e destino",
        "quando passaram a ser conhecidas pelo planejador (known_at desconhecido; dt_registro é só hipótese)",
    ),
    "vinculo.motorista_veiculo": (
        "no instante, o motorista aparece com a placa no feed e/ou na solicitação",
        "vínculo fora desses instantes; placa pode ter mais de um motorista no dia",
    ),
}


def runs_es(o: pd.DataFrame, d0: pd.Timestamp, gap_max_s: float = GAP_MAX_S) -> pd.DataFrame:
    """Intervalos contínuos de presença no feed por motorista e classe (ocupado/presente_sem_viagem). `o` com t (s) e colunas do feed."""
    linhas = []
    o = o.dropna(subset=["t"]).sort_values(["cd_motorista", "t"])
    for did, g in o.groupby("cd_motorista"):
        ocup = (g.status == 3) & g.codigo_solicitacao.notna()
        t = g.t.to_numpy()
        cls = ocup.to_numpy()
        ini = 0
        for i in range(1, len(t) + 1):
            quebra = i == len(t) or (t[i] - t[i - 1] > gap_max_s) or (cls[i] != cls[ini])
            if quebra:
                a, b = t[ini], t[i - 1] + CADENCIA_ES_S
                linhas.append(
                    {
                        "motorista": did,
                        "placa": g.cd_veiculo_pseudo.iloc[ini],
                        "t_ini": float(a),
                        "t_fim": float(b),
                        "estado": "ocupado_com_evidencia" if cls[ini] else "presente_sem_viagem_es",
                        "fonte": "es.posicao_ofertas",
                        "certeza": "alta" if cls[ini] else "baixa",
                        "pos_lat": float(g.latitude.iloc[ini]),
                        "pos_lon": float(g.longitude.iloc[ini]),
                        "t_obs": float(a),
                        "conhecido_pelo_planejador": "nao_dia_alvo",
                    }
                )
                ini = i
    return pd.DataFrame(linhas)


def lacunas_desconhecidas(runs: pd.DataFrame) -> pd.DataFrame:
    """Entre duas presenças do mesmo motorista com lacuna > GAP_MAX_S: intervalo DESCONHECIDO (nunca 'livre')."""
    out = []
    for did, g in runs.sort_values(["motorista", "t_ini"]).groupby("motorista"):
        for (_, a), (_, b) in zip(g.iterrows(), g.iloc[1:].iterrows(), strict=False):
            if b.t_ini - a.t_fim > 1e-6:
                out.append(
                    {
                        "motorista": did,
                        "placa": a.placa,
                        "t_ini": a.t_fim,
                        "t_fim": b.t_ini,
                        "estado": "desconhecido",
                        "fonte": "lacuna_no_feed",
                        "certeza": "nenhuma",
                        "pos_lat": None,
                        "pos_lon": None,
                        "t_obs": None,
                        "conhecido_pelo_planejador": "nao_dia_alvo",
                    }
                )
    return pd.DataFrame(out)


def uniao(intervalos: list[tuple[float, float]], tol_s: float = 1e-9) -> list[tuple[float, float]]:
    out: list[list[float]] = []
    for a, b in sorted(intervalos):
        if out and a <= out[-1][1] + tol_s:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


def aparar_inicio_ocupado(runs: pd.DataFrame, gap_max_s: float = GAP_MAX_S) -> tuple[pd.DataFrame, dict]:
    """Inicialização com viagem histórica em andamento: NÃO inicializa como livre quem tem evidência de ocupação.

    Em cada janela contínua do motorista, as runs `ocupado_com_evidencia` do INÍCIO da janela são removidas: o veículo só entra no
    ambiente simulado quando a viagem histórica em andamento termina (aproximação registrada: usa a duração observada, informação
    do avaliador, igual para todas as políticas). Uma janela inteira ocupada desaparece. Depois da inicialização, só viagens
    simuladas determinam a ocupação.
    """
    tol = max(gap_max_s - CADENCIA_ES_S, 0.0)
    manter, janelas, ocupadas_no_inicio, aparado_s = [], 0, 0, 0.0
    for _, g in runs.sort_values(["motorista", "t_ini"]).groupby("motorista"):
        inicio_janela, fim_ant = True, None
        for idx, r in g.iterrows():
            if fim_ant is None or r.t_ini - fim_ant > tol:
                inicio_janela = True
                janelas += 1
            if inicio_janela and r.estado == "ocupado_com_evidencia":
                if fim_ant is None or r.t_ini - fim_ant > tol:
                    ocupadas_no_inicio += 1
                aparado_s += r.t_fim - r.t_ini
            else:
                inicio_janela = False
                manter.append(idx)
            fim_ant = r.t_fim
    return runs.loc[manter].copy(), {
        "janelas": janelas,
        "janelas_iniciadas_com_evidencia_de_ocupacao": ocupadas_no_inicio,
        "horas_aparadas_no_inicio": round(aparado_s / 3600, 2),
        "aproximacao": "entra ao fim da viagem histórica em andamento (duração observada; comum a todas as políticas)",
    }


def resolver_unicidade(runs: pd.DataFrame, tol_s: float = 150.0) -> tuple[pd.DataFrame, dict]:
    """Garante recursos únicos: uma placa não é dois veículos simultâneos e um motorista não está em duas placas ao mesmo tempo.

    Sobreposição maior que `tol_s` entre runs de motoristas diferentes na MESMA placa (ou da mesma pessoa em placas diferentes) é
    conflito: a run que começa depois é recortada para começar após a anterior (o trecho recortado vira desconhecido, contado).
    Sobreposição <= tol_s é arredondamento do fim (último snapshot + cadência). Vínculos ambíguos não são resolvidos por inferência.
    """
    r = runs.sort_values("t_ini").reset_index(drop=True).copy()
    out = {"conflitos_placa": 0, "conflitos_motorista": 0, "horas_excluidas": 0.0}
    for chave, campo in (("placa", "conflitos_placa"), ("motorista", "conflitos_motorista")):
        outro = "motorista" if chave == "placa" else "placa"
        fim_por = {}
        for i in r.index:
            k = r.at[i, chave]
            if k is None or (isinstance(k, float) and pd.isna(k)):
                continue
            prev = fim_por.get(k)
            if prev is not None and prev[1] != r.at[i, outro] and r.at[i, "t_ini"] < prev[0] - tol_s:
                novo_ini = prev[0]
                out[campo] += 1
                out["horas_excluidas"] += (min(novo_ini, r.at[i, "t_fim"]) - r.at[i, "t_ini"]) / 3600
                r.at[i, "t_ini"] = min(novo_ini, r.at[i, "t_fim"])
            fim_por[k] = (max(r.at[i, "t_fim"], prev[0] if prev else 0.0), r.at[i, outro])
    r = r[r.t_fim - r.t_ini > 1e-6]
    out["horas_excluidas"] = round(out["horas_excluidas"], 3)
    return r, out


def trocas_de_recurso(o: pd.DataFrame, janela_s: float = 1800.0) -> dict:
    """Trocas observadas: motorista entre placas e placa entre motoristas; distância entre a última e a primeira posição (sem teleporte)."""
    o = o.dropna(subset=["cd_motorista", "cd_veiculo_pseudo", "t"]).sort_values("t")
    res = {"placa_troca_de_motorista": 0, "motorista_troca_de_placa": 0, "mais_de_2km": 0, "mais_de_2km_e_ate_30min": 0}
    for chave, outro, campo in (
        ("cd_veiculo_pseudo", "cd_motorista", "placa_troca_de_motorista"),
        ("cd_motorista", "cd_veiculo_pseudo", "motorista_troca_de_placa"),
    ):
        for _, g in o.groupby(chave):
            g = g.reset_index(drop=True)
            mud = g[outro] != g[outro].shift()
            for i in g.index[mud][1:]:
                a, b = g.iloc[i - 1], g.iloc[i]
                res[campo] += 1
                dkm = _km(a.latitude, a.longitude, b.latitude, b.longitude)
                if dkm > 2.0:
                    res["mais_de_2km"] += 1
                    if b.t - a.t <= janela_s:
                        res["mais_de_2km_e_ate_30min"] += 1
    return res


def _km(la1, lo1, la2, lo2) -> float:
    from tcc_frota.domain.entities import reta_km

    return reta_km(float(la1), float(lo1), float(la2), float(lo2))


def cenario_evidencia_restrita(runs: pd.DataFrame, gap_max_s: float = GAP_MAX_S) -> dict[str, list[tuple[float, float]]]:
    """E: janelas online = presença contínua no feed (qualquer status). Lacunas ficam FORA (desconhecido != livre).

    Runs de classes diferentes (ocupado/presente) são emendados quando a distância entre eles é só a diferença entre a cadência e o
    intervalo real dos snapshots (< gap_max_s - cadência); lacunas reais (> gap_max_s entre snapshots) continuam separando janelas.
    """
    tol = max(gap_max_s - CADENCIA_ES_S, 0.0)
    return {d: uniao(list(zip(g.t_ini, g.t_fim, strict=True)), tol) for d, g in runs.groupby("motorista")}


def _intersecao(a: list[tuple[float, float]], b: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out = []
    for x0, x1 in a:
        for y0, y1 in b:
            lo, hi = max(x0, y0), min(x1, y1)
            if hi > lo:
                out.append((lo, hi))
    return uniao(out)


def cenario_jornada(
    runs: pd.DataFrame, jornadas: dict[str, list[tuple[float, float]]], *, gap_ponte_s: float = 1200.0, gap_max_s: float = GAP_MAX_S
) -> tuple[dict[str, list[tuple[float, float]]], dict]:
    """Cenário J (regra explícita; sensibilidade, NÃO limite garantido). Janela de disponibilidade do motorista =

        jornada registrada  ∩  presença no feed, estendida por pontes de lacunas <= `gap_ponte_s` (hipótese: pausa curta/falha do feed).

    - A jornada DELIMITA o período operacional; nunca é tratada inteira como tempo livre.
    - Dentro da jornada, lacunas do feed > `gap_ponte_s` são desconhecidas e ficam FORA (pausas e compromissos restringem).
    - Observações do feed fora da jornada são EXCLUÍDAS de J (conflito resolvido a favor da jornada) e contadas em horas.
    - Jornada sem nenhuma observação válida do feed na janela: sem posição para inicializar -> motorista não simulado (contado).
    - Motorista no feed sem jornada atribuída (ponte ausente/ambígua): mantém a janela de E (contado), pois não há como delimitar.
    - Planejador: nada disto é conhecido na véspera (jornada realizada e feed do dia-alvo são do avaliador); só a escala estimada seria.
    """
    base = cenario_evidencia_restrita(runs, gap_max_s)
    out: dict[str, list[tuple[float, float]]] = {}
    diag = {
        "motoristas_com_jornada": 0,
        "jornada_sem_feed": 0,
        "motoristas_sem_jornada_mantidos_como_E": 0,
        "horas_feed_fora_da_jornada": 0.0,
        "horas_ponte_adicionadas": 0.0,
    }
    for d, janelas in base.items():
        js = jornadas.get(d)
        if not js:
            out[d] = janelas
            diag["motoristas_sem_jornada_mantidos_como_E"] += 1
            continue
        diag["motoristas_com_jornada"] += 1
        ponte: list[tuple[float, float]] = []
        for (_a0, a1), (b0, _b1) in zip(janelas, janelas[1:], strict=False):
            if b0 - a1 <= gap_ponte_s:
                ponte.append((a1, b0))
        estendida = uniao(janelas + ponte)
        diag["horas_ponte_adicionadas"] += sum(e - s for s, e in _intersecao(ponte, uniao(js))) / 3600
        dentro = _intersecao(estendida, uniao(js))
        diag["horas_feed_fora_da_jornada"] += (
            sum(e - s for s, e in janelas) - sum(e - s for s, e in _intersecao(janelas, uniao(js)))
        ) / 3600
        if dentro:
            out[d] = dentro
    for d in jornadas:
        if d not in base:
            diag["jornada_sem_feed"] += 1  # jornada sem nenhuma observação do feed: sem posição válida
    return out, diag


def resumo_evidencias(tab: pd.DataFrame) -> dict:
    if tab.empty:
        return {}
    tab = tab.assign(horas=(tab.t_fim - tab.t_ini) / 3600)
    return {
        "linhas": int(len(tab)),
        "horas_por_estado_e_fonte": {f"{e}|{f}": round(float(h), 1) for (e, f), h in tab.groupby(["estado", "fonte"]).horas.sum().items()},
        "motoristas": int(tab.motorista.nunique()),
    }
