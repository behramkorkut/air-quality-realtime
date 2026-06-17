"""Pipeline temps réel de surveillance de la qualité de l'air.

Sous-paquets :
- producer  : simulateur de capteurs qui émet des relevés vers Redpanda
- processor : consumer qui détecte les dépassements de seuils et émet des alertes
- sink      : chargement des données vers Snowflake
- common    : configuration et utilitaires partagés
"""

__version__ = "0.1.0"
