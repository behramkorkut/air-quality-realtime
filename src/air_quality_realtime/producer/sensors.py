"""Simulateur de stations de mesure de la qualité de l'air.

Génère des relevés réalistes : niveau de base par station, cycle journalier
(pics aux heures de pointe pour le NO2), bruit aléatoire, et pics de pollution
occasionnels pour déclencher des alertes côté processor.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone

from air_quality_realtime.common.models import Pollutant, SensorReading


@dataclass
class Station:
    """Une station de mesure, avec ses niveaux de base par polluant (µg/m³)."""

    station_id: str
    city: str
    latitude: float
    longitude: float
    baselines: dict[Pollutant, float] = field(default_factory=dict)

    def generate_reading(self, spike_probability: float = 0.05) -> SensorReading:
        """Produit un relevé pour l'instant présent (UTC).

        - facteur journalier : 2 pics (matin ~8h, soir ~19h) liés au trafic ;
        - bruit gaussien ~15 % autour du niveau de base ;
        - avec une probabilité `spike_probability`, on injecte un pic (x2 à x4).
        """
        now = datetime.now(timezone.utc)
        factor = _diurnal_factor(now.hour)

        def value(base: float) -> float:
            noise = random.gauss(0, base * 0.15)
            v = base * factor + noise
            if random.random() < spike_probability:
                v *= random.uniform(2.0, 4.0)  # épisode de pollution
            return round(max(0.0, v), 1)

        return SensorReading(
            station_id=self.station_id,
            city=self.city,
            latitude=self.latitude,
            longitude=self.longitude,
            timestamp=now,
            pm25=value(self.baselines[Pollutant.PM25]),
            pm10=value(self.baselines[Pollutant.PM10]),
            no2=value(self.baselines[Pollutant.NO2]),
            o3=value(self.baselines[Pollutant.O3]),
        )


def _diurnal_factor(hour: int) -> float:
    """Multiplicateur selon l'heure : ~1 la nuit, pics matin et soir."""
    morning = 0.4 * math.exp(-((hour - 8) ** 2) / 8)
    evening = 0.5 * math.exp(-((hour - 19) ** 2) / 8)
    return 1.0 + morning + evening


# Pool de stations bordelaises (coordonnées approximatives). Chaque station a un
# profil différent : trafic dense, fond urbain, périurbain, etc.
_STATION_POOL: list[Station] = [
    Station("BDX-CENTRE", "Bordeaux", 44.8378, -0.5792,
            {Pollutant.PM25: 12, Pollutant.PM10: 22, Pollutant.NO2: 28, Pollutant.O3: 45}),
    Station("BDX-BASTIDE", "Bordeaux", 44.8443, -0.5530,
            {Pollutant.PM25: 9, Pollutant.PM10: 18, Pollutant.NO2: 20, Pollutant.O3: 55}),
    Station("TALENCE", "Talence", 44.8076, -0.5848,
            {Pollutant.PM25: 8, Pollutant.PM10: 16, Pollutant.NO2: 16, Pollutant.O3: 60}),
    Station("MERIGNAC", "Mérignac", 44.8333, -0.6450,
            {Pollutant.PM25: 10, Pollutant.PM10: 20, Pollutant.NO2: 22, Pollutant.O3: 50}),
    Station("PESSAC", "Pessac", 44.8060, -0.6310,
            {Pollutant.PM25: 7, Pollutant.PM10: 15, Pollutant.NO2: 14, Pollutant.O3: 62}),
]


def build_stations(n: int) -> list[Station]:
    """Renvoie les `n` premières stations du pool (n borné à la taille du pool)."""
    n = max(1, min(n, len(_STATION_POOL)))
    return _STATION_POOL[:n]
