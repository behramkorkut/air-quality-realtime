"""Tests de la logique de détection d'alertes (AlertDetector)."""

from datetime import datetime, timezone

from air_quality_realtime.common.models import Pollutant
from air_quality_realtime.processor.detector import AlertDetector


def make_reading(no2: float):
    """Relevé de test : seul le NO2 varie (seuil OMS NO2 = 25 µg/m³)."""
    from air_quality_realtime.common.models import SensorReading

    return SensorReading(
        station_id="BDX-CENTRE",
        city="Bordeaux",
        latitude=44.8378,
        longitude=-0.5792,
        timestamp=datetime.now(timezone.utc),
        pm25=0,
        pm10=0,
        no2=no2,
        o3=0,
    )


def test_pas_alerte_sous_le_seuil():
    detector = AlertDetector(window_size=3)
    assert detector.process(make_reading(no2=10)) == []


def test_alerte_edge_triggered_pas_de_doublon():
    detector = AlertDetector(window_size=1)
    alerts = detector.process(make_reading(no2=50))
    assert len(alerts) == 1
    assert alerts[0].pollutant == Pollutant.NO2
    assert alerts[0].exceedance_ratio == 2.0  # 50 / 25
    # Toujours au-dessus : aucune nouvelle alerte (edge-triggered).
    assert detector.process(make_reading(no2=50)) == []


def test_realarme_apres_retour_sous_le_seuil():
    detector = AlertDetector(window_size=1)
    detector.process(make_reading(no2=50))  # alerte
    detector.process(make_reading(no2=5))   # repasse sous le seuil -> réarme
    alerts = detector.process(make_reading(no2=50))  # re-dépasse
    assert len(alerts) == 1


def test_moyenne_glissante_lisse_un_pic_isole():
    # Fenêtre de 4 : trois valeurs basses puis un pic. La moyenne reste sous
    # le seuil -> pas d'alerte (le lissage absorbe le pic isolé).
    detector = AlertDetector(window_size=4)
    for _ in range(3):
        assert detector.process(make_reading(no2=10)) == []
    # (10 + 10 + 10 + 60) / 4 = 22.5 < 25
    assert detector.process(make_reading(no2=60)) == []
