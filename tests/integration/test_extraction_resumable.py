"""Retomada, idempotência e guarda de pseudonimização na extração (leitor SQL substituído por um falso)."""

import json
from datetime import datetime

import pytest

import tcc_frota.data.reading as leitura
from tcc_frota.data.extraction.runner import extrair_sql
from tcc_frota.data.privacy import pseudonymization as pz


class _Leitor:
    chamadas = 0

    @classmethod
    def from_env(cls, *_a, **_k):
        return cls()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def iter_query(self, _sql, _params=()):
        type(self).chamadas += 1
        yield {
            "CD_SOLICITACAO": 1,
            "CD_MOTORISTA": 42,
            "CD_VEICULO": 9,
            "DT_REGISTRO": datetime(2026, 3, 10, 8),
            "DT_REGISTRO_ATUALIZACAO": None,
        }


@pytest.fixture
def ambiente(monkeypatch):
    monkeypatch.setattr(leitura, "SqlServerReader", _Leitor)
    monkeypatch.setenv("TCC_PSEUDO_SECRET", "k" * 40)
    _Leitor.chamadas = 0


def test_segunda_execucao_pula_o_lote_pronto_e_manifesto_traz_versao_sem_segredo(ambiente, tmp_path):
    r1 = extrair_sql("solicitacao", "2026-03-10", "2026-03-10", raiz=tmp_path)
    r2 = extrair_sql("solicitacao", "2026-03-10", "2026-03-10", raiz=tmp_path)
    assert r1[0]["estado"] == "gravado" and r2[0]["estado"] == "ja_pronto" and _Leitor.chamadas == 1
    texto = (tmp_path / "ods/solicitacao/dt=2026-03-10/manifest.json").read_text(encoding="utf-8")
    man = json.loads(texto)
    assert man["pseudonimizacao"]["chave_id"] == pz.chave_id_de("k" * 40) and "k" * 40 not in texto


def test_segredo_trocado_impede_continuar_a_campanha(ambiente, tmp_path, monkeypatch):
    extrair_sql("solicitacao", "2026-03-10", "2026-03-10", raiz=tmp_path)
    monkeypatch.setenv("TCC_PSEUDO_SECRET", "j" * 40)
    with pytest.raises(pz.SegredoIncompativel):
        extrair_sql("solicitacao", "2026-03-11", "2026-03-11", raiz=tmp_path)
    assert not (tmp_path / "ods/solicitacao/dt=2026-03-11").exists()


def test_segredo_ausente_impede_continuar_e_nao_cria_segredo(ambiente, tmp_path, monkeypatch):
    extrair_sql("solicitacao", "2026-03-10", "2026-03-10", raiz=tmp_path)
    monkeypatch.delenv("TCC_PSEUDO_SECRET")
    monkeypatch.setenv("TCC_SEGREDOS_DIR", str(tmp_path / "vazio"))
    with pytest.raises(pz.SegredoAusente):
        extrair_sql("solicitacao", "2026-03-11", "2026-03-11", raiz=tmp_path)
    assert not (tmp_path / "vazio").exists()


def test_lote_corrompido_e_regravado_na_retomada(ambiente, tmp_path):
    extrair_sql("solicitacao", "2026-03-10", "2026-03-10", raiz=tmp_path)
    (tmp_path / "ods/solicitacao/dt=2026-03-10/part-000.parquet").write_bytes(b"x")
    assert extrair_sql("solicitacao", "2026-03-10", "2026-03-10", raiz=tmp_path)[0]["estado"] == "gravado"


class _LeitorBloco(_Leitor):
    def iter_query(self, _sql, params=()):
        type(self).chamadas += 1
        for dia, cd in ((10, 1), (11, 2), (12, 3)):
            yield {
                "CD_LOG_STATUS_SOLICITACAO": cd,
                "CD_SOLICITACAO": cd,
                "DT_REGISTRO": datetime(2026, 3, dia, 9),
                "TX_STATUS": "x",
                "CD_MOTORISTA": 42,
                "LEGADO": 0,
                "DT_SOLICITACAO": datetime(2026, 3, dia, 8),
            }


def test_leitura_em_bloco_gera_lotes_diarios_com_uma_consulta_e_e_idempotente(monkeypatch, tmp_path):
    monkeypatch.setattr(leitura, "SqlServerReader", _LeitorBloco)
    monkeypatch.setenv("TCC_PSEUDO_SECRET", "k" * 40)
    _LeitorBloco.chamadas = 0
    r1 = extrair_sql("status_solicitacao", "2026-03-10", "2026-03-12", raiz=tmp_path, bloco_dias=3)
    assert _LeitorBloco.chamadas == 1
    for dia in ("10", "11", "12"):
        man = json.loads((tmp_path / f"ods/status_solicitacao/dt=2026-03-{dia}/manifest.json").read_text(encoding="utf-8"))
        assert man["linhas"] == 1
    assert [x["estado"] for x in r1 if "lote" in x] == ["gravado"] * 3
    r2 = extrair_sql("status_solicitacao", "2026-03-10", "2026-03-12", raiz=tmp_path, bloco_dias=3)
    assert _LeitorBloco.chamadas == 1 and all(x["estado"] == "ja_pronto" for x in r2)
