"""Tests du sink DuckDB (avec une base en mémoire, sans Kafka ni fichier)."""

from datetime import datetime, timezone

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


def test_schema_cree_et_insertion_readings():
    sink = DuckDBSink(":memory:")
    assert sink.write_readings([_reading(), _reading()]) == 2
    count = sink._con.execute("SELECT count(*) FROM readings").fetchone()[0]
    assert count == 2
    sink.close()


def test_insertion_alerts():
    sink = DuckDBSink(":memory:")
    assert sink.write_alerts([_alert()]) == 1
    row = sink._con.execute(
        "SELECT pollutant, exceedance_ratio FROM alerts"
    ).fetchone()
    assert row == ("no2", 1.2)
    sink.close()


def test_lot_vide_ninsere_rien():
    sink = DuckDBSink(":memory:")
    assert sink.write_readings([]) == 0
    assert sink.write_alerts([]) == 0
    sink.close()
