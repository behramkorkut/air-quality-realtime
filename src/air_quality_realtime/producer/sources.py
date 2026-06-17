"""Sources de relevés — abstraction interchangeable.

Idée clé (inversion de dépendance) : le producer consomme une `ReadingSource`
sans savoir d'où viennent les données. On peut donc brancher :
- `SimulatedSource`  : capteurs simulés, haute fréquence (démo temps réel live) ;
- `OpenMeteoSource`  : vraies données via l'API publique gratuite Open-Meteo.

Les deux exposent la même méthode `fetch()` qui renvoie un relevé par station.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

import httpx
import structlog

from air_quality_realtime.common.models import SensorReading
from air_quality_realtime.producer.sensors import Station

log = structlog.get_logger()


class ReadingSource(Protocol):
    """Contrat commun à toutes les sources."""

    name: str

    def fetch(self) -> list[SensorReading]:
        """Renvoie un lot de relevés (en général un par station)."""
        ...


class SimulatedSource:
    """Génère des relevés synthétiques à partir du simulateur de stations."""

    name = "simulated"

    def __init__(self, stations: list[Station], spike_probability: float = 0.05) -> None:
        self.stations = stations
        self.spike_probability = spike_probability

    def fetch(self) -> list[SensorReading]:
        return [s.generate_reading(self.spike_probability) for s in self.stations]


class OpenMeteoSource:
    """Récupère les vraies concentrations via l'API Open-Meteo (gratuite, sans clé).

    Doc : https://open-meteo.com/en/docs/air-quality-api
    Note : les données sont horaires — cette source est faite pour être appelée
    périodiquement (typiquement par le DAG Airflow), pas en haute fréquence.
    """

    name = "openmeteo"
    BASE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

    # Correspondance noms de paramètres Open-Meteo -> champs de notre modèle.
    _PARAM_MAP = {
        "pm2_5": "pm25",
        "pm10": "pm10",
        "nitrogen_dioxide": "no2",
        "ozone": "o3",
    }

    def __init__(
        self,
        stations: list[Station],
        client: httpx.Client | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.stations = stations
        self._client = client or httpx.Client(timeout=timeout)

    def fetch(self) -> list[SensorReading]:
        readings: list[SensorReading] = []
        for st in self.stations:
            params = {
                "latitude": st.latitude,
                "longitude": st.longitude,
                "current": ",".join(self._PARAM_MAP.keys()),
                "timezone": "GMT",
            }
            resp = self._client.get(self.BASE_URL, params=params)
            resp.raise_for_status()
            current = resp.json()["current"]

            # Open-Meteo renvoie une heure sans fuseau (ex. "2026-06-17T14:00")
            # qu'on interprète en UTC (on a demandé timezone=GMT).
            ts = datetime.fromisoformat(current["time"]).replace(tzinfo=timezone.utc)

            readings.append(
                SensorReading(
                    station_id=st.station_id,
                    city=st.city,
                    latitude=st.latitude,
                    longitude=st.longitude,
                    timestamp=ts,
                    # `or 0.0` : l'API peut renvoyer null pour un polluant manquant.
                    **{
                        field: float(current.get(api_key) or 0.0)
                        for api_key, field in self._PARAM_MAP.items()
                    },
                )
            )
        return readings


def build_source(name: str, stations: list[Station]) -> ReadingSource:
    """Fabrique la source demandée (sélectionnée via la config `SOURCE`)."""
    if name == "simulated":
        return SimulatedSource(stations)
    if name == "openmeteo":
        return OpenMeteoSource(stations)
    raise ValueError(f"Source inconnue : {name!r} (attendu: 'simulated' ou 'openmeteo')")
