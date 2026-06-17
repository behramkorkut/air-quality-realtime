"""Publication des relevés vers Redpanda (API Kafka).

On encapsule le `confluent_kafka.Producer` dans une petite classe pour :
- centraliser la config et la sérialisation ;
- gérer le rapport de livraison (savoir si un message a échoué) ;
- exposer une API simple (`publish`, `flush`) au reste du code.
"""

from __future__ import annotations

import structlog
from confluent_kafka import Producer

from air_quality_realtime.common.models import SensorReading

log = structlog.get_logger()


class KafkaPublisher:
    def __init__(self, bootstrap_servers: str, topic: str) -> None:
        self.topic = topic
        # `linger.ms` : petite attente pour regrouper les messages en lots
        # (meilleur débit). En dev la valeur par défaut suffit largement.
        self._producer = Producer(
            {
                "bootstrap.servers": bootstrap_servers,
                "client.id": "aq-producer",
            }
        )

    def _on_delivery(self, err, msg) -> None:
        """Callback appelé par librdkafka quand un message est livré (ou échoue)."""
        if err is not None:
            log.error("delivery.failed", error=str(err))

    def publish(self, reading: SensorReading) -> None:
        # La CLÉ du message = station_id. Conséquence importante : tous les
        # relevés d'une même station partent dans la même partition, ce qui
        # garantit leur ordre. C'est le rôle clé du partitionnement par clé.
        self._producer.produce(
            self.topic,
            key=reading.station_id.encode("utf-8"),
            value=reading.model_dump_json().encode("utf-8"),
            on_delivery=self._on_delivery,
        )
        # poll(0) : traite les callbacks de livraison en attente, sans bloquer.
        self._producer.poll(0)

    def flush(self, timeout: float = 10.0) -> None:
        """Attend l'envoi des messages encore en mémoire (à l'arrêt)."""
        remaining = self._producer.flush(timeout)
        if remaining > 0:
            log.warning("flush.incomplete", remaining=remaining)
