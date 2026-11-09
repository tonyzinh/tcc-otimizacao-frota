"""Retentativa de página ES: repete sem pular/duplicar; erro de certificado e PIT expirado são explícitos."""

import ssl
import urllib.error

import pytest

import tcc_frota.data.reading.es as es


class _Resp:
    def __init__(self, texto):
        self.t = texto.encode()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self.t


def _leitor(monkeypatch, comportamentos):
    chamadas = []

    def fake(req, timeout=None, context=None):
        chamadas.append(req.data)
        c = comportamentos.pop(0)
        if isinstance(c, Exception):
            raise c
        return _Resp(c)

    monkeypatch.setattr(es.urllib.request, "urlopen", fake)
    monkeypatch.setattr(es.time, "sleep", lambda *_: None)
    r = es.ElasticReader(es.ElasticSettings("https://x", "u", "p", True))
    return r, chamadas


def test_queda_transitoria_repete_a_mesma_pagina_com_o_mesmo_corpo(monkeypatch):
    r, ch = _leitor(monkeypatch, [ssl.SSLError("record layer failure"), '{"hits": {"hits": []}}'])
    assert r._request("POST", "/_search", {"search_after": [5]}) == {"hits": {"hits": []}}
    assert len(ch) == 2 and ch[0] == ch[1]


def test_certificado_invalido_nao_e_repetido(monkeypatch):
    r, ch = _leitor(monkeypatch, [urllib.error.URLError(ssl.SSLCertVerificationError("bad cert")), "{}"])
    with pytest.raises(es.ElasticError, match="certificado"):
        r._request("POST", "/_search", {})
    assert len(ch) == 1


def test_pit_expirado_levanta_erro_proprio(monkeypatch):
    r, _ = _leitor(monkeypatch, [urllib.error.HTTPError("u", 404, "nf", {}, None)])
    with pytest.raises(es.ElasticPitExpirado):
        r._request("POST", "/_search", {})


def test_esgota_tentativas_e_levanta_conexao(monkeypatch):
    r, ch = _leitor(monkeypatch, [OSError("x")] * 4)
    with pytest.raises(ConnectionError):
        r._request("POST", "/_search", {})
    assert len(ch) == 4
