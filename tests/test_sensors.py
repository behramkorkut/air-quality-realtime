"""Tests du modèle de données et du simulateur de capteurs."""

from datetime import timezone

import pytest

from air_quality_realtime.common.models import Pollutant, SensorReading, WHO_THRESHOLDS
from air_quality_realtime.producer.sensors import build_stations


def test_build_stations_borne_le_nombre():
    # On ne peut pas demander plus de stations que le pool n'en contient.
    assert len(build_stations(2)) == 2
    assert len(build_stations(999)) <= 5
    assert len(build_stations(0)) == 1  # au moins une station


def test_reading_est_valide_et_positif():
    station = build_stations(1)[0]
    reading = station.generate_reading(spike_probability=0.0)

    assert isinstance(reading, SensorReading)
    # Toutes les concentrations sont positives ou nulles.
    for value in reading.pollutant_values().values():
        assert value >= 0
    # Le timestamp est en UTC.
    assert reading.timestamp.tzinfo == timezone.utc


def test_spike_garanti_depasse_un_seuil():
    # Avec spike_probability=1.0, au moins un polluant doit dépasser son seuil OMS
    # sur quelques tirages (le pic multiplie par 2 à 4 le niveau de base).
    station = build_stations(1)[0]
    depasse = False
    for _ in range(20):
        reading = station.generate_reading(spike_probability=1.0)
        values = reading.pollutant_values()
        if any(values[p] > WHO_THRESHOLDS[p] for p in Pollutant):
            depasse = True
            break
    assert depasse, "un pic devrait faire dépasser au moins un seuil"


def test_concentration_negative_rejetee():
    # Le contrat Pydantic interdit les valeurs négatives.
    with pytest.raises(ValueError):
        SensorReading(
            station_id="X", city="Y", latitude=0.0, longitude=0.0,
            timestamp="2026-01-01T00:00:00Z",
            pm25=-1, pm10=10, no2=10, o3=10,
        )
