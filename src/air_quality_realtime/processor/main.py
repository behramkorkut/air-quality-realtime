"""Point d'entrée du processor (commande `aq-processor`).

Consomme les relevés depuis `air-quality-raw`, détecte les dépassements de
seuils (moyenne glissante) et publie les alertes sur `air-quality-alerts`.
"""

from __future__ import annotations

import structlog

from air_quality_realtime.common.config import settings
from air_quality_realtime.common.kafka import JsonProducer, create_consumer
from air_quality_realtime.common.models import SensorReading
from air_quality_realtime.processor.detector import AlertDetector

log = structlog.get_logger()


def main() -> None:
    consumer = create_consumer(
        settings.kafka_bootstrap_servers,
        settings.processor_group_id,
        [settings.topic_raw],
    )
    producer = JsonProducer(settings.kafka_bootstrap_servers, client_id="aq-processor")
    detector = AlertDetector(window_size=settings.processor_window_size)

    log.info(
        "processor.start",
        group_id=settings.processor_group_id,
        consume=settings.topic_raw,
        produce=settings.topic_alerts,
        window_size=settings.processor_window_size,
    )

    try:
        while True:
            msg = consumer.poll(1.0)  # attend jusqu'à 1 s un nouveau message
            if msg is None:
                continue
            if msg.error():
                log.error("consume.error", error=str(msg.error()))
                continue

            reading = SensorReading.model_validate_json(msg.value())
            for alert in detector.process(reading):
                producer.publish(settings.topic_alerts, alert.station_id, alert)
                log.warning(
                    "alert.raised",
                    station=alert.station_id,
                    pollutant=alert.pollutant.value,
                    average=alert.average,
                    threshold=alert.threshold,
                    ratio=alert.exceedance_ratio,
                )
    except KeyboardInterrupt:
        log.info("processor.stop")
    finally:
        producer.flush()
        consumer.close()  # quitte proprement le consumer group


if __name__ == "__main__":
    main()
