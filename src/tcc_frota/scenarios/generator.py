"""Gerador sintético, parametrizado e reproduzível, de frota, histórico e demanda sobre a geografia pública da Grande Vitória.

Tudo que NÃO é geografia é HIPÓTESE EXPERIMENTAL SINTÉTICA, rotulada como tal na tabela de parâmetros (`tabela_parametros`). Nenhuma estatística
de dados privados é usada. As concentrações de demanda são localizadas no mapa por conveniência experimental e NÃO representam fluxos reais.

Aleatoriedade: `numpy.random.SeedSequence([ESCOPO, id_do_cenario_numerico, semente, canal])`; o mesmo (cenário, semente) gera sempre os mesmos dados,
e canais separados (histórico, dia avaliado, frota, previsão) evitam que mudar uma parte altere as outras.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace

import numpy as np

from tcc_frota.domain.entities import SimDriver, SimRequest
from tcc_frota.scenarios.geography import Pontos, haversine_km

VERSAO_GERADOR = "1.0.0"
ESCOPO = 20261108

HORAS = tuple(range(6, 22))  # horas locais com solicitações (hipótese)
TURNOS_INICIO_H = (6, 8, 10, 12)  # hipótese: início de jornada
DURACAO_JORNADA_H = 9.0

# Âncoras públicas do mapa (pontos de referência; a intensidade associada é HIPÓTESE sintética, não observação)
ANCORAS = {
    "centro_vitoria": (-20.3155, -40.3128),
    "praia_da_costa": (-20.3427, -40.2896),
    "campo_grande": (-20.3358, -40.3919),
    "jardim_camburi": (-20.2650, -40.2700),
}


@dataclass(frozen=True)
class Operacao:
    """Parâmetros operacionais comuns a todos os cenários (hipóteses experimentais)."""

    velocidade_kmh: float = 25.0
    raio_despacho_km: float = 8.0  # por via (piloto só com a referência: com 5–6 km a referência atende <80% mesmo com demanda baixa)
    paciencia_s: float = 600.0
    dist_viagem_escala_km: float = 6.0  # escala da distribuição de destinos (decaimento exponencial por via)
    sigma_hub_km: float = 3.0
    fracao_hubs: float = 0.7
    dias_historico: int = 28
    dias_para_kappa: int = 3


@dataclass(frozen=True)
class Cenario:
    id: str
    descricao: str
    espacial: str  # "uniforme" | "hubs" | "movel"
    posicao_inicial: str = "uniforme"  # "uniforme" | "concentrada"
    desvio: str = "nenhum"  # "nenhum" | "hubs_trocados" (o dia avaliado difere do padrão do histórico)
    n_veiculos: int = 100
    pedidos_por_veiculo: float = 8.0  # relação demanda/frota (hipótese de intensidade)
    previsao: str = "historico"  # "historico" | "perfeita" (DIAGNÓSTICO idealizado)
    sigma_previsao: float = 0.0  # erro multiplicativo lognormal adicional, controlado
    res_zona: int = 7
    max_km_guloso: float = 3.0
    codigo: int = 0  # entra na semente

    def com(self, **kw) -> Cenario:
        return replace(self, **kw)


# ------------------------------------------------------------------ demanda esperada
HUBS_PADRAO = {
    "centro_vitoria": [(9.0, 1.5, 1.0), (18.0, 1.5, 0.8)],
    "praia_da_costa": [(19.0, 2.0, 1.0)],
    "campo_grande": [(7.5, 1.2, 1.0)],
}
HUBS_MOVEL = {  # janelas quase disjuntas: a região quente muda ao longo do dia
    "campo_grande": [(7.5, 1.1, 1.0)],
    "centro_vitoria": [(13.0, 1.6, 1.0)],
    "praia_da_costa": [(19.0, 1.4, 1.0)],
}
TROCA_HUBS = {"centro_vitoria": "campo_grande", "campo_grande": "centro_vitoria", "praia_da_costa": "praia_da_costa"}


@dataclass
class Mundo:
    pontos: Pontos
    zonas: list[str]  # ids H3 da resolução de planejamento
    zona_idx: np.ndarray  # por ponto
    pontos_da_zona: list[np.ndarray]
    zona_lat: np.ndarray  # centro (média) dos pontos da zona
    zona_lon: np.ndarray
    chave: dict = field(default_factory=dict)

    @staticmethod
    def de(pontos: Pontos, res_zona: int) -> Mundo:
        import h3

        zonas_pt = np.array([h3.cell_to_parent(str(c), res_zona) for c in pontos.celula])
        zonas = sorted(set(zonas_pt))
        zi = {z: i for i, z in enumerate(zonas)}
        idx = np.array([zi[z] for z in zonas_pt])
        pz = [np.where(idx == i)[0] for i in range(len(zonas))]
        zl = np.array([pontos.lat[a].mean() for a in pz])
        zo = np.array([pontos.lon[a].mean() for a in pz])
        chave = {(round(float(a), 6), round(float(b), 6)): i for i, (a, b) in enumerate(zip(pontos.lat, pontos.lon, strict=True))}
        return Mundo(pontos, zonas, idx, pz, zl, zo, chave)


class MetricaRede:
    """Distância por via entre pontos do mundo (km). Posição fora do conjunto de pontos é erro: nada se teletransporta nem anda em linha reta."""

    def __init__(self, m: Mundo):
        self.m = m

    def km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        a = self.m.chave[(round(lat1, 6), round(lon1, 6))]
        b = self.m.chave[(round(lat2, 6), round(lon2, 6))]
        return float(self.m.pontos.dist_km[a, b])


class MetricaRapida:
    """Mesma distância de `MetricaRede` (menor caminho entre pontos do mundo), com consulta exata antes do arredondamento.

    Só acelera: devolve valores idênticos. Posição fora do conjunto de pontos continua sendo erro."""

    def __init__(self, m: Mundo):
        self.m = m
        self._exato = {(float(a), float(b)): i for i, (a, b) in enumerate(zip(m.pontos.lat, m.pontos.lon, strict=True))}

    def _idx(self, lat: float, lon: float) -> int:
        i = self._exato.get((lat, lon))
        return i if i is not None else self.m.chave[(round(lat, 6), round(lon, 6))]

    def km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        return float(self.m.pontos.dist_km[self._idx(lat1, lon1), self._idx(lat2, lon2)])


def _perfil_base() -> np.ndarray:
    h = np.array(HORAS, float)
    p = 1.0 + 0.6 * np.exp(-(((h - 8.5) / 1.8) ** 2)) + 0.7 * np.exp(-(((h - 18.0) / 2.0) ** 2))
    return p / p.sum()


def lambda_esperado(c: Cenario, op: Operacao, m: Mundo, dia_avaliado: bool) -> np.ndarray:
    """Matriz esperada de pedidos λ[hora_idx, zona_idx] (soma = pedidos_por_veiculo × n_veiculos)."""
    total = c.pedidos_por_veiculo * c.n_veiculos
    nz = len(m.zonas)
    base = np.outer(_perfil_base(), np.ones(nz) / nz)
    if c.espacial == "uniforme":
        return total * base
    hubs = HUBS_MOVEL if c.espacial == "movel" else HUBS_PADRAO
    frac = 0.8 if c.espacial == "movel" else op.fracao_hubs
    hs = np.array(HORAS, float)
    cobertura = np.zeros((len(HORAS), nz))
    for nome, janelas in hubs.items():
        ancora = TROCA_HUBS[nome] if (dia_avaliado and c.desvio == "hubs_trocados") else nome
        lat, lon = ANCORAS[ancora]
        dkm = haversine_km(lat, lon, m.zona_lat, m.zona_lon)
        espaco = np.exp(-0.5 * (dkm / op.sigma_hub_km) ** 2)
        for centro, sigma_h, peso in janelas:
            tempo = peso * np.exp(-0.5 * ((hs - centro) / sigma_h) ** 2)
            cobertura += np.outer(tempo, espaco)
    cobertura = cobertura / cobertura.sum()
    return total * ((1 - frac) * base + frac * cobertura)


# ------------------------------------------------------------------ frota
def gerar_frota(c: Cenario, m: Mundo, rng: np.random.Generator) -> list[dict]:
    n = c.n_veiculos
    ini = rng.choice(TURNOS_INICIO_H, size=n)
    if c.posicao_inicial == "uniforme":
        pts = rng.integers(0, len(m.pontos), n)
    else:  # frota desequilibrada: 85% perto de um ponto de concentração distante dos hubs, o resto uniforme
        la, lo = ANCORAS["jardim_camburi"]
        ref = int(np.argmin(haversine_km(la, lo, m.pontos.lat, m.pontos.lon)))
        perto = np.where(m.pontos.dist_km[ref] <= 4.0)[0]
        pts = np.where(rng.random(n) < 0.85, rng.choice(perto, n), rng.integers(0, len(m.pontos), n))
    return [
        {"did": f"V{i:03d}", "inicio_h": float(ini[i]), "fim_h": float(ini[i] + DURACAO_JORNADA_H), "ponto": int(pts[i])} for i in range(n)
    ]


def frota_para_sim(frota: list[dict], m: Mundo) -> list[SimDriver]:
    return [
        SimDriver(
            v["did"], ((v["inicio_h"] * 3600.0, v["fim_h"] * 3600.0, float(m.pontos.lat[v["ponto"]]), float(m.pontos.lon[v["ponto"]])),)
        )
        for v in frota
    ]


# ------------------------------------------------------------------ pedidos
def gerar_pedidos(lam: np.ndarray, op: Operacao, m: Mundo, rng: np.random.Generator, id0: int = 0) -> tuple[list[SimRequest], np.ndarray]:
    """Pedidos do dia a partir de λ (Poisson por hora×zona, chegada uniforme na hora, origem uniforme entre os pontos da zona, destino por decaimento
    exponencial da distância por via). Devolve (pedidos, contagem[hora, zona])."""
    cont = rng.poisson(lam)
    reqs: list[SimRequest] = []
    rid = id0
    d = m.pontos.dist_km
    for hi, h in enumerate(HORAS):
        for zi in np.nonzero(cont[hi])[0]:
            for _ in range(int(cont[hi, zi])):
                o = int(rng.choice(m.pontos_da_zona[zi]))
                w = np.exp(-d[o] / op.dist_viagem_escala_km)
                w[o] = 0.0
                dest = int(rng.choice(len(w), p=w / w.sum()))
                t = h * 3600.0 + float(rng.random()) * 3600.0
                trip_s = float(d[o, dest] / op.velocidade_kmh * 3600.0)
                reqs.append(
                    SimRequest(
                        rid,
                        t,
                        float(m.pontos.lat[o]),
                        float(m.pontos.lon[o]),
                        float(m.pontos.lat[dest]),
                        float(m.pontos.lon[dest]),
                        trip_s,
                        None,
                        False,
                        int(h),
                        m.zonas[zi],
                    )
                )
                rid += 1
    reqs.sort(key=lambda r: (r.t, r.rid))
    return reqs, cont


def rng_de(c: Cenario, semente: int, canal: str) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence([ESCOPO, c.codigo, semente, sum(ord(x) * (i + 1) for i, x in enumerate(canal))]))


def tabela_parametros(c: Cenario, op: Operacao) -> list[dict]:
    """Nome, unidade, valor, justificativa e classe de cada parâmetro (hipótese experimental ou informação geográfica)."""
    hip = "hipótese experimental"
    geo = "informação geográfica"
    return [
        {
            "nome": "velocidade_kmh",
            "unidade": "km/h",
            "valor": op.velocidade_kmh,
            "justificativa": "velocidade média efetiva urbana constante, escolhida sem calibrar em dados privados",
            "classe": hip,
        },
        {
            "nome": "raio_despacho_km",
            "unidade": "km por via",
            "valor": op.raio_despacho_km,
            "justificativa": "limite de busca do despacho ao mais próximo",
            "classe": hip,
        },
        {
            "nome": "paciencia_s",
            "unidade": "s",
            "valor": op.paciencia_s,
            "justificativa": "prazo máximo de espera do passageiro (homogêneo)",
            "classe": hip,
        },
        {
            "nome": "dist_viagem_escala_km",
            "unidade": "km",
            "valor": op.dist_viagem_escala_km,
            "justificativa": "escala do decaimento exponencial da distância origem-destino",
            "classe": hip,
        },
        {
            "nome": "sigma_hub_km",
            "unidade": "km",
            "valor": op.sigma_hub_km,
            "justificativa": "largura espacial das concentrações de demanda",
            "classe": hip,
        },
        {
            "nome": "fracao_hubs",
            "unidade": "fração",
            "valor": op.fracao_hubs,
            "justificativa": "parcela da demanda nas concentrações (restante: fundo uniforme)",
            "classe": hip,
        },
        {
            "nome": "turnos_inicio_h",
            "unidade": "h",
            "valor": list(TURNOS_INICIO_H),
            "justificativa": "horários possíveis de início de jornada",
            "classe": hip,
        },
        {"nome": "duracao_jornada_h", "unidade": "h", "valor": DURACAO_JORNADA_H, "justificativa": "jornada homogênea", "classe": hip},
        {
            "nome": "horas_com_pedidos",
            "unidade": "h local",
            "valor": [HORAS[0], HORAS[-1] + 1],
            "justificativa": "janela de solicitações",
            "classe": hip,
        },
        {
            "nome": "dias_historico",
            "unidade": "dias",
            "valor": op.dias_historico,
            "justificativa": "histórico sintético usado na previsão",
            "classe": hip,
        },
        {"nome": "n_veiculos", "unidade": "veículos", "valor": c.n_veiculos, "justificativa": "frota homogênea", "classe": hip},
        {
            "nome": "pedidos_por_veiculo",
            "unidade": "pedidos/veículo/dia",
            "valor": c.pedidos_por_veiculo,
            "justificativa": "relação demanda/frota do cenário",
            "classe": hip,
        },
        {"nome": "res_zona", "unidade": "H3", "valor": c.res_zona, "justificativa": "resolução das regiões de planejamento", "classe": hip},
        {
            "nome": "ancoras",
            "unidade": "lat,lon",
            "valor": ANCORAS,
            "justificativa": "pontos de referência do mapa onde se localizam as concentrações sintéticas (não são fluxos reais)",
            "classe": geo,
        },
        {
            "nome": "max_km_guloso",
            "unidade": "km por via",
            "valor": c.max_km_guloso,
            "justificativa": "salto máximo do reposicionamento (artigo: 3,0)",
            "classe": hip,
        },
    ]


def descrever(c: Cenario) -> dict:
    return asdict(c)
