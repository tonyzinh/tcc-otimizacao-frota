"""Executor em lotes diários, idempotente e retomável, com manifesto por lote e manifesto da campanha."""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date, datetime, timedelta
from pathlib import Path

from tcc_frota.extracao.entidades import EntidadeEs, EntidadeSql, entidades_es, entidades_sql
from tcc_frota.extracao.filtro import FiltroV1
from tcc_frota.extracao.saida import RAIZ_PADRAO, agora_utc, caminho_lote, gravar_lote, hash_json, lote_pronto, versao_codigo
from tcc_frota.v2.rules import load_salt, pseudonym

FUSO_FONTE = "-03:00"  # ES traz o deslocamento no valor; SQL é sem deslocamento (RN024 pendente): ver manifesto


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


def _tratar_sql(ent: EntidadeSql, linhas: Iterable[dict], dia: str, ini: str, fim: str, salt: str):
    ingestao = datetime.fromisoformat(agora_utc().replace("Z", "+00:00"))
    ok, rej, vistos = [], [], set()
    for bruta in linhas:
        r = {k.lower(): v for k, v in bruta.items()}
        for c in ent.pseudo:
            r[c] = pseudonym(r.get(c), salt)
        for c in ent.coords:
            v = _num(r.get(c))
            r[c] = round(v, ent.casas) if v is not None else None
        for c, tipo in ent.colunas.items():
            if tipo == "float64" and c not in ent.coords:
                r[c] = _num(r.get(c))
        r["event_time"] = r.get(ent.evento)
        r["available_at"] = (r.get(ent.disponivel) if ent.disponivel else None) or r["event_time"]
        r["ingested_at"] = ingestao
        chave = tuple(r.get(k) for k in ent.chave)
        motivo = None
        if any(k is None for k in chave):
            motivo = "chave_nula"
        elif chave in vistos:
            motivo = "chave_duplicada"
        elif r["event_time"] is None:
            motivo = "event_time_nulo"
        elif not ent.snapshot and not (ini <= str(r["event_time"])[:10] < fim) and ent.nome not in {"status_solicitacao"}:
            motivo = "fora_da_janela"
        if motivo:
            rej.append({"motivo": motivo, **{k: str(r.get(k)) for k in ent.chave}})
            continue
        vistos.add(chave)
        ok.append({c: r.get(c) for c in ent.colunas})
    return ok, rej


def extrair_sql(entidade: str, inicio: str, fim: str, *, filtro: FiltroV1 | None = None, raiz: Path = RAIZ_PADRAO, forcar: bool = False) -> list[dict]:
    from tcc_frota.leitura import SqlServerReader

    f = filtro or FiltroV1()
    ent = entidades_sql(f)[entidade]
    salt = load_salt()
    resultados = []
    lotes = ["snapshot"] if ent.snapshot else list(dias(inicio, fim))
    with SqlServerReader.from_env(ent.banco, query_timeout_s=900) as leitor:
        for dia in lotes:
            ini = dia if not ent.snapshot else inicio
            fi = (date.fromisoformat(dia) + timedelta(days=1)).isoformat() if not ent.snapshot else fim
            assinatura = hash_json({"f": f.descricao(), "sql": ent.sql, "ini": ini, "fim": fi, "col": ent.colunas})
            pasta = caminho_lote(raiz, "ods", entidade, dia)
            if not forcar and lote_pronto(pasta, assinatura):
                resultados.append({"lote": dia, "estado": "ja_pronto"})
                continue
            bruto = leitor.iter_query(ent.sql, ent.parametros(f, ini, fi))
            ok, rej = _tratar_sql(ent, bruto, dia, ini, fi, salt)
            meta = {
                "fonte": ent.banco, "sistema": "SQL Server", "entidade": entidade, "lote": dia, "janela": [ini, fi],
                "filtro": f.descricao(), "assinatura": assinatura, "fuso": "sem deslocamento na fonte; coincide com -03:00 (America/Sao_Paulo) em 14 de 14 solicitações comparadas com o ES em 10/03/2026 (evidência amostral; RN024 segue pendente)",
                "limites": ent.limites, "chave": list(ent.chave), "somente_leitura": True,
            }
            man = gravar_lote(pasta, ok, rej, meta=meta, colunas=ent.colunas)
            resultados.append({"lote": dia, "estado": "gravado", "linhas": man["linhas"], "rejeitadas": man["rejeitadas"]})
    return resultados


def _iso(v):
    return v


