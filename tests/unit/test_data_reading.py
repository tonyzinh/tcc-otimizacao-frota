"""Conexões somente leitura: configuração, lista de permissões de SQL e de rotas do Elasticsearch (sem rede)."""

import pytest

from tcc_frota.data.reading.env import ConfigError, parse_env
from tcc_frota.data.reading.es import ElasticSettings, ForbiddenRequestError, assert_allowed
from tcc_frota.data.reading.sql_guard import UnsafeQueryError, assert_read_only
from tcc_frota.data.reading.sqlserver import SqlServerReader, SqlServerSettings, build_connection_string


def test_parse_env_ignora_comentarios_traco_duplo_e_remove_aspas():
    text = "DW_DATABASE='dw'\n\n-- Vale para DW\nUSER=u\nPASSWORD=\"p#1;2\"\n# x\nSEM_IGUAL\n"
    assert parse_env(text) == {"DW_DATABASE": "dw", "USER": "u", "PASSWORD": "p#1;2"}


def test_settings_sql_exige_chaves_e_nao_vaza_senha_no_repr():
    env = {"SERVER": "srv", "USER": "u", "PASSWORD": "segredo", "DW_DATABASE": "dw"}
    settings = SqlServerSettings.from_env("dw", env)
    assert settings.database == "dw"
    assert "segredo" not in repr(settings)
    with pytest.raises(ConfigError):
        SqlServerSettings.from_env("ODS", env)  # ODS_DATABASE ausente
    with pytest.raises(ConfigError):
        SqlServerSettings.from_env("OUTRO", env)


def test_connection_string_escapa_senha_e_so_pede_somente_leitura_em_driver_moderno():
    settings = SqlServerSettings("srv", "dw", "u", "a};b")
    novo = build_connection_string(settings, "ODBC Driver 18 for SQL Server")
    assert "PWD={a}};b}" in novo and "ApplicationIntent=ReadOnly" in novo
    assert "ApplicationIntent" not in build_connection_string(settings, "SQL Server")


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1",
        "select a, [Update] from t where x = 'delete from y' -- drop table z",
        "WITH c AS (SELECT 1 AS a) SELECT a FROM c;",
        "/* nota */ SELECT TOP 10 * FROM dbo.t WHERE d >= ?",
    ],
)
def test_assert_read_only_aceita_leituras_simples(sql):
    assert assert_read_only(sql) == sql


@pytest.mark.parametrize(
    "sql",
    [
        "",
        "DELETE FROM t",
        "SELECT 1; DROP TABLE t",
        "SELECT * INTO nova FROM t",
        "EXEC sp_who",
        "SELECT 1 /* ok */; UPDATE t SET a = 1",
        "WITH c AS (SELECT 1) INSERT INTO t SELECT * FROM c",
        "SELECT * FROM OPENROWSET('x', 'y', 'z')",
        "SELECT NEXT VALUE FOR dbo.seq",
        "SELECT 'aberta",
        "DECLARE @a INT = 1 SELECT @a",
    ],
)
def test_assert_read_only_recusa_escrita_e_multiplas_instrucoes(sql):
    with pytest.raises(UnsafeQueryError):
        assert_read_only(sql)


def test_query_recusa_escrita_antes_de_conectar(monkeypatch):
    monkeypatch.setenv("TCC_REAL_DATA_AUTHORIZED", "YES")
    reader = SqlServerReader(SqlServerSettings("srv", "dw", "u", "p"))
    with pytest.raises(UnsafeQueryError):
        reader.query("DELETE FROM t")


def test_query_exige_portao_de_dados_reais(monkeypatch):
    monkeypatch.delenv("TCC_REAL_DATA_AUTHORIZED", raising=False)
    reader = SqlServerReader(SqlServerSettings("srv", "dw", "u", "p"))
    with pytest.raises(PermissionError):
        reader.query("SELECT 1")


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/"),
        ("GET", "/_cluster/health"),
        ("POST", "/solicitacoes-2026.03/_search"),
        ("GET", "/idx-a,idx-b/_count"),
        ("POST", "/_search/scroll"),
        ("DELETE", "/_search/scroll"),
        ("GET", "/_cat/indices?format=json"),
    ],
)
def test_es_aceita_rotas_de_leitura(method, path):
    assert_allowed(method, path)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("PUT", "/idx"),
        ("DELETE", "/idx"),
        ("POST", "/idx/_doc"),
        ("POST", "/idx/_update/1"),
        ("POST", "/idx/_delete_by_query"),
        ("POST", "/_bulk"),
        ("POST", "/idx/_search/../_close"),
        ("PUT", "/_cluster/settings"),
        ("DELETE", "/_search/scroll/_all/x"),
    ],
)
def test_es_recusa_qualquer_rota_de_escrita_ou_administracao(method, path):
    with pytest.raises(ForbiddenRequestError):
        assert_allowed(method, path)


def test_es_settings_valida_url_e_oculta_senha():
    s = ElasticSettings.from_env({"ENDPOINT": "https://es.exemplo:9243/", "ES_USER": "u", "ES_PASSWORD": "segredo"})
    assert s.endpoint == "https://es.exemplo:9243" and "segredo" not in repr(s)
    with pytest.raises(ConfigError):
        ElasticSettings("es.exemplo", "u", "p")
