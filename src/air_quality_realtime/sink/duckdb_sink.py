"""Sink DuckDB : persiste relevés et alertes dans un entrepôt local.

DuckDB est une base analytique colonnaire (OLAP), même philosophie que
Snowflake/BigQuery mais en local et sans serveur. On l'utilise comme stand-in
de Snowflake pour développer toute la logique de chargement sans coût ni cloud.
Voir docs/snowflake-deployment.md pour la transposition vers Snowflake.

Concurrence : DuckDB n'autorise qu'UN seul processus en écriture sur le fichier.
Pour que le dashboard puisse lire pendant que le sink tourne, le sink ouvre et
FERME sa connexion à chaque écriture (il ne garde donc pas le verrou en continu).
Le dashboard lit alors en read-only dans les intervalles.
"""

from __future__ import annotations

import time

import duckdb
import structlog

from air_quality_realtime.common.models import Alert, SensorReading

log = structlog.get_logger()


def _connect_rw(path: str, retries: int = 10, delay: float = 0.2) -> duckdb.DuckDBPyConnection:
    """Ouvre une connexion en écriture, avec retry si le dashboard lit à l'instant T."""
    last_exc: Exception | None = None
    for _ in range(retries):
        try:
            return duckdb.connect(path)
        except duckdb.Error as exc:  # une connexion concurrente tient le verrou
            last_exc = exc
            time.sleep(delay)
    raise RuntimeError(f"Connexion DuckDB en écriture impossible: {last_exc}")

# TIMESTAMPTZ : DuckDB stocke un instant avec fuseau (équivaut au TIMESTAMP_TZ
# de Snowflake). Schéma idempotent (IF NOT EXISTS) : créable à chaque démarrage.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS readings (
    station_id  VARCHAR,
    city        VARCHAR,
    latitude    DOUBLE,
    longitude   DOUBLE,
    event_time  TIMESTAMPTZ,
    pm25        DOUBLE,
    pm10        DOUBLE,
    no2         DOUBLE,
    o3          DOUBLE
);

CREATE TABLE IF NOT EXISTS alerts (
    station_id       VARCHAR,
    city             VARCHAR,
    pollutant        VARCHAR,
    average          DOUBLE,
    threshold        DOUBLE,
    window_size      INTEGER,
    exceedance_ratio DOUBLE,
    event_time       TIMESTAMPTZ
);
"""


class DuckDBSink:
    def __init__(self, path: str) -> None:
        self.path = path
        # On crée le schéma une fois, puis on relâche tout de suite la connexion.
        con = _connect_rw(self.path)
        try:
            con.execute(_SCHEMA)
        finally:
            con.close()

    def write(self, readings: list[SensorReading], alerts: list[Alert]) -> tuple[int, int]:
        """Écrit un micro-lot (relevés + alertes) puis ferme la connexion.

        Ouvrir/fermer à chaque lot libère le verrou d'écriture entre deux flushes,
        ce qui permet au dashboard de lire le fichier en read-only.
        """
        if not readings and not alerts:
            return (0, 0)

        con = _connect_rw(self.path)
        try:
            n_r = self._insert_readings(con, readings)
            n_a = self._insert_alerts(con, alerts)
        finally:
            con.close()
        return (n_r, n_a)

    @staticmethod
    def _insert_readings(con: duckdb.DuckDBPyConnection, readings: list[SensorReading]) -> int:
        if not readings:
            return 0
        rows = [
            (r.station_id, r.city, r.latitude, r.longitude, r.timestamp,
             r.pm25, r.pm10, r.no2, r.o3)
            for r in readings
        ]
        con.executemany("INSERT INTO readings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
        return len(rows)

    @staticmethod
    def _insert_alerts(con: duckdb.DuckDBPyConnection, alerts: list[Alert]) -> int:
        if not alerts:
            return 0
        rows = [
            (a.station_id, a.city, a.pollutant.value, a.average, a.threshold,
             a.window_size, a.exceedance_ratio, a.timestamp)
            for a in alerts
        ]
        con.executemany("INSERT INTO alerts VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
        return len(rows)
