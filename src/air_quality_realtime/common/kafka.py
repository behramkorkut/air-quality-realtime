"""Plomberie Kafka/Redpanda partagée par le producer et le processor.

On factorise ici ce qui est commun : un producteur JSON générique (envoie
n'importe quel modèle Pydantic) et une fabrique de consumer configuré.
"""

from __future__ import annotations

import structlog
from confluent_kafka import Consumer, Producer
from pydantic import BaseModel

log = structlog.get_logger()


class JsonProducer:
    """Producteur générique : sérialise un modèle Pydantic en JSON et l'envoie.

    Asynchrone (librdkafka) : `produce()` bufferise, `poll(0)` traite les
    accusés de livraison, `flush()` vide le buffer à l'arrêt.
    """

    def __init__(self, bootstrap_servers: str, client_id: str = "aq") -> None:
        self._producer = Producer(
            {"bootstrap.servers": bootstrap_servers, "client.id": client_id}
        )

    def _on_delivery(self, err, msg) -> None:
        if err is not None:
            log.error("delivery.failed", error=str(err))

    def publish(self, topic: str, key: str, payload: BaseModel) -> None:
        # La clé détermine la partition : même clé -> même partition -> ordre garanti.
        self._producer.produce(
            topic,
            key=key.encode("utf-8"),
            value=payload.model_dump_json().encode("utf-8"),
            on_delivery=self._on_delivery,
        )
        self._producer.poll(0)

    def flush(self, timeout: float = 10.0) -> None:
        remaining = self._producer.flush(timeout)
        if remaining > 0:
            log.warning("flush.incomplete", remaining=remaining)


def create_consumer(
    bootstrap_servers: str, group_id: str, topics: list[str]
) -> Consumer:
    """Crée un consumer abonné aux topics donnés.

    - group.id : les consumers d'un même groupe se partagent les partitions
      (scalabilité horizontale). Les offsets sont suivis par groupe.
    - auto.offset.reset=earliest : si le groupe n'a jamais lu, on repart du début.
    """
    consumer = Consumer(
        {
            "bootstrap.servers": bootstrap_servers,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
        }
    )
    consumer.subscribe(topics)
    return consumer
