"""Logique de détection d'alertes — pure, sans dépendance à Kafka.

Pour chaque (station, polluant), on maintient une fenêtre glissante des derniers
relevés et on compare leur MOYENNE au seuil OMS. Travailler sur la moyenne (et
non sur chaque valeur brute) lisse le bruit et évite d'alerter sur un pic isolé.

Le déclenchement est "edge-triggered" : on émet une alerte uniquement au moment
où l'on PASSE au-dessus du seuil, pas à chaque relevé suivant. L'alerte se
réarme une fois repassé sous le seuil. Cela évite de noyer l'utilisateur sous
des alertes répétées tant que la pollution reste élevée.
"""

from __future__ import annotations

from collections import defaultdict, deque

from air_quality_realtime.common.models import (
    WHO_THRESHOLDS,
    Alert,
    Pollutant,
    SensorReading,
)


class AlertDetector:
    def __init__(
        self,
        window_size: int = 5,
        thresholds: dict[Pollutant, float] | None = None,
    ) -> None:
        self.window_size = window_size
        self.thresholds = thresholds or WHO_THRESHOLDS
        # Fenêtre glissante des dernières valeurs, par (station, polluant).
        self._windows: dict[tuple[str, Pollutant], deque[float]] = defaultdict(
            lambda: deque(maxlen=window_size)
        )
        # (station, polluant) actuellement en état d'alerte (pour l'edge-trigger).
        self._in_alert: set[tuple[str, Pollutant]] = set()

    def process(self, reading: SensorReading) -> list[Alert]:
        """Met à jour les fenêtres et renvoie les NOUVELLES alertes déclenchées."""
        alerts: list[Alert] = []

        for pollutant, value in reading.pollutant_values().items():
            key = (reading.station_id, pollutant)
            window = self._windows[key]
            window.append(value)
            average = sum(window) / len(window)
            threshold = self.thresholds[pollutant]

            if average > threshold:
                if key not in self._in_alert:  # transition sous -> au-dessus
                    self._in_alert.add(key)
                    alerts.append(
                        Alert(
                            station_id=reading.station_id,
                            city=reading.city,
                            pollutant=pollutant,
                            average=round(average, 2),
                            threshold=threshold,
                            window_size=self.window_size,
                            exceedance_ratio=round(average / threshold, 2),
                            timestamp=reading.timestamp,
                        )
                    )
            else:
                self._in_alert.discard(key)  # repassé sous le seuil -> réarme

        return alerts
