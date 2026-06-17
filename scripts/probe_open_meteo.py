"""Sonde l'API Open-Meteo et affiche la réponse brute.

But : vérifier la structure réelle de la réponse (noms de champs, format de
date, unités) avant de s'appuyer dessus dans OpenMeteoSource.

Usage :
    uv run python scripts/probe_open_meteo.py
"""

import json

import httpx

URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
PARAMS = {
    "latitude": 44.8378,   # Bordeaux Centre
    "longitude": -0.5792,
    "current": "pm2_5,pm10,nitrogen_dioxide,ozone",
    "timezone": "GMT",
}

if __name__ == "__main__":
    resp = httpx.get(URL, params=PARAMS, timeout=10.0)
    resp.raise_for_status()
    print(f"HTTP {resp.status_code}\n")
    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
