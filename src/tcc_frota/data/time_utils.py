"""Conversões de tempo explícitas entre as fontes da V1 Viagens (America/Sao_Paulo, UTC-3 sem horário de verão desde 2019).

Convenções, com nível de evidência (docs/AVALIACAO_BASE_V1_VIAGENS.md):
  ods   : datetime ingênuo = hora local de Brasília (executado: ES-ODS, 4 dias, mediana ~1 min).
  es    : texto ISO com offset -03:00 = hora local (executado, mesmos 4 dias).
  cobli : datetime2 ingênuo = UTC (executado: teste de relógio 0/-3h/+3h em 4 dias).
RN024 (semântica oficial do carimbo de criação) segue pendente: aqui não se supõe; conversões não alteram o valor original,
que é preservado pelo chamador. Nenhuma subtração fixa genérica: cada fonte tem sua regra.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pandas as pd

LOCAL = timezone(timedelta(hours=-3), "America/Sao_Paulo(-03:00)")
UTC = UTC
FONTES = {"ods": "local", "es": "offset", "cobli": "utc"}


def para_local(valor, fonte: str):
    """Devolve o instante em hora local ingênua (Brasília). `valor`: datetime/Timestamp/str/NaT."""
    if valor is None or pd.isna(valor):
        return pd.NaT
    if fonte not in FONTES:
        raise ValueError(f"fonte de tempo desconhecida: {fonte}")
    t = pd.Timestamp(valor)
    if fonte == "ods":
        if t.tzinfo is not None:
            raise ValueError("ODS deve ser ingênuo (hora local); recebeu fuso")
        return t
    if fonte == "es":
        if t.tzinfo is None:
            raise ValueError("ES deve trazer offset; recebeu ingênuo")
        return t.tz_convert(LOCAL).tz_localize(None)
    if t.tzinfo is not None:
        raise ValueError("Cobli deve ser ingênuo (UTC); recebeu fuso")
    return t.tz_localize(UTC).tz_convert(LOCAL).tz_localize(None)


def serie_para_local(s: pd.Series, fonte: str) -> pd.Series:
    return pd.Series([para_local(v, fonte) for v in s], index=s.index, dtype="datetime64[ns]")


def dia_local_para_janela_utc(dia: str) -> tuple[datetime, datetime]:
    """Janela UTC ingênua [ini, fim) que cobre o dia local `dia` (usada para consultar a Cobli)."""
    ini = datetime.fromisoformat(dia).replace(tzinfo=LOCAL).astimezone(UTC).replace(tzinfo=None)
    return ini, ini + timedelta(days=1)


# --- Semântica temporal (esquema 2 das extrações) ---------------------------------------------------------------------
SEMANTICA = {
    "event_time": "horário do evento operacional na fonte (ES dataHora do snapshot; ODS dt_registro/dt_inicio_realizada...)",
    "gps_observado_em": "horário em que o GPS observou a posição (ES dataPosicaoGPS); normalmente ANTERIOR ao evento",
    "ultima_atualizacao_em": "horário da última atualização do registro na fonte (ES dataAtualizacao; ODS dt_registro_atualizacao); NÃO é atraso de ingestão",
    "extraido_em": "horário (UTC) da extração local; NÃO é ingestão histórica",
    "known_at": "horário em que o dado esteve disponível ao sistema: DESCONHECIDO (nulo) salvo evidência",
}


def conhecido_sob_hipotese(event_time, atraso_s: float):
    """HIPÓTESE de acesso (não evidência): o dado seria conhecido `atraso_s` segundos após o evento.

    Evidência de que NÃO há garantia: em 4 dias de ES, dataAtualizacao precede dataHora (carimbo do último GPS, não da entrega) e
    o ODS só traz a última atualização do registro. Não protege contra vazamento temporal: use cenários de atraso
    (configs/data/time_access_assumptions.yaml) e reporte sensibilidade.
    """
    if event_time is None or pd.isna(event_time):
        return pd.NaT
    return pd.Timestamp(event_time) + pd.Timedelta(seconds=atraso_s)


def idade_posicao_s(gps_observado_em, instante) -> float:
    """Idade (s) de uma posição no `instante`: posição conhecida pode estar velha e representar mal o veículo."""
    if gps_observado_em is None or pd.isna(gps_observado_em):
        return float("nan")
    return (pd.Timestamp(instante) - pd.Timestamp(gps_observado_em)).total_seconds()
