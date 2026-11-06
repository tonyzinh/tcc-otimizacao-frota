"""Cliente Elasticsearch somente leitura, sem dependências externas (urllib).

Só passam as rotas de leitura da lista de permissões; qualquer outra combinação de método e
caminho (escrita, `_update`, `_delete_by_query`, `_bulk`, criação/remoção de índice) é recusada
antes de abrir a conexão.
"""

from __future__ import annotations

import base64
import json
import re
import ssl
import urllib.error
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote, urlencode, urlsplit

from tcc_frota.ingestion.files import authorize
from tcc_frota.leitura.env import ConfigError, load_env, require

_INDEX = r"[A-Za-z0-9_.,*\-]+"
# (método, caminho). Apenas leitura; DELETE só encerra o contexto de scroll.
_ROUTES = (
    ("GET", r"/"),
    ("GET", r"/_cluster/health"),
    ("GET", r"/_cat/indices(?:/" + _INDEX + r")?"),
    ("GET", r"/" + _INDEX + r"/_mapping"),
    ("GET", r"/" + _INDEX + r"/_count"),
    ("POST", r"/" + _INDEX + r"/_count"),
    ("GET", r"/" + _INDEX + r"/_search"),
    ("POST", r"/" + _INDEX + r"/_search"),
    ("POST", r"/" + _INDEX + r"/_pit"),  # abre ponto no tempo (PIT): contexto de leitura, não altera dados
    ("DELETE", r"/_pit"),
    ("POST", r"/_search"),  # busca com PIT (o índice vai no corpo)
    ("POST", r"/_search/scroll"),
    ("DELETE", r"/_search/scroll"),
)
_ALLOWED = tuple((method, re.compile(pattern)) for method, pattern in _ROUTES)


class ForbiddenRequestError(PermissionError):
    """Requisição fora da lista de rotas de leitura."""


class ElasticError(RuntimeError):
    pass


def assert_allowed(method: str, path: str) -> None:
    clean = path.split("?", 1)[0]
    if not any(m == method.upper() and p.fullmatch(clean) for m, p in _ALLOWED):
        raise ForbiddenRequestError(f"rota não permitida em modo somente leitura: {method.upper()} {clean}")


@dataclass(frozen=True)
class ElasticSettings:
    endpoint: str
    user: str
    password: str = field(repr=False)
    verify_tls: bool = True

    def __post_init__(self) -> None:
        parts = urlsplit(self.endpoint)
        if parts.scheme not in {"https", "http"} or not parts.hostname:
            raise ConfigError("ENDPOINT deve ser uma URL http(s) completa")

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> ElasticSettings:
        values = env if env is not None else load_env()
        require(values, "ENDPOINT", "ES_USER", "ES_PASSWORD")
        return cls(
            endpoint=values["ENDPOINT"].rstrip("/"),
            user=values["ES_USER"],
            password=values["ES_PASSWORD"],
            verify_tls=values.get("ES_VERIFY_TLS", "true").lower() not in {"0", "false", "no"},
        )


