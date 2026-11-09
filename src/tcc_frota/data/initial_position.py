"""Condições iniciais da referência: posição do veículo no início da jornada, respeitando o tempo.

Duas condições SEPARADAS (nenhuma equivale à outra):
  A. primeira_posicao_observada: usa a observação válida mais recente até o início da jornada (com idade máxima e sem
     deslocamento conhecido entre a observação e o início); se só houver observação DEPOIS do início, o intervalo inicial é
     DESCONHECIDO e o motorista só entra no despacho na primeira observação. Nunca se usa posição futura para localizar um instante
     anterior e nunca se extrapola uma posição através de viagem ou compromisso.
  B. matriz_configurada: todos partem de uma base física informada (hipótese explícita ou regra confirmada). Sem coordenadas
     informadas, levanta MatrizNaoDefinida; nenhuma coordenada é inventada. Não está comprovado que os veículos começam na base.

Unidades: segundos desde a meia-noite local do dia simulado; coordenadas em graus.
Nota D+1: a posição observada no dia-alvo pode inicializar o ambiente simulado, mas NÃO é informação conhecida pelo planejador
na véspera (`conhecida_pelo_planejador_vespera` é sempre False para observações do dia-alvo).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

CONDICOES = ("primeira_posicao_observada", "matriz_configurada")


class MatrizNaoDefinida(NotImplementedError):
    """A condição matriz_configurada exige coordenadas informadas; nenhuma é assumida."""


@dataclass(frozen=True)
class Matriz:
    lat: float
    lon: float
    fonte: str  # onde a base foi definida (regra confirmada ou hipótese do proprietário)


@dataclass(frozen=True)
class Observacao:
    t: float  # segundos (meia-noite local do dia simulado; pode ser negativo para a véspera)
    lat: float
    lon: float
    origem: str  # ex.: es.posicao_ofertas | ods.log_status


@dataclass(frozen=True)
class PosicaoInicial:
    estado: str  # conhecida_no_inicio | conhecida_apos_inicio | desconhecida | hipotese_matriz
    inicio_efetivo_s: float | None
    lat: float | None
    lon: float | None
    desconhecido_s: float
    idade_s: float | None
    origem: str | None
    t_observacao_s: float | None
    motivo: str
    conhecida_pelo_planejador_vespera: bool = False

    def asdict(self) -> dict:
        return asdict(self)


def _bloqueada(t_obs: float, t_ini: float, moveis: tuple[tuple[float, float], ...]) -> bool:
    """Há viagem/compromisso (intervalos de movimento) entre a observação e o início? Então a posição não vale no início."""
    return any(a < t_ini and b > t_obs for a, b in moveis)


def posicao_inicial(
    sessao: tuple[float, float],
    observacoes: list[Observacao],
    *,
    max_idade_s: float,
    moveis: tuple[tuple[float, float], ...] = (),
    condicao: str = "primeira_posicao_observada",
    matriz: Matriz | None = None,
) -> PosicaoInicial:
    s, e = sessao
    if condicao not in CONDICOES:
        raise ValueError(f"condição inicial desconhecida: {condicao}")
    if condicao == "matriz_configurada":
        if matriz is None:
            raise MatrizNaoDefinida("matriz_configurada exige coordenadas da base física (não encontradas nas regras nem nos cadastros)")
        return PosicaoInicial(
            "hipotese_matriz", s, matriz.lat, matriz.lon, 0.0, 0.0, f"hipotese:{matriz.fonte}", None, "hipótese de base física"
        )
    obs = sorted(observacoes, key=lambda o: o.t)
    antes = [o for o in obs if o.t <= s]
    if antes:
        o = antes[-1]
        idade = s - o.t
        if idade <= max_idade_s and not _bloqueada(o.t, s, moveis):
            return PosicaoInicial("conhecida_no_inicio", s, o.lat, o.lon, 0.0, idade, o.origem, o.t, "observação vigente no início")
        motivo_antes = "observação anterior velha demais" if idade > max_idade_s else "movimento conhecido entre a observação e o início"
    else:
        motivo_antes = "sem observação até o início"
    depois = [o for o in obs if s < o.t < e]
    if depois:
        o = depois[0]
        return PosicaoInicial(
            "conhecida_apos_inicio", o.t, o.lat, o.lon, o.t - s, 0.0, o.origem, o.t, f"{motivo_antes}; entra na 1ª observação"
        )
    return PosicaoInicial("desconhecida", None, None, None, e - s, None, None, None, f"{motivo_antes}; sem observação na jornada")


def construir_sessoes(
    jornadas: dict[str, list[tuple[float, float]]],
    observacoes: dict[str, list[Observacao]],
    *,
    max_idade_s: float,
    moveis: dict[str, tuple[tuple[float, float], ...]] | None = None,
    condicao: str = "primeira_posicao_observada",
    matriz: Matriz | None = None,
) -> tuple[dict[str, tuple[tuple[float, float, float, float], ...]], dict]:
    """Sessões (início efetivo, fim, lat, lon) para `SimDriver` e o relatório de cobertura perdida."""
    moveis = moveis or {}
    sessoes: dict[str, list] = {}
    contagem: dict[str, int] = {}
    perdido = total = 0.0
    detalhe: list[dict] = []
    for did, js in jornadas.items():
        for s, e in js:
            p = posicao_inicial(
                (s, e), observacoes.get(did, []), max_idade_s=max_idade_s, moveis=moveis.get(did, ()), condicao=condicao, matriz=matriz
            )
            contagem[p.estado] = contagem.get(p.estado, 0) + 1
            total += e - s
            perdido += p.desconhecido_s
            if p.estado != "desconhecida" and p.inicio_efetivo_s is not None:
                sessoes.setdefault(did, []).append((p.inicio_efetivo_s, e, p.lat, p.lon))
            detalhe.append({"estado": p.estado, "desconhecido_s": p.desconhecido_s, "idade_s": p.idade_s})
    relatorio = {
        "condicao": condicao,
        "max_idade_s": max_idade_s,
        "jornadas": sum(contagem.values()),
        "por_estado": contagem,
        "segundos_jornada_total": total,
        "segundos_desconhecidos": perdido,
        "pct_jornada_desconhecida": round(100 * perdido / total, 2) if total else None,
        "tratamento_do_desconhecido": "motorista indisponível ao despacho até a 1ª observação; jornada sem observação é excluída (contada)",
        "conhecida_pelo_planejador_vespera": False,
    }
    return {d: tuple(v) for d, v in sessoes.items()}, relatorio
