"""Pseudônimos estáveis entre execuções e fontes; guarda contra segredo ausente ou trocado."""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from tcc_frota.data.extraction.entidades import entidades_es, entidades_sql
from tcc_frota.data.extraction.executor import _linhas_es, _tratar_sql
from tcc_frota.data.extraction.filtro import FiltroV1
from tcc_frota.data.privacy import pseudonimizacao as pz

SEG_A = pz.Segredo("a" * 40, pz.chave_id_de("a" * 40))
SEG_B = pz.Segredo("b" * 40, pz.chave_id_de("b" * 40))


def test_mesma_entidade_gera_mesmo_pseudonimo_entre_tipos_e_formatos():
    assert pz.pseudonimo("motorista", 5, SEG_A) == pz.pseudonimo("motorista", "5", SEG_A) == pz.pseudonimo("motorista", "5.0", SEG_A)
    assert pz.pseudonimo("placa", "abc-1d23", SEG_A) == pz.pseudonimo("placa", " ABC1D23 ", SEG_A)
    assert pz.pseudonimo("placa", "ABC1D23", SEG_A) != pz.pseudonimo("veiculo_cod", "ABC1D23", SEG_A)
    assert pz.pseudonimo("motorista", None, SEG_A) is None and pz.pseudonimo("motorista", "  ", SEG_A) is None


def test_segredo_diferente_muda_pseudonimo_e_chave_id_nao_revela_segredo():
    assert pz.pseudonimo("motorista", 7, SEG_A) != pz.pseudonimo("motorista", 7, SEG_B)
    assert SEG_A.valor not in repr(SEG_A) and SEG_A.valor not in json.dumps(pz.descricao(SEG_A))


def test_coluna_sem_entidade_declarada_falha_explicitamente():
    with pytest.raises(pz.PseudonimizacaoError):
        pz.entidade_da_coluna("coluna_nova")


def test_vinculos_sobrevivem_a_processos_separados(tmp_path):
    """Dois processos distintos (como duas execuções de extração) produzem os mesmos pseudônimos."""
    codigo = "from tcc_frota.data.privacy import pseudonimizacao as p; s=p.carregar_segredo(); print(p.pseudonimo('motorista', 123, s), p.pseudonimo('placa', 'abc-1d23', s), s.chave_id)"
    env = {**os.environ, "TCC_PSEUDO_SECRET": "z" * 40, "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src")}
    saidas = [subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True, env=env, check=True).stdout for _ in range(2)]
    assert saidas[0] == saidas[1] and saidas[0].strip()


def test_ods_e_es_ligam_o_mesmo_motorista_e_es_e_cobli_ligam_a_mesma_placa():
    f = FiltroV1()
    ods = entidades_sql(f)["solicitacao"]
    base = {
        "CD_SOLICITACAO": 1,
        "CD_PASSAGEIRO": 1,
        "CD_MOTORISTA": 42,
        "CD_VEICULO": 9,
        "DT_REGISTRO": datetime(2026, 3, 10, 8),
        "DT_REGISTRO_ATUALIZACAO": None,
    }
    ok, _ = _tratar_sql(ods, [base], "2026-03-10", "2026-03-10", "2026-03-11", SEG_A)
    item = {"codigo": "42", "placa": "abc-1d23", "codigoRegiao": 1, "codigosTiposServico": [1]}
    hit = {"_id": "d", "_source": {"codigo": "d", "codigoRegiao": 1, "dataHora": "2026-03-10T09:00:00-03:00", "ofertaList": [item]}}
    es, _ = _linhas_es(entidades_es()["posicao_ofertas"], [hit], f, SEG_A, datetime(2026, 3, 11))
    assert ok[0]["cd_motorista"] == es[0]["cd_motorista"]
    cobli = entidades_sql(f)["telemetria_cobli"]
    brut = {"DEVICE_ID": "d1", "TYPE": "trips", "LICENSE_PLATE": "ABC1D23", "START_ADDRESS_DATETIME": datetime(2026, 3, 10, 8)}
    cb, _ = _tratar_sql(cobli, [brut], "2026-03-10", "2026-03-10", "2026-03-11", SEG_A)
    assert cb[0]["license_plate"] == es[0]["cd_veiculo_pseudo"]


def test_inicializar_nao_cria_segredo_quando_ha_dados_dependentes(tmp_path):
    raiz = tmp_path / "ext"
    (raiz / "ods" / "x" / "dt=1").mkdir(parents=True)
    (raiz / "ods" / "x" / "dt=1" / "manifest.json").write_text("{}")
    with pytest.raises(pz.SegredoAusente):
        pz.inicializar(raiz, destino=tmp_path / "seg" / "s")
    assert not (tmp_path / "seg" / "s").exists()


def test_migracao_do_legado_preserva_o_valor_e_backup_restaura(tmp_path):
    legado = tmp_path / ".pseudo_salt"
    legado.write_text("L" * 48 + "\n")
    novo = tmp_path / "seg" / "pseudo_secret"
    s = pz.inicializar(tmp_path / "vazio", a_partir_de=legado, destino=novo)
    assert s.chave_id == pz.chave_id_de("L" * 48)
    bak = pz.fazer_backup(s, tmp_path / "bak")
    novo.unlink()
    r = pz.restaurar(s.chave_id, destino=novo, backup_dir=bak.parent)
    assert r.chave_id == s.chave_id
    with pytest.raises(pz.PseudonimizacaoError):
        pz.inicializar(tmp_path / "vazio", a_partir_de=legado, destino=novo)  # não sobrescreve


def test_carregar_segredo_ausente_nao_gera_arquivo(tmp_path, monkeypatch):
    monkeypatch.delenv("TCC_PSEUDO_SECRET", raising=False)
    with pytest.raises(pz.SegredoAusente):
        pz.carregar_segredo(tmp_path / "nao_existe")
    assert not (tmp_path / "nao_existe").exists()


def test_guarda_da_campanha_bloqueia_segredo_ausente_trocado_e_lote_legado(tmp_path):
    raiz = tmp_path / "ext"
    pz.garantir_compatibilidade(raiz, SEG_A)  # primeira extração registra
    assert pz.garantir_compatibilidade(raiz, SEG_A)["chave_id"] == SEG_A.chave_id  # idempotente
    with pytest.raises(pz.SegredoIncompativel):
        pz.garantir_compatibilidade(raiz, SEG_B)
    with pytest.raises(pz.SegredoAusente):
        pz.garantir_compatibilidade(raiz, None)
    outra = tmp_path / "legado"
    (outra / "ods" / "e" / "dt=1").mkdir(parents=True)
    (outra / "ods" / "e" / "dt=1" / "manifest.json").write_text(json.dumps({"entidade": "e"}))
    with pytest.raises(pz.SegredoIncompativel):
        pz.garantir_compatibilidade(outra, SEG_A)


def test_lote_compativel_exige_mesma_versao():
    assert pz.lote_compativel({"pseudonimizacao": pz.descricao(SEG_A)}, SEG_A)
    assert not pz.lote_compativel({"pseudonimizacao": pz.descricao(SEG_A)}, SEG_B)
    assert not pz.lote_compativel({}, SEG_A)
