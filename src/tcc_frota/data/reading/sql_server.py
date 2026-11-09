"""Leitor SQL Server somente leitura (pyodbc). Bancos: DW, ODS e STG do `.env`."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any

from tcc_frota.data.authorization import authorize
from tcc_frota.data.reading.env import ConfigError, load_env, require
from tcc_frota.data.reading.sql_guard import assert_catalog_only, assert_read_only

DATABASES = ("DW", "ODS", "STG")
PREFERRED_DRIVERS = ("ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server", "SQL Server")


@dataclass(frozen=True)
class SqlServerSettings:
    server: str
    database: str
    user: str
    password: str = field(repr=False)
    driver: str | None = None  # None = o melhor driver ODBC instalado
    trust_server_certificate: bool = False

    @classmethod
    def from_env(cls, database: str = "DW", env: dict[str, str] | None = None) -> SqlServerSettings:
        key = database.upper()
        if key not in DATABASES:
            raise ConfigError(f"banco inválido: use um de {DATABASES}")
        values = env if env is not None else load_env()
        require(values, "SERVER", "USER", "PASSWORD", f"{key}_DATABASE")
        return cls(
            server=values["SERVER"],
            database=values[f"{key}_DATABASE"],
            user=values["USER"],
            password=values["PASSWORD"],
            driver=values.get("SQL_DRIVER") or None,
            trust_server_certificate=values.get("SQL_TRUST_SERVER_CERTIFICATE", "").lower() in {"1", "true", "yes"},
        )


def _braced(value: str) -> str:
    return "{" + value.replace("}", "}}") + "}"


def build_connection_string(settings: SqlServerSettings, driver: str, *, timeout_s: int = 15) -> str:
    parts = [
        f"DRIVER={_braced(driver)}",
        f"SERVER={settings.server}",
        f"DATABASE={_braced(settings.database)}",
        f"UID={_braced(settings.user)}",
        f"PWD={_braced(settings.password)}",
    ]
    if "ODBC Driver" in driver:  # o driver legado "SQL Server" não entende estas palavras-chave
        trust = "yes" if settings.trust_server_certificate else "no"
        parts += ["ApplicationIntent=ReadOnly", "Encrypt=yes", f"TrustServerCertificate={trust}", f"Connection Timeout={timeout_s}"]
    return ";".join(parts)


def _scrub(message: str, settings: SqlServerSettings) -> str:
    for secret in (settings.password, settings.user):
        if secret:
            message = message.replace(secret, "***")
    return message


class SqlServerReader:
    """Executa apenas SELECT/WITH aprovados por `assert_read_only`, em transação sempre revertida."""

    def __init__(self, settings: SqlServerSettings, *, query_timeout_s: int = 300, connect_timeout_s: int = 15):
        self.settings = settings
        self.query_timeout_s = query_timeout_s
        self.connect_timeout_s = connect_timeout_s
        self._conn: Any = None

    @classmethod
    def from_env(cls, database: str = "DW", **kwargs: Any) -> SqlServerReader:
        return cls(SqlServerSettings.from_env(database), **kwargs)

    def _driver(self, pyodbc: Any) -> str:
        installed = set(pyodbc.drivers())
        if self.settings.driver:
            if self.settings.driver not in installed:
                raise ConfigError("driver ODBC configurado não está instalado")
            return self.settings.driver
        for name in PREFERRED_DRIVERS:
            if name in installed:
                return name
        raise ConfigError("nenhum driver ODBC do SQL Server instalado")

    def connect(self) -> SqlServerReader:
        if self._conn is not None:
            return self
        try:
            import pyodbc
        except ImportError as exc:  # pragma: no cover - depende do ambiente
            raise ConfigError("instale o extra de leitura: pip install -e .[fontes]") from exc
        driver = self._driver(pyodbc)
        try:
            self._conn = pyodbc.connect(
                build_connection_string(self.settings, driver, timeout_s=self.connect_timeout_s),
                autocommit=False,
                timeout=self.query_timeout_s,
            )
        except pyodbc.Error as exc:
            detail = _scrub(str(exc), self.settings)
            raise ConnectionError(f"falha ao conectar ao SQL Server ({type(exc).__name__}): {detail}") from None
        return self

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.rollback()
            finally:
                self._conn.close()
                self._conn = None

    def __enter__(self) -> SqlServerReader:
        return self.connect()

    def __exit__(self, *exc: object) -> None:
        self.close()

    def ping(self) -> dict[str, Any]:
        """Verifica a conexão sem ler dados de negócio (não exige o portão de dados reais)."""
        self.connect()
        cur = self._conn.cursor()
        try:
            cur.execute("SELECT 1")
            ok = cur.fetchone()[0] == 1
        finally:
            cur.close()
            self._conn.rollback()
        return {"ok": ok, "database": self.settings.database}

    def inspect(self, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        """Metadados (INFORMATION_SCHEMA / sys): não lê dados de negócio, por isso não exige o portão de dados reais."""
        assert_catalog_only(sql)
        return list(self._iter(sql, params, 10_000))

    def iter_query(self, sql: str, params: Sequence[Any] = (), *, batch_size: int = 10_000) -> Iterator[dict[str, Any]]:
        """Itera linhas como dicionários, em lotes, sem materializar o resultado."""
        authorize("real", "local")
        assert_read_only(sql)
        yield from self._iter(sql, params, batch_size)

    def _iter(self, sql: str, params: Sequence[Any], batch_size: int) -> Iterator[dict[str, Any]]:
        self.connect()
        cur = self._conn.cursor()
        try:
            cur.execute(sql, tuple(params))
            names = [c[0] for c in cur.description or ()]
            while True:
                rows = cur.fetchmany(batch_size)
                if not rows:
                    return
                for row in rows:
                    yield dict(zip(names, row, strict=True))
        finally:
            cur.close()
            self._conn.rollback()

    def query(self, sql: str, params: Sequence[Any] = (), *, max_rows: int = 500_000) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for row in self.iter_query(sql, params):
            if len(out) >= max_rows:
                raise OverflowError(f"resultado excede {max_rows} linhas: use iter_query ou filtre/agregue na consulta")
            out.append(row)
        return out