class ElasticReader:
    def __init__(self, settings: ElasticSettings, *, timeout_s: float = 60.0):
        self.settings = settings
        self.timeout_s = timeout_s
        token = base64.b64encode(f"{settings.user}:{settings.password}".encode()).decode()
        self._headers = {"Authorization": f"Basic {token}", "Accept": "application/json", "User-Agent": "tcc-frota-leitura"}
        self._ctx = None if settings.verify_tls else ssl._create_unverified_context()  # opt-in explícito via ES_VERIFY_TLS

    @classmethod
    def from_env(cls, **kwargs: Any) -> ElasticReader:
        return cls(ElasticSettings.from_env(), **kwargs)

    def _request(self, method: str, path: str, body: dict | None = None, params: dict[str, Any] | None = None) -> Any:
        assert_allowed(method, path)
        url = self.settings.endpoint + quote(path, safe="/_,*.-") + (f"?{urlencode(params)}" if params else "")
        data = json.dumps(body).encode() if body is not None else None
        headers = dict(self._headers)
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s, context=self._ctx) as resp:
                payload = resp.read()
        except urllib.error.HTTPError as exc:
            raise ElasticError(f"Elasticsearch respondeu HTTP {exc.code} em {method.upper()} {path.split('?')[0]}") from None
        except urllib.error.URLError as exc:
            raise ConnectionError(f"falha ao conectar ao Elasticsearch ({type(exc.reason).__name__})") from None
        return json.loads(payload) if payload else {}

    def ping(self) -> dict[str, Any]:
        """Verifica conexão e credenciais; devolve só versão e estado do cluster (sem dados de negócio)."""
        info = self._request("GET", "/")
        health = self._request("GET", "/_cluster/health")
        return {"ok": True, "version": info.get("version", {}).get("number"), "status": health.get("status")}

    def indices(self) -> list[dict[str, Any]]:
        """Nomes, contagem de documentos e tamanho dos índices (metadados; sem portão de dados reais)."""
        return self._request("GET", "/_cat/indices", params={"format": "json", "h": "index,docs.count,store.size"})

    def mapping(self, index: str) -> dict[str, Any]:
        """Esquema dos campos do índice (metadados; sem portão de dados reais)."""
        return self._request("GET", f"/{index}/_mapping")

    def count(self, index: str, query: dict | None = None) -> int:
        authorize("real", "local")
        return int(self._request("POST", f"/{index}/_count", {"query": query or {"match_all": {}}})["count"])

    def search(self, index: str, query: dict | None = None, *, size: int = 100, source: list[str] | None = None, sort: list | None = None) -> list[dict]:
        authorize("real", "local")
        body: dict[str, Any] = {"query": query or {"match_all": {}}, "size": size}
        if source is not None:
            body["_source"] = source
        if sort is not None:
            body["sort"] = sort
        return self._request("POST", f"/{index}/_search", body)["hits"]["hits"]

    def iter_search(
        self, index: str, query: dict | None = None, *, source: list[str] | None = None, batch_size: int = 1000, scroll: str = "2m"
    ) -> Iterator[dict]:
        """Percorre todos os documentos que casam com `query`, em lotes (scroll), limpando o contexto ao fim."""
        authorize("real", "local")
        body: dict[str, Any] = {"query": query or {"match_all": {}}, "size": batch_size, "sort": ["_doc"]}
        if source is not None:
            body["_source"] = source
        page = self._request("POST", f"/{index}/_search", body, params={"scroll": scroll})
        scroll_id = page.get("_scroll_id")
        try:
            while True:
                hits = page["hits"]["hits"]
                if not hits:
                    return
                yield from hits
                page = self._request("POST", "/_search/scroll", {"scroll": scroll, "scroll_id": scroll_id})
                scroll_id = page.get("_scroll_id", scroll_id)
        finally:
            if scroll_id:
                try:
                    self._request("DELETE", "/_search/scroll", {"scroll_id": scroll_id})
                except (ElasticError, ConnectionError):
                    pass

    def iter_search_pit(
        self,
        index: str,
        query: dict | None = None,
        *,
        sort_field: str,
        source: list[str] | None = None,
        batch_size: int = 2000,
        keep_alive: str = "2m",
    ) -> Iterator[dict]:
        """Percorre os resultados com PIT + `search_after` (sem `from/size` profundo), ordenados por `sort_field`."""
        authorize("real", "local")
        pit_id = self._request("POST", f"/{index}/_pit", params={"keep_alive": keep_alive})["id"]
        search_after: list | None = None
        try:
            while True:
                body: dict[str, Any] = {
                    "query": query or {"match_all": {}},
                    "size": batch_size,
                    "pit": {"id": pit_id, "keep_alive": keep_alive},
                    "sort": [{sort_field: "asc"}, {"_shard_doc": "asc"}],
                    "track_total_hits": False,
                }
                if source is not None:
                    body["_source"] = source
                if search_after is not None:
                    body["search_after"] = search_after
                page = self._request("POST", "/_search", body)
                pit_id = page.get("pit_id", pit_id)
                hits = page["hits"]["hits"]
                if not hits:
                    return
                yield from hits
                search_after = hits[-1]["sort"]
        finally:
            try:
                self._request("DELETE", "/_pit", {"id": pit_id})
            except (ElasticError, ConnectionError):
                pass
