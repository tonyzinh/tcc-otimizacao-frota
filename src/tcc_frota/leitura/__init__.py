"""Conexões somente leitura ao SQL Server e ao Elasticsearch de origem.

Defesa em camadas, nesta ordem de força: (1) permissões do login (use contas só de leitura);
(2) o cliente deste pacote só emite consultas aprovadas por uma lista de permissões;
(3) leituras de dados reais exigem `TCC_REAL_DATA_AUTHORIZED=YES` (portão do projeto).
Nada aqui grava no banco, no índice ou no disco, e as credenciais nunca aparecem em `repr` ou erros.
"""

from tcc_frota.leitura.env import ConfigError, load_env
from tcc_frota.leitura.es import ElasticReader, ElasticSettings
from tcc_frota.leitura.sql_guard import UnsafeQueryError, assert_read_only
from tcc_frota.leitura.sqlserver import SqlServerReader, SqlServerSettings

__all__ = [
    "ConfigError",
    "ElasticReader",
    "ElasticSettings",
    "SqlServerReader",
    "SqlServerSettings",
    "UnsafeQueryError",
    "assert_read_only",
    "load_env",
]
