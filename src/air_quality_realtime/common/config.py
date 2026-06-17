"""Configuration centralisée du projet.

On utilise pydantic-settings : les valeurs sont lues depuis les variables
d'environnement (et le fichier .env en développement local). Avantage :
- typage et validation automatiques (un port reste un entier, etc.) ;
- un seul endroit pour toute la config, importable partout ;
- les secrets ne sont jamais codés en dur dans le code.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore les variables d'env non déclarées ici
    )

    # --- Redpanda / Kafka ---
    # 127.0.0.1 (et non "localhost") pour forcer l'IPv4 et éviter l'avertissement
    # de connexion IPv6 (::1) que librdkafka émet sinon au démarrage.
    kafka_bootstrap_servers: str = "127.0.0.1:19092"
    topic_raw: str = "air-quality-raw"
    topic_alerts: str = "air-quality-alerts"

    # --- Producer ---
    source: str = "simulated"  # "simulated" (haute fréquence) ou "openmeteo" (réel)
    producer_interval_seconds: float = 2.0
    producer_n_stations: int = 5

    # --- Snowflake (rempli à l'étape sink) ---
    snowflake_account: str = ""
    snowflake_user: str = ""
    snowflake_password: str = ""
    snowflake_warehouse: str = ""
    snowflake_database: str = ""
    snowflake_schema: str = ""


# Instance unique importée par les autres modules : `from ...common.config import settings`
settings = Settings()
