"""Accès en lecture à l'entrepôt DuckDB pour le dashboard.

Connexion en read-only avec petit retry : le sink relâche le verrou entre deux
micro-lots, mais une collision ponctuelle reste possible — on réessaie alors.

La notion de "récent" est calée sur le dernier événement présent dans la table
(et non sur l'horloge murale) : le dashboard reste pertinent aussi bien en live
que sur des données rejouées.
"""

from __future__ import annotations

import time

import duckdb
import pandas as pd

# Fenêtre considérée comme "récente" pour les alertes (minutes).
RECENT_MINUTES = 15


def _connect(path: str, retries: int = 5, delay: float = 0.3) -> duckdb.DuckDBPyConnection:
    last_exc: Exception | None = None
    for _ in range(retries):
        try:
            return duckdb.connect(path, read_only=True)
        except duckdb.Error as exc:  # verrou tenu par le sink à cet instant
            last_exc = exc
            time.sleep(delay)
    raise RuntimeError(f"Connexion DuckDB read-only impossible: {last_exc}")


def get_summary(path: str) -> dict:
    """Compteurs globaux + nombre de stations en alerte récemment."""
    con = _connect(path)
    try:
        n_readings = con.execute("SELECT count(*) FROM readings").fetchone()[0]
        n_alerts = con.execute("SELECT count(*) FROM alerts").fetchone()[0]
        stations_en_alerte = con.execute(
            f"""
            SELECT count(DISTINCT station_id) FROM alerts
            WHERE event_time >= (SELECT max(event_time) FROM alerts)
                                 - INTERVAL {RECENT_MINUTES} MINUTE
            """
        ).fetchone()[0]
        return {
            "readings": n_readings,
            "alerts": n_alerts,
            "stations_en_alerte": stations_en_alerte or 0,
        }
    finally:
        con.close()


def get_station_status(path: str) -> pd.DataFrame:
    """Dernier relevé par station + drapeau d'alerte récente (pour la carte)."""
    con = _connect(path)
    try:
        return con.execute(
            f"""
            WITH dernier AS (
                SELECT station_id, city, latitude, longitude, pm25, pm10, no2, o3,
                       row_number() OVER (PARTITION BY station_id
                                          ORDER BY event_time DESC) AS rn
                FROM readings
            ),
            recentes AS (
                SELECT DISTINCT station_id FROM alerts
                WHERE event_time >= (SELECT max(event_time) FROM alerts)
                                     - INTERVAL {RECENT_MINUTES} MINUTE
            )
            SELECT d.station_id, d.city, d.latitude, d.longitude,
                   d.pm25, d.pm10, d.no2, d.o3,
                   (r.station_id IS NOT NULL) AS en_alerte
            FROM dernier d
            LEFT JOIN recentes r USING (station_id)
            WHERE d.rn = 1
            """
        ).df()
    finally:
        con.close()


def get_recent_alerts(path: str, limit: int = 20) -> pd.DataFrame:
    con = _connect(path)
    try:
        return con.execute(
            """
            SELECT event_time, station_id, city, pollutant,
                   average, threshold, exceedance_ratio
            FROM alerts
            ORDER BY event_time DESC
            LIMIT ?
            """,
            [limit],
        ).df()
    finally:
        con.close()


def get_station_timeseries(path: str, station_id: str, limit: int = 100) -> pd.DataFrame:
    """Évolution des polluants pour une station (les `limit` derniers relevés)."""
    con = _connect(path)
    try:
        df = con.execute(
            """
            SELECT event_time, pm25, pm10, no2, o3
            FROM readings
            WHERE station_id = ?
            ORDER BY event_time DESC
            LIMIT ?
            """,
            [station_id, limit],
        ).df()
        return df.sort_values("event_time").set_index("event_time")
    finally:
        con.close()


def get_station_ids(path: str) -> list[str]:
    con = _connect(path)
    try:
        return [r[0] for r in con.execute(
            "SELECT DISTINCT station_id FROM readings ORDER BY station_id"
        ).fetchall()]
    finally:
        con.close()
