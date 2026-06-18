"""Tests du sink DuckDB (sur un fichier temporaire, sans Kafka)."""

from datetime import datetime, timezone

import duckdb

from air_quality_realtime.common.models import Alert, Pollutant, SensorReading
from air_quality_realtime.sink.duckdb_sink import DuckDBSink


def _reading() -> SensorReading:
    return SensorReading(
        station_id="BDX-CENTRE",
        city="Bordeaux",
        latitude=44.8378,
        longitude=-0.5792,
        timestamp=datetime.now(timezone.utc),
        pm25=12.0,
        pm10=20.0,
        no2=30.0,
        o3=80.0,
    )


def _alert() -> Alert:
    return Alert(
        station_id="BDX-CENTRE",
        city="Bordeaux",
        pollutant=Pollutant.NO2,
        average=30.0,
        threshold=25.0,
        window_size=5,
        exceedance_ratio=1.2,
        timestamp=datetime.now(timezone.utc),
    )


def test_write_persiste_readings_et_alerts(tmp_path):
    db = str(tmp_path / "test.duckdb")
    sink = DuckDBSink(db)
    n_r, n_a = sink.write([_reading(), _reading()], [_alert()])
    assert (n_r, n_a) == (2, 1)

    # Relecture via une connexion read-only indépendante (comme le dashboard).
    con = duckdb.connect(db, read_only=True)
    assert con.execute("SELECT count(*) FROM readings").fetchone()[0] == 2
    assert con.execute("SELECT count(*) FROM alerts").fetchone()[0] == 1
    assert con.execute("SELECT pollutant FROM alerts").fetchone()[0] == "no2"
    con.close()


def test_write_lot_vide_ninsere_rien(tmp_path):
    sink = DuckDBSink(str(tmp_path / "test.duckdb"))
    assert sink.write([], []) == (0, 0)


def test_schema_cree_meme_sans_ecriture(tmp_path):
    # Le schéma doit exister dès l'init, même avant toute écriture.
    db = str(tmp_path / "test.duckdb")
    DuckDBSink(db)
    con = duckdb.connect(db, read_only=True)
    tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
    assert {"readings", "alerts"} <= tables
    con.close()
