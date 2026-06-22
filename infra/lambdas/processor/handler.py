"""Lambda Processor — détection d'alertes qualité de l'air sur AWS.

Port serverless du module `processor/detector.py` du projet. Même logique :
pour chaque (station, polluant), on maintient une fenêtre glissante des
derniers relevés et on compare leur MOYENNE au seuil OMS. Déclenchement
"edge-triggered" : on alerte uniquement au passage SOUS -> AU-DESSUS du seuil.

Différence imposée par le serverless : une Lambda est sans état entre deux
invocations. La fenêtre glissante et le flag "en alerte" sont donc persistés
dans DynamoDB (table window-state) au lieu d'être gardés en RAM.

Le handler accepte deux formes d'événement :
- un événement SQS (clé "Records", chaque "body" = un relevé JSON) ;
- un événement de test direct : un relevé seul, ou {"readings": [ ... ]}.
"""

from __future__ import annotations

import json
import os
from decimal import Decimal

import boto3

# --- Configuration (injectée par Terraform via les variables d'environnement) ---
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]
READINGS_TABLE = os.environ["READINGS_TABLE"]
WINDOW_STATE_TABLE = os.environ["WINDOW_STATE_TABLE"]
WINDOW_SIZE = int(os.environ.get("WINDOW_SIZE", "5"))

# Seuils indicatifs OMS 2021 (µg/m³) — identiques à common/models.py.
WHO_THRESHOLDS: dict[str, float] = {
    "pm25": 15.0,
    "pm10": 45.0,
    "no2": 25.0,
    "o3": 100.0,
}

# Clients AWS (réutilisés entre invocations à chaud).
_dynamodb = boto3.resource("dynamodb")
_sns = boto3.client("sns")
_readings_table = _dynamodb.Table(READINGS_TABLE)
_window_table = _dynamodb.Table(WINDOW_STATE_TABLE)


def _to_dynamo(value):
    """DynamoDB n'accepte pas les float Python : on convertit en Decimal."""
    if isinstance(value, float):
        return Decimal(str(value))
    return value


def _store_reading(reading: dict) -> None:
    item = {k: _to_dynamo(v) for k, v in reading.items()}
    _readings_table.put_item(Item=item)


def _process_reading(reading: dict) -> list[dict]:
    """Met à jour les fenêtres et renvoie les NOUVELLES alertes déclenchées."""
    alerts: list[dict] = []
    station_id = reading["station_id"]
    city = reading.get("city", "")
    timestamp = reading["timestamp"]

    _store_reading(reading)

    for pollutant, threshold in WHO_THRESHOLDS.items():
        if pollutant not in reading:
            continue
        value = float(reading[pollutant])
        pk = f"{station_id}#{pollutant}"

        # 1. Charger l'état persistant de la fenêtre (ou repartir de zéro).
        state = _window_table.get_item(Key={"pk": pk}).get("Item")
        values = [float(v) for v in state["values"]] if state else []
        in_alert = bool(state["in_alert"]) if state else False

        # 2. Mettre à jour la fenêtre glissante (on garde les WINDOW_SIZE derniers).
        values.append(value)
        values = values[-WINDOW_SIZE:]
        average = sum(values) / len(values)

        # 3. Logique edge-triggered (identique à AlertDetector.process).
        new_in_alert = in_alert
        if average > threshold:
            if not in_alert:  # transition sous -> au-dessus
                new_in_alert = True
                alerts.append(
                    {
                        "station_id": station_id,
                        "city": city,
                        "pollutant": pollutant,
                        "average": round(average, 2),
                        "threshold": threshold,
                        "window_size": len(values),
                        "exceedance_ratio": round(average / threshold, 2),
                        "timestamp": timestamp,
                    }
                )
        else:
            new_in_alert = False  # repassé sous le seuil -> réarme

        # 4. Persister le nouvel état.
        _window_table.put_item(
            Item={
                "pk": pk,
                "values": [Decimal(str(v)) for v in values],
                "in_alert": new_in_alert,
                "updated_at": timestamp,
            }
        )

    return alerts


def _publish_alert(alert: dict) -> None:
    subject = f"🚨 {alert['city']} — {alert['pollutant'].upper()} au-dessus du seuil OMS"
    message = (
        f"Dépassement détecté sur la station {alert['station_id']} ({alert['city']}).\n\n"
        f"Polluant      : {alert['pollutant'].upper()}\n"
        f"Moyenne ({alert['window_size']} relevés) : {alert['average']} µg/m³\n"
        f"Seuil OMS     : {alert['threshold']} µg/m³\n"
        f"Sévérité      : x{alert['exceedance_ratio']} le seuil\n"
        f"Horodatage    : {alert['timestamp']}\n"
    )
    _sns.publish(TopicArn=SNS_TOPIC_ARN, Subject=subject[:100], Message=message)


def _extract_readings(event: dict) -> list[dict]:
    """Normalise les différentes formes d'événement en une liste de relevés."""
    if "Records" in event:  # déclenchement par SQS
        return [json.loads(record["body"]) for record in event["Records"]]
    if "readings" in event:  # test : {"readings": [...]}
        return event["readings"]
    return [event]  # test : un relevé unique


def handler(event, context):
    readings = _extract_readings(event)
    all_alerts: list[dict] = []
    for reading in readings:
        all_alerts.extend(_process_reading(reading))

    for alert in all_alerts:
        _publish_alert(alert)

    result = {"processed": len(readings), "alerts": len(all_alerts)}
    print(json.dumps(result))  # visible dans CloudWatch Logs
    return result