def _linhas_es(ent: EntidadeEs, hits: Iterable[dict], filtro: FiltroV1, salt: str, ingestao: datetime):
    ok, rej = [], []
    for h in hits:
        s, hid = h["_source"], h["_id"]
        base = {"doc_codigo": str(s.get("codigo") or hid), "ingested_at": ingestao}
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
                ok.append({
                    **base, "event_time": s["dataHora"], "available_at": it.get("dataAtualizacao") or s["dataHora"],
                    "evento_dataHora": s["dataHora"], "cd_motorista": pseudonym(it["codigo"], salt),
                    "cd_veiculo_pseudo": pseudonym(it.get("placa"), salt), "status": it.get("status"),
                    "latitude": it.get("latitude"), "longitude": it.get("longitude"), "h3_index": it.get("h3Index"),
                    "accuracy": it.get("accuracy"), "passageiro_embarcado": it.get("passageiroEmbarcado"),
                    "data_posicao_gps": it.get("dataPosicaoGPS"), "data_atualizacao": it.get("dataAtualizacao"),
                    "codigo_proxima_solicitacao": it.get("codigoProximaSolicitacao"), "codigo_solicitacao": it.get("codigoSolicitacao"),
                    "distancia_restante": it.get("distanciaRestante"),
                    "tempo_segundos_viagem_restante": it.get("tempoSegundosViagemRestante"),
                    "servicos": ",".join(str(x) for x in servs), "codigo_regiao": it.get("codigoRegiao"),
                })
        elif ent.nome == "sumario_ofertas":
            ok.append({
                **base, "event_time": s["dataHora"], "available_at": s["dataHora"], "codigo_regiao": s.get("codigoRegiao"),
                "qtd_a_caminho": s.get("qtdACaminho"), "qtd_aproveitamento": s.get("qtdAproveitamento"),
                "qtd_com_passageiro": s.get("qtdComPassageiro"), "qtd_indisponivel": s.get("qtdIndisponivel"),
                "qtd_offline": s.get("qtdOffline"), "qtd_online": s.get("qtdOnline"), "qtd_selecionado": s.get("qtdSelecionado"),
            })
        else:  # reposicionamento_sugerido
            o = s.get("origem") or {}
            ok.append({
                **base, "event_time": s.get("dataRegistro"), "available_at": s.get("dataRegistro"), "regiao_id": s.get("regiaoId"),
                "user_id": pseudonym(s.get("userId"), salt), "h3": s.get("h3"), "mode": s.get("mode"),
                "id_motivo": s.get("idMotivo"), "descricao_motivo": s.get("descricaoMotivo"), "origem_lat": o.get("lat"),
                "origem_lng": o.get("lng"), "codigo_solicitacao": s.get("codigoSolicitacao"),
                "reposicionamento_desligado": s.get("reposicionamentoDesligado"), "distancia": s.get("distancia"),
            })
    return ok, rej


def extrair_es(entidade: str, inicio: str, fim: str, *, filtro: FiltroV1 | None = None, raiz: Path = RAIZ_PADRAO, forcar: bool = False) -> list[dict]:
    from tcc_frota.leitura import ElasticReader

    f = filtro or FiltroV1()
    ent = entidades_es()[entidade]
    salt = load_salt()
    leitor = ElasticReader.from_env(timeout_s=180)
    resultados = []
    for dia in dias(inicio, fim):
        proximo = (date.fromisoformat(dia) + timedelta(days=1)).isoformat()
        ini_iso, fim_iso = f"{dia}T00:00:00{FUSO_FONTE}", f"{proximo}T00:00:00{FUSO_FONTE}"
        indice = ent.indice.format(aaaamm=dia[:4] + "-" + dia[5:7])
        regiao_campo = {"posicao_ofertas": "codigoRegiao", "sumario_ofertas": "codigoRegiao", "reposicionamento_sugerido": "regiaoId"}[entidade]
        consulta = {"bool": {"filter": [{"term": {regiao_campo: f.regiao}}, {"range": {ent.campo_tempo: {"gte": ini_iso, "lt": fim_iso}}}]}}
        assinatura = hash_json({"f": f.descricao(), "idx": indice, "q": consulta, "col": ent.colunas})
        pasta = caminho_lote(raiz, "es", entidade, dia)
        if not forcar and lote_pronto(pasta, assinatura):
            resultados.append({"lote": dia, "estado": "ja_pronto"})
            continue
        ingestao = datetime.fromisoformat(agora_utc().replace("Z", "+00:00"))
        hits = leitor.iter_search_pit(indice, consulta, sort_field=ent.campo_tempo)
        ok, rej = _linhas_es(ent, hits, f, salt, ingestao)
        meta = {
            "fonte": "Elasticsearch", "sistema": "Elasticsearch", "entidade": entidade, "lote": dia, "janela": [ini_iso, fim_iso],
            "indice": indice, "filtro": f.descricao(), "assinatura": assinatura, "fuso": f"valores com deslocamento explícito (-03:00 observado); dia = {FUSO_FONTE}",
            "paginacao": "PIT + search_after", "limites": ent.limites, "chave": list(ent.chave), "somente_leitura": True,
        }
        man = gravar_lote(pasta, ok, rej, meta=meta, colunas=ent.colunas)
        resultados.append({"lote": dia, "estado": "gravado", "linhas": man["linhas"], "rejeitadas": man["rejeitadas"]})
    return resultados


def gravar_campanha(raiz: Path, comando: dict, resultados: dict) -> Path:
    raiz.mkdir(parents=True, exist_ok=True)
    caminho = raiz / "campanha.json"
    antigo = json.loads(caminho.read_text(encoding="utf-8")) if caminho.is_file() else {"execucoes": []}
    antigo["execucoes"].append({"em_utc": agora_utc(), "codigo": versao_codigo(), "comando": comando, "resultados": resultados})
    caminho.write_text(json.dumps(antigo, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return caminho
