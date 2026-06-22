"""Lambda Producer — génère des relevés et les dépose dans SQS.

Port serverless du Producer du projet (SimulatedSource). À chaque invocation
(déclenchée par EventBridge), on émet un relevé par station vers la file SQS
"raw". Des pics aléatoires dépassent parfois les seuils OMS, ce qui permet de
voir le pipeline déclencher des alertes de bout en bout.

Pas de dépendance externe : stdlib + boto3 (fourni par AWS).
"""

from __future__ import annotations

import json
import os
import random
from datetime import datetime, timezone

import boto3

RAW_QUEUE_URL = os.environ["RAW_QUEUE_URL"]
N_STATIONS = int(os.environ.get("N_STATIONS", "5"))

_sqs = boto3.client("sqs")

# Quelques stations fictives (comme les stations simulées du projet).
STATIONS = [
    ("FR-PARIS-01", "Paris", 48.85, 2.35),
    ("FR-LYON-01", "Lyon", 45.76, 4.84),
    ("FR-MARSEILLE-01", "Marseille", 43.30, 5.37),
    ("FR-LILLE-01", "Lille", 50.63, 3.06),
    ("FR-BORDEAUX-01", "Bordeaux", 44.84, -0.58),
]

# (valeur_normale_max, valeur_de_pic) par polluant. ~25 % de chance de pic.
_PROFILE = {
    "pm25": (12.0, 45.0),
    "pm10": (35.0, 75.0),
    "no2": (20.0, 50.0),
    "o3": (80.0, 140.0),
}


def _measure(normal_max: float, spike: float, spike_prob: float = 0.25) -> float:
    if random.random() < spike_prob:
        return round(random.uniform(spike * 0.8, spike * 1.2), 1)
    return round(random.uniform(0.0, normal_max), 1)


def _make_reading(station: tuple) -> dict:
    station_id, city, lat, lon = station
    return {
        "station_id": station_id,
        "city": city,
        "latitude": lat,
        "longitude": lon,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pm25": _measure(*_PROFILE["pm25"]),
        "pm10": _measure(*_PROFILE["pm10"]),
        "no2": _measure(*_PROFILE["no2"]),
        "o3": _measure(*_PROFILE["o3"]),
    }


def handler(event, context):
    sent = 0
    for station in STATIONS[:N_STATIONS]:
        reading = _make_reading(station)
        _sqs.send_message(QueueUrl=RAW_QUEUE_URL, MessageBody=json.dumps(reading))
        sent += 1

    result = {"sent": sent}
    print(json.dumps(result))  # visible dans CloudWatch Logs
    return result
