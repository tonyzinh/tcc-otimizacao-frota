from datetime import datetime

import pytest

from tcc_frota.data.extraction import saida
from tcc_frota.data.extraction.entidades import entidades_es, entidades_sql
from tcc_frota.data.extraction.executor import _linhas_es, _tratar_sql, dias
from tcc_frota.data.extraction.filtro import FiltroV1
from tcc_frota.data.privacy.pseudonimizacao import Segredo, chave_id_de
from tcc_frota.data.reading.es import ForbiddenRequestError, assert_allowed
from tcc_frota.data.reading.sql_guard import assert_read_only

SAL = Segredo("x" * 32, chave_id_de("x" * 32))


def test_todas_consultas_sql_sao_somente_leitura_e_tem_parametros_coerentes():
    f = FiltroV1()
    for nome, ent in entidades_sql(f).items():
        assert_read_only(ent.sql)
        assert len(ent.parametros(f, "2026-03-10", "2026-03-11")) == ent.sql.count("?"), nome


def test_filtro_exclui_prime_e_limita_regiao_e_servicos():
    ent = entidades_sql(FiltroV1())["solicitacao"]
    assert "CD_REGIAO = ?" in ent.sql and "IN (1,11,12,19)" in ent.sql and "'Prime'" in ent.sql


def test_tratar_sql_pseudonimiza_arredonda_e_rejeita_duplicada():
    ent = entidades_sql(FiltroV1())["solicitacao"]
    base = {
        "CD_SOLICITACAO": 1,
        "CD_PASSAGEIRO": 7,
        "CD_MOTORISTA": 9,
        "CD_VEICULO": 3,
        "TX_ORIGEM_LAT": "-20.123456",
        "DT_REGISTRO": datetime(2026, 3, 10, 8, 0),
        "DT_REGISTRO_ATUALIZACAO": None,
    }
    ok, rej = _tratar_sql(ent, [base, dict(base)], "2026-03-10", "2026-03-10", "2026-03-11", SAL)
    assert len(ok) == 1 and rej[0]["motivo"] == "chave_duplicada"
    assert ok[0]["tx_origem_lat"] == -20.123 and ok[0]["cd_passageiro"] != "7" and len(ok[0]["cd_passageiro"]) == 20
    assert ok[0]["known_at"] is None  # disponibilidade desconhecida: nunca inferida do evento


def test_es_posicao_descarta_servico_fora_e_pseudonimiza():
    ent = entidades_es()["posicao_ofertas"]
    item = {"codigo": 5, "placa": "ABC1D23", "codigoRegiao": 1, "codigosTiposServico": [1], "latitude": -20.0, "longitude": -40.0}
    fora = {**item, "codigo": 6, "codigosTiposServico": [3]}
    hit = {"_id": "d1", "_source": {"codigo": "d1", "codigoRegiao": 1, "dataHora": "2026-03-10T09:00:00-03:00", "ofertaList": [item, fora]}}
    ok, rej = _linhas_es(ent, [hit], FiltroV1(), SAL, datetime(2026, 3, 11))
    assert len(ok) == 1 and len(rej) == 1 and "ABC1D23" not in str(ok)


def test_lote_idempotente_e_checksum(tmp_path):
    cols = {"a": "int64", "b": "string"}
    pasta = tmp_path / "dt=2026-03-10"
    saida.gravar_lote(pasta, [{"a": 1, "b": "x"}], [], meta={"assinatura": "s1", "lote": "2026-03-10"}, colunas=cols)
    assert saida.lote_pronto(pasta, "s1") and not saida.lote_pronto(pasta, "s2")
    (pasta / "part-000.parquet").write_bytes(b"corrompido")
    assert not saida.lote_pronto(pasta, "s1")


def test_dias_inclusivo():
    assert list(dias("2026-03-30", "2026-04-01")) == ["2026-03-30", "2026-03-31", "2026-04-01"]


def test_es_pit_permitido_mas_escrita_continua_proibida():
    assert_allowed("POST", "/indexoferta/_pit")
    assert_allowed("POST", "/_search")
    assert_allowed("DELETE", "/_pit")
    for metodo, caminho in (("POST", "/indexoferta/_doc"), ("POST", "/indexoferta/_bulk"), ("DELETE", "/indexoferta"), ("PUT", "/_pit")):
        with pytest.raises(ForbiddenRequestError):
            assert_allowed(metodo, caminho)


def test_compromissos_externos_excluem_o_alvo_e_trazem_so_o_minimo_para_indisponibilidade():
    f = FiltroV1()
    ent = entidades_sql(f)["compromissos_externos"]
    assert "NOT (s.CD_REGIAO = ?" in ent.sql and "'Prime'" in ent.sql
    assert set(ent.colunas) >= {"cd_veiculo", "tx_categoria", "dt_inicio_realizada", "dt_fim_realizada"}
    assert not any(c in ent.colunas for c in ("cd_passageiro", "cd_motorista", "nu_valor", "tx_destino_lat"))
    assert set(ent.coords) == {"tx_origem_lat", "tx_origem_lng", "tx_destinoreal_lat", "tx_destinoreal_lng"} and ent.casas == 3
    assert ent.disponivel == "dt_registro" and ent.evento == "dt_inicio_realizada"
    assert len(ent.parametros(f, "2026-03-10", "2026-03-11")) == ent.sql.count("?")


def test_fronteira_do_dia_lote_exclui_registro_da_meia_noite_seguinte():
    ent = entidades_sql(FiltroV1())["solicitacao"]
    base = {"CD_SOLICITACAO": 1, "DT_REGISTRO": datetime(2026, 3, 11, 0, 0), "DT_REGISTRO_ATUALIZACAO": None}
    ok, rej = _tratar_sql(ent, [base], "2026-03-10", "2026-03-10", "2026-03-11", SAL)
    assert not ok and rej[0]["motivo"] == "fora_da_janela"
    ok2, _ = _tratar_sql(ent, [{**base, "DT_REGISTRO": datetime(2026, 3, 10, 23, 59, 59)}], "2026-03-10", "2026-03-10", "2026-03-11", SAL)
    assert len(ok2) == 1


def test_cobli_consulta_o_dia_local_com_relogio_em_utc():
    ent = entidades_sql(FiltroV1())["telemetria_cobli"]
    assert ent.deslocamento_janela_h == 3 and ent.janela_livre


def test_dia_do_registro_aceita_texto_utc_e_converte_para_dia_local():
    from types import SimpleNamespace

    from tcc_frota.data.extraction.executor import _dia_do_registro

    ent = SimpleNamespace(coluna_lote="start_address_datetime", deslocamento_janela_h=3)
    # 01:00 UTC de 11/03 = 22:00 local de 10/03
    assert _dia_do_registro(ent, {"START_ADDRESS_DATETIME": "2026-03-11 01:00:00"}) == "2026-03-10"
    assert _dia_do_registro(ent, {"START_ADDRESS_DATETIME": datetime(2026, 3, 11, 4, 0)}) == "2026-03-11"
