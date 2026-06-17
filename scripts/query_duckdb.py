"""Interroge l'entrepôt DuckDB pour vérifier le contenu chargé par le sink.

À lancer de préférence quand le sink est arrêté (DuckDB autorise un seul
processus en écriture sur le fichier).

Usage : uv run python scripts/query_duckdb.py
"""

import duckdb

from air_quality_realtime.common.config import settings


def main() -> None:
    con = duckdb.connect(settings.duckdb_path, read_only=True)

    n_readings = con.execute("SELECT count(*) FROM readings").fetchone()[0]
    n_alerts = con.execute("SELECT count(*) FROM alerts").fetchone()[0]
    print(f"readings : {n_readings}")
    print(f"alerts   : {n_alerts}\n")

    print("Dernières alertes :")
    rows = con.execute(
        """
        SELECT station_id, pollutant, average, threshold, exceedance_ratio, event_time
        FROM alerts
        ORDER BY event_time DESC
        LIMIT 5
        """
    ).fetchall()
    for r in rows:
        print(f"  {r[0]:<12} {r[1]:<5} moy={r[2]:<7} seuil={r[3]:<6} x{r[4]} @ {r[5]}")

    print("\nNombre d'alertes par polluant :")
    for pollutant, count in con.execute(
        "SELECT pollutant, count(*) FROM alerts GROUP BY pollutant ORDER BY 2 DESC"
    ).fetchall():
        print(f"  {pollutant:<5} : {count}")

    con.close()


if __name__ == "__main__":
    main()
