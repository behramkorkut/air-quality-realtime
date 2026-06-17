"""Modèles de données du pipeline.

Le `SensorReading` est le *contrat* de la donnée : tout ce qui circule sur
Redpanda respecte cette structure. Le valider avec Pydantic dès la production
garantit qu'aucune donnée malformée n'entre dans le pipeline (réflexe qualité).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Pollutant(str, Enum):
    """Polluants suivis. Hérite de str pour une sérialisation JSON naturelle."""

    PM25 = "pm25"
    PM10 = "pm10"
    NO2 = "no2"
    O3 = "o3"


# Seuils indicatifs OMS 2021 (en µg/m³). Ce sont des valeurs guides moyennées
# (24 h ou 8 h selon le polluant) ; on les utilise ici comme seuils instantanés
# pour le déclenchement d'alertes — simplification volontaire et documentée.
WHO_THRESHOLDS: dict[Pollutant, float] = {
    Pollutant.PM25: 15.0,
    Pollutant.PM10: 45.0,
    Pollutant.NO2: 25.0,
    Pollutant.O3: 100.0,
}


class SensorReading(BaseModel):
    """Un relevé émis par une station de mesure à un instant donné."""

    station_id: str
    city: str
    latitude: float
    longitude: float
    timestamp: datetime  # toujours en UTC
    pm25: float = Field(ge=0, description="Particules fines < 2.5 µm (µg/m³)")
    pm10: float = Field(ge=0, description="Particules < 10 µm (µg/m³)")
    no2: float = Field(ge=0, description="Dioxyde d'azote (µg/m³)")
    o3: float = Field(ge=0, description="Ozone (µg/m³)")

    def pollutant_values(self) -> dict[Pollutant, float]:
        """Renvoie les valeurs sous forme {Pollutant: valeur}, pratique pour
        comparer aux seuils côté processor."""
        return {
            Pollutant.PM25: self.pm25,
            Pollutant.PM10: self.pm10,
            Pollutant.NO2: self.no2,
            Pollutant.O3: self.o3,
        }
