"""Sink DuckDB : persiste relevés et alertes dans un entrepôt local.

DuckDB est une base analytique colonnaire (OLAP), même philosophie que
Snowflake/BigQuery mais en local et sans serveur. On l'utilise comme stand-in
de Snowflake pour développer toute la logique de chargement sans coût ni cloud.
Voir docs/snowflake-deployment.md pour la transposition vers Snowflake.
"""

from __future__ import annotations

import duckdb
import structlog

from air_quality_realtime.common.models import Alert, SensorReading

log = structlog.get_logger()

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
        self._con = duckdb.connect(path)
        self._con.execute(_SCHEMA)

    def write_readings(self, readings: list[SensorReading]) -> int:
        if not readings:
            return 0
        rows = [
            (r.station_id, r.city, r.latitude, r.longitude, r.timestamp,
             r.pm25, r.pm10, r.no2, r.o3)
            for r in readings
        ]
        # executemany dans une transaction implicite : un seul lot inséré d'un coup.
        self._con.executemany(
            "INSERT INTO readings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows
        )
        return len(rows)

    def write_alerts(self, alerts: list[Alert]) -> int:
        if not alerts:
            return 0
        rows = [
            (a.station_id, a.city, a.pollutant.value, a.average, a.threshold,
             a.window_size, a.exceedance_ratio, a.timestamp)
            for a in alerts
        ]
        self._con.executemany(
            "INSERT INTO alerts VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows
        )
        return len(rows)

    def close(self) -> None:
        self._con.close()
