"""Point d'entrée du sink (commande `aq-sink`).

Consomme `air-quality-raw` ET `air-quality-alerts`, et persiste dans DuckDB
par micro-lots. Le micro-batch est essentiel pour une base analytique : on
n'insère pas ligne par ligne (coûteux en colonnaire), on regroupe puis on écrit.
C'est exactement la logique qu'on appliquerait à Snowflake (COPY/Snowpipe).
"""

from __future__ import annotations

import time

import structlog

from air_quality_realtime.common.config import settings
from air_quality_realtime.common.kafka import create_consumer
from air_quality_realtime.common.models import Alert, SensorReading
from air_quality_realtime.sink.duckdb_sink import DuckDBSink

log = structlog.get_logger()


def main() -> None:
    consumer = create_consumer(
        settings.kafka_bootstrap_servers,
        settings.sink_group_id,
        [settings.topic_raw, settings.topic_alerts],
    )
    sink = DuckDBSink(settings.duckdb_path)

    readings: list[SensorReading] = []
    alerts: list[Alert] = []
    last_flush = time.monotonic()
    total_r = 0
    total_a = 0

    log.info(
        "sink.start",
        db=settings.duckdb_path,
        topics=[settings.topic_raw, settings.topic_alerts],
        batch_size=settings.sink_batch_size,
        flush_seconds=settings.sink_flush_seconds,
    )

    def flush() -> None:
        nonlocal total_r, total_a, last_flush
        n_r, n_a = sink.write(readings, alerts)
        if n_r or n_a:
            total_r += n_r
            total_a += n_a
            log.info(
                "sink.flush",
                readings=n_r,
                alerts=n_a,
                total_readings=total_r,
                total_alerts=total_a,
            )
        readings.clear()
        alerts.clear()
        last_flush = time.monotonic()

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is not None:
                if msg.error():
                    log.error("consume.error", error=str(msg.error()))
                elif msg.topic() == settings.topic_raw:
                    readings.append(SensorReading.model_validate_json(msg.value()))
                elif msg.topic() == settings.topic_alerts:
                    alerts.append(Alert.model_validate_json(msg.value()))

            # On écrit si le lot est plein OU si le délai est écoulé (et qu'il y a
            # quelque chose à écrire) : garantit une latence bornée même à faible débit.
            buffered = len(readings) + len(alerts)
            due = (time.monotonic() - last_flush) >= settings.sink_flush_seconds
            if buffered >= settings.sink_batch_size or (due and buffered):
                flush()
    except KeyboardInterrupt:
        log.info("sink.stop")
    finally:
        flush()  # ne pas perdre le dernier lot
        sink.close()
        consumer.close()


if __name__ == "__main__":
    main()
