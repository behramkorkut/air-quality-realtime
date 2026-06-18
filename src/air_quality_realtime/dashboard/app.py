"""Dashboard Streamlit temps réel de la qualité de l'air à Bordeaux.

Lit l'entrepôt DuckDB (en read-only) alimenté par le sink, et se rafraîchit
automatiquement toutes les 5 s via st.fragment(run_every=...).

Lancement :
    uv run streamlit run src/air_quality_realtime/dashboard/app.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from air_quality_realtime.common.config import settings
from air_quality_realtime.common.models import WHO_THRESHOLDS, Pollutant
from air_quality_realtime.dashboard import queries

DB_PATH = settings.duckdb_path

st.set_page_config(page_title="Qualité de l'air — Bordeaux", page_icon="🌫️", layout="wide")
st.title("🌫️ Qualité de l'air à Bordeaux — temps réel")
st.caption(
    "Flux de capteurs → Redpanda → détection d'alertes → DuckDB. "
    f"Seuils OMS 2021 (µg/m³) : PM2.5={WHO_THRESHOLDS[Pollutant.PM25]}, "
    f"PM10={WHO_THRESHOLDS[Pollutant.PM10]}, NO₂={WHO_THRESHOLDS[Pollutant.NO2]}, "
    f"O₃={WHO_THRESHOLDS[Pollutant.O3]}."
)


def _alert_color(en_alerte: bool) -> list[int]:
    # Rouge si station en alerte récente, vert sinon (format [R, G, B, A]).
    return [220, 40, 40, 200] if en_alerte else [40, 160, 80, 160]


@st.fragment(run_every="5s")
def live_view() -> None:
    """Section rafraîchie automatiquement toutes les 5 secondes."""
    try:
        summary = queries.get_summary(DB_PATH)
        status = queries.get_station_status(DB_PATH)
        alerts = queries.get_recent_alerts(DB_PATH)
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Entrepôt indisponible (le sink écrit peut-être) : {exc}")
        return

    # --- Indicateurs clés ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Relevés ingérés", f"{summary['readings']:,}".replace(",", " "))
    c2.metric("Alertes totales", f"{summary['alerts']:,}".replace(",", " "))
    c3.metric("Stations en alerte", summary["stations_en_alerte"])
    c4.metric("Stations suivies", len(status))

    st.divider()
    left, right = st.columns([1, 1])

    # --- Carte des stations ---
    with left:
        st.subheader("Stations")
        if not status.empty:
            status = status.copy()
            status["color"] = status["en_alerte"].apply(_alert_color)
            status["size"] = 120
            st.map(status, latitude="latitude", longitude="longitude",
                   color="color", size="size")
        else:
            st.info("Aucune donnée encore. Lance le producer, le processor et le sink.")

    # --- Dernières alertes ---
    with right:
        st.subheader("Dernières alertes")
        if not alerts.empty:
            st.dataframe(alerts, hide_index=True, use_container_width=True)
        else:
            st.info("Aucune alerte récente.")


def trend_view() -> None:
    """Évolution des polluants pour une station (sélecteur)."""
    st.subheader("Évolution des polluants par station")
    stations = queries.get_station_ids(DB_PATH)
    if not stations:
        st.info("En attente de données.")
        return
    station = st.selectbox("Station", stations)
    series = queries.get_station_timeseries(DB_PATH, station)
    if series.empty:
        st.info("Pas de relevés pour cette station.")
        return
    st.line_chart(series)


live_view()
st.divider()
trend_view()
