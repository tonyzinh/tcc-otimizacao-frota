"""Executor em lotes diários, idempotente e retomável, com manifesto por lote e manifesto da campanha."""

from __future__ import annotations

import json
import time
from collections.abc import Iterable
from datetime import date, datetime, timedelta
from pathlib import Path

from tcc_frota.data.extraction.entidades import EntidadeEs, EntidadeSql, entidades_es, entidades_sql
from tcc_frota.data.extraction.filtro import FiltroV1
from tcc_frota.data.extraction.saida import RAIZ_PADRAO, agora_utc, caminho_lote, gravar_lote, hash_json, lote_pronto, versao_codigo
from tcc_frota.data.privacy import pseudonimizacao as pz
from tcc_frota.data.privacy.pseudonimizacao import Segredo

FUSO_FONTE = "-03:00"  # ES traz o deslocamento no valor; SQL é sem deslocamento (RN024 pendente): ver manifesto


def _log_lote(raiz: Path, **registro) -> None:
    """Uma linha por lote em LOG_LOTES.jsonl (duração, linhas, falhas): evidência para estimar o tempo restante. Sem dados de negócio."""
    raiz.mkdir(parents=True, exist_ok=True)
    registro = {"em_utc": agora_utc(), **registro}
    with (raiz / "LOG_LOTES.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False, default=str) + "\n")


def dias(inicio: str, fim: str) -> Iterable[str]:
    d, f = date.fromisoformat(inicio), date.fromisoformat(fim)
    while d <= f:
        yield d.isoformat()
        d += timedelta(days=1)


def _num(v):
    if v in (None, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _tratar_sql(ent: EntidadeSql, linhas: Iterable[dict], dia: str, ini: str, fim: str, segredo: Segredo):
    ingestao = datetime.fromisoformat(agora_utc().replace("Z", "+00:00"))
    ok, rej, vistos = [], [], set()
    for bruta in linhas:
        r = {k.lower(): v for k, v in bruta.items()}
        for c in ent.pseudo:
            r[c] = pz.pseudonimo(pz.entidade_da_coluna(c), r.get(c), segredo)
        for c in ent.coords:
            v = _num(r.get(c))
            r[c] = round(v, ent.casas) if v is not None else None
        for c, tipo in ent.colunas.items():
            if tipo == "float64" and c not in ent.coords:
                r[c] = _num(r.get(c))
        r["event_time"] = r.get(ent.evento)
        r["known_at"] = None  # sem evidência do horário de disponibilidade ao sistema: desconhecido, nunca inferido
        r["extraido_em"] = ingestao
        chave = tuple(r.get(k) for k in ent.chave)
        motivo = None
        if any(k is None for k in chave):
            motivo = "chave_nula"
        elif chave in vistos:
            motivo = "chave_duplicada"
        elif r["event_time"] is None:
            motivo = "event_time_nulo"
        elif (
            not ent.snapshot
            and not ent.janela_livre
            and not (ini <= str(r["event_time"])[:10] < fim)
            and ent.nome not in {"status_solicitacao"}
        ):
            motivo = "fora_da_janela"
        if motivo:
            rej.append({"motivo": motivo, **{k: str(r.get(k)) for k in ent.chave}})
            continue
        vistos.add(chave)
        ok.append({c: r.get(c) for c in ent.colunas})
    return ok, rej


def _dia_do_registro(ent: EntidadeSql, linha: dict) -> str | None:
    v = {k.lower(): x for k, x in linha.items()}.get(ent.coluna_lote or "")
    if v is None:
        return None
    if isinstance(v, str):  # colunas de texto (ex.: Cobli) chegam como string ISO naive
        v = datetime.fromisoformat(v.replace("T", " ").split(".")[0])
    return (v - timedelta(hours=ent.deslocamento_janela_h)).date().isoformat()


def _blocos(dias_pendentes: list[str], k: int) -> list[list[str]]:
    """Agrupa dias pendentes CONSECUTIVOS em blocos de até k dias (uma consulta por bloco)."""
    blocos: list[list[str]] = []
    for d in dias_pendentes:
        if blocos and len(blocos[-1]) < k and date.fromisoformat(d) - date.fromisoformat(blocos[-1][-1]) == timedelta(days=1):
            blocos[-1].append(d)
        else:
            blocos.append([d])
    return blocos


def extrair_sql(
    entidade: str,
    inicio: str,
    fim: str,
    *,
    filtro: FiltroV1 | None = None,
    raiz: Path = RAIZ_PADRAO,
    forcar: bool = False,
    bloco_dias: int = 1,
) -> list[dict]:
    """Extrai por dia. `bloco_dias` > 1 lê vários dias numa só consulta e reparte por dia local, só nas entidades com `coluna_lote`.

    A repartição não muda a semântica: cada lote diário tem a mesma janela, assinatura e filtro do modo diário.
    """
    from tcc_frota.data.reading import SqlServerReader

    f = filtro or FiltroV1()
    ent = entidades_sql(f)[entidade]
    segredo = pz.carregar_segredo()
    pz.garantir_compatibilidade(raiz, segredo)
    resultados: list[dict] = []
    lotes = ["snapshot"] if ent.snapshot else list(dias(inicio, fim))
    chunk = bloco_dias if (ent.coluna_lote and not ent.snapshot) else 1

    def janela(dia: str) -> tuple[str, str]:
        return (dia, (date.fromisoformat(dia) + timedelta(days=1)).isoformat()) if not ent.snapshot else (inicio, fim)

    def assina(ini: str, fi: str) -> str:
        return hash_json(
            {
                "f": f.descricao(),
                "sql": ent.sql,
                "ini": ini,
                "fim": fi,
                "col": ent.colunas,
                "dh": ent.deslocamento_janela_h,
                "pz": pz.descricao(segredo),
            }
        )

    def fonte_h(ts: str) -> str:
        if not ent.deslocamento_janela_h or ent.snapshot:
            return ts
        return (datetime.fromisoformat(ts) + timedelta(hours=ent.deslocamento_janela_h)).strftime("%Y-%m-%d %H:%M:%S")

    def gravar(dia: str, bruto, q_ini: str, q_fim: str, leitor_chamadas: int) -> None:
        ini, fi = janela(dia)
        ok, rej = _tratar_sql(ent, bruto, dia, ini, fi, segredo)
        meta = {
            "fonte": ent.banco,
            "sistema": "SQL Server",
            "entidade": entidade,
            "lote": dia,
            "janela": [ini, fi],
            "janela_consulta_na_hora_da_fonte": [q_ini, q_fim],
            "consulta_em_bloco": leitor_chamadas > 1,
            "filtro": f.descricao(),
            "assinatura": assina(ini, fi),
            "fuso": "sem deslocamento na fonte; coincide com -03:00 (America/Sao_Paulo): ES-ODS em 4 dias (07, 10, 13, 17/03/2026), mediana de 1 min; RN024 segue pendente",
            "limites": ent.limites,
            "chave": list(ent.chave),
            "somente_leitura": True,
            "pseudonimizacao": pz.descricao(segredo),
        }
        man = gravar_lote(caminho_lote(raiz, "ods", entidade, dia), ok, rej, meta=meta, colunas=ent.colunas)
        resultados.append({"lote": dia, "estado": "gravado", "linhas": man["linhas"], "rejeitadas": man["rejeitadas"]})

    with SqlServerReader.from_env(ent.banco, query_timeout_s=1800) as leitor:
        pendentes = []
        for dia in lotes:
            ini, fi = janela(dia)
            if not forcar and lote_pronto(caminho_lote(raiz, "ods", entidade, dia), assina(ini, fi)):
                resultados.append({"lote": dia, "estado": "ja_pronto"})
            else:
                pendentes.append(dia)
        for bloco in _blocos(pendentes, chunk) if chunk > 1 else [[d] for d in pendentes]:
            q_ini = fonte_h(janela(bloco[0])[0])
            q_fim = fonte_h(janela(bloco[-1])[1])
            t0 = time.monotonic()
            try:
                bruto = list(leitor.iter_query(ent.sql, ent.parametros(f, q_ini, q_fim)))
            except Exception as exc:
                _log_lote(
                    raiz,
                    fonte="ods",
                    entidade=entidade,
                    bloco=[bloco[0], bloco[-1]],
                    estado="falha",
                    erro=type(exc).__name__,
                    duracao_s=round(time.monotonic() - t0, 1),
                )
                raise
            dur = round(time.monotonic() - t0, 1)
            if len(bloco) == 1:
                gravar(bloco[0], bruto, q_ini, q_fim, 1)
                _log_lote(
                    raiz,
                    fonte="ods",
                    entidade=entidade,
                    lote=bloco[0],
                    tamanho_bloco=1,
                    duracao_leitura_s=dur,
                    linhas_brutas=len(bruto),
                    **{k: resultados[-1].get(k) for k in ("linhas", "rejeitadas")},
                )
                continue
            por_dia: dict[str, list] = {d: [] for d in bloco}
            sem_dia = 0
            for linha in bruto:
                d = _dia_do_registro(ent, linha)
                if d in por_dia:
                    por_dia[d].append(linha)
                else:
                    sem_dia += 1
            if sem_dia:
                resultados.append({"bloco": [bloco[0], bloco[-1]], "estado": "aviso", "linhas_fora_do_bloco_ou_sem_dia": sem_dia})
            for d in bloco:
                gravar(d, por_dia[d], q_ini, q_fim, len(bloco))
                _log_lote(
                    raiz,
                    fonte="ods",
                    entidade=entidade,
                    lote=d,
                    tamanho_bloco=len(bloco),
                    duracao_leitura_s=dur,
                    linhas_brutas_bloco=len(bruto),
                    **{k: resultados[-1].get(k) for k in ("linhas", "rejeitadas")},
                )
    return resultados


def _iso(v):
    return v


def _linhas_es(ent: EntidadeEs, hits: Iterable[dict], filtro: FiltroV1, segredo: Segredo, ingestao: datetime):
    ok, rej = [], []
    for h in hits:
        s, hid = h["_source"], h["_id"]
        base = {"doc_codigo": str(s.get("codigo") or hid), "extraido_em": ingestao, "known_at": None}
        if ent.nome == "posicao_ofertas":
            if s.get("codigoRegiao") != filtro.regiao:
                rej.append({"motivo": "regiao_fora", "doc": hid})
                continue
            for it in s.get("ofertaList") or []:
                servs = it.get("codigosTiposServico") or []
                if it.get("codigoRegiao") != filtro.regiao or not set(servs) & set(filtro.servicos):
                    rej.append({"motivo": "servico_fora_ou_sem_servico", "doc": hid})
                    continue
                if it.get("codigo") is None:
                    rej.append({"motivo": "chave_nula", "doc": hid})
                    continue
                ok.append(
                    {
                        **base,
                        "event_time": s["dataHora"],
                        "cd_motorista": pz.pseudonimo("motorista", it["codigo"], segredo),
                        "cd_veiculo_pseudo": pz.pseudonimo("placa", it.get("placa"), segredo),
                        "status": it.get("status"),
                        "latitude": it.get("latitude"),
                        "longitude": it.get("longitude"),
                        "h3_index": it.get("h3Index"),
                        "accuracy": it.get("accuracy"),
                        "passageiro_embarcado": it.get("passageiroEmbarcado"),
                        "gps_observado_em": it.get("dataPosicaoGPS"),
                        "ultima_atualizacao_em": it.get("dataAtualizacao"),
                        "codigo_proxima_solicitacao": it.get("codigoProximaSolicitacao"),
                        "codigo_solicitacao": it.get("codigoSolicitacao"),
                        "distancia_restante": it.get("distanciaRestante"),
                        "tempo_segundos_viagem_restante": it.get("tempoSegundosViagemRestante"),
                        "servicos": ",".join(str(x) for x in servs),
                        "codigo_regiao": it.get("codigoRegiao"),
                    }
                )
        elif ent.nome == "sumario_ofertas":
            ok.append(
                {
                    **base,
                    "event_time": s["dataHora"],
                    "codigo_regiao": s.get("codigoRegiao"),
                    "qtd_a_caminho": s.get("qtdACaminho"),
                    "qtd_aproveitamento": s.get("qtdAproveitamento"),
                    "qtd_com_passageiro": s.get("qtdComPassageiro"),
                    "qtd_indisponivel": s.get("qtdIndisponivel"),
                    "qtd_offline": s.get("qtdOffline"),
                    "qtd_online": s.get("qtdOnline"),
                    "qtd_selecionado": s.get("qtdSelecionado"),
                }
            )
        else:  # reposicionamento_sugerido
            o = s.get("origem") or {}
            ok.append(
                {
                    **base,
                    "event_time": s.get("dataRegistro"),
                    "regiao_id": s.get("regiaoId"),
                    "user_id": pz.pseudonimo("motorista", s.get("userId"), segredo),
                    "h3": s.get("h3"),
                    "mode": s.get("mode"),
                    "id_motivo": s.get("idMotivo"),
                    "descricao_motivo": s.get("descricaoMotivo"),
                    "origem_lat": o.get("lat"),
                    "origem_lng": o.get("lng"),
                    "codigo_solicitacao": s.get("codigoSolicitacao"),
                    "reposicionamento_desligado": s.get("reposicionamentoDesligado"),
                    "distancia": s.get("distancia"),
                }
            )
    return ok, rej


def extrair_es(
    entidade: str, inicio: str, fim: str, *, filtro: FiltroV1 | None = None, raiz: Path = RAIZ_PADRAO, forcar: bool = False
) -> list[dict]:
    from tcc_frota.data.reading import ElasticReader

    f = filtro or FiltroV1()
    ent = entidades_es()[entidade]
    segredo = pz.carregar_segredo()
    pz.garantir_compatibilidade(raiz, segredo)
    leitor = ElasticReader.from_env(timeout_s=180)
    resultados = []
    for dia in dias(inicio, fim):
        proximo = (date.fromisoformat(dia) + timedelta(days=1)).isoformat()
        ini_iso, fim_iso = f"{dia}T00:00:00{FUSO_FONTE}", f"{proximo}T00:00:00{FUSO_FONTE}"
        indice = ent.indice.format(aaaamm=dia[:4] + "-" + dia[5:7])
        regiao_campo = {"posicao_ofertas": "codigoRegiao", "sumario_ofertas": "codigoRegiao", "reposicionamento_sugerido": "regiaoId"}[
            entidade
        ]
        consulta = {"bool": {"filter": [{"term": {regiao_campo: f.regiao}}, {"range": {ent.campo_tempo: {"gte": ini_iso, "lt": fim_iso}}}]}}
        assinatura = hash_json({"f": f.descricao(), "idx": indice, "q": consulta, "col": ent.colunas, "pz": pz.descricao(segredo)})
        pasta = caminho_lote(raiz, "es", entidade, dia)
        if not forcar and lote_pronto(pasta, assinatura):
            resultados.append({"lote": dia, "estado": "ja_pronto"})
            continue
        ingestao = datetime.fromisoformat(agora_utc().replace("Z", "+00:00"))
        t0 = time.monotonic()
        hits = leitor.iter_search_pit(indice, consulta, sort_field=ent.campo_tempo)
        try:
            ok, rej = _linhas_es(ent, hits, f, segredo, ingestao)
        except Exception as exc:
            _log_lote(
                raiz,
                fonte="es",
                entidade=entidade,
                lote=dia,
                estado="falha",
                erro=type(exc).__name__,
                duracao_s=round(time.monotonic() - t0, 1),
            )
            raise
        dur_es = round(time.monotonic() - t0, 1)
        meta = {
            "fonte": "Elasticsearch",
            "sistema": "Elasticsearch",
            "entidade": entidade,
            "lote": dia,
            "janela": [ini_iso, fim_iso],
            "indice": indice,
            "filtro": f.descricao(),
            "assinatura": assinatura,
            "fuso": f"valores com deslocamento explícito (-03:00 observado); dia = {FUSO_FONTE}",
            "paginacao": "PIT + search_after",
            "limites": ent.limites,
            "chave": list(ent.chave),
            "somente_leitura": True,
            "pseudonimizacao": pz.descricao(segredo),
        }
        man = gravar_lote(pasta, ok, rej, meta=meta, colunas=ent.colunas)
        resultados.append({"lote": dia, "estado": "gravado", "linhas": man["linhas"], "rejeitadas": man["rejeitadas"]})
        _log_lote(
            raiz, fonte="es", entidade=entidade, lote=dia, duracao_leitura_s=dur_es, linhas=man["linhas"], rejeitadas=man["rejeitadas"]
        )
    return resultados


def gravar_campanha(raiz: Path, comando: dict, resultados: dict) -> Path:
    raiz.mkdir(parents=True, exist_ok=True)
    caminho = raiz / "campanha.json"
    antigo = json.loads(caminho.read_text(encoding="utf-8")) if caminho.is_file() else {"execucoes": []}
    antigo["execucoes"].append({"em_utc": agora_utc(), "codigo": versao_codigo(), "comando": comando, "resultados": resultados})
    caminho.write_text(json.dumps(antigo, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return caminho
