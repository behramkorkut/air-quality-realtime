"""Point d'entrée du producer (commande `aq-producer`).

Récupère des relevés depuis la source configurée (`simulated` ou `openmeteo`)
et les publie sur le topic Redpanda `air-quality-raw`.
"""

from __future__ import annotations

import time

import structlog

from air_quality_realtime.common.config import settings
from air_quality_realtime.producer.publisher import KafkaPublisher
from air_quality_realtime.producer.sensors import build_stations
from air_quality_realtime.producer.sources import build_source

log = structlog.get_logger()


def main() -> None:
    stations = build_stations(settings.producer_n_stations)
    source = build_source(settings.source, stations)
    publisher = KafkaPublisher(settings.kafka_bootstrap_servers, settings.topic_raw)

    log.info(
        "producer.start",
        source=source.name,
        topic=settings.topic_raw,
        bootstrap=settings.kafka_bootstrap_servers,
        n_stations=len(stations),
        interval_s=settings.producer_interval_seconds,
    )

    sent = 0
    try:
        while True:
            for reading in source.fetch():
                publisher.publish(reading)
                sent += 1
            log.info("producer.batch_sent", total=sent)
            time.sleep(settings.producer_interval_seconds)
    except KeyboardInterrupt:
        log.info("producer.stop", total=sent)
    finally:
        # On s'assure que les derniers messages partent bien avant de quitter.
        publisher.flush()


if __name__ == "__main__":
    main()
