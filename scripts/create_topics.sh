#!/usr/bin/env bash
# Crée les topics du pipeline avec 3 partitions chacun.
# À lancer une fois Redpanda démarré (docker compose up -d).
#
# Usage : ./scripts/create_topics.sh
set -euo pipefail

COMPOSE_FILE="docker/docker-compose.yml"
BROKER="redpanda-0"

# Détecte la commande Compose disponible : V2 ("docker compose") ou V1 ("docker-compose").
if docker compose version >/dev/null 2>&1; then
  DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  DC="docker-compose"
else
  echo "Ni 'docker compose' ni 'docker-compose' n'est disponible." >&2
  exit 1
fi
echo "Commande Compose détectée : $DC"

# rpk est le CLI de Redpanda, embarqué dans l'image du broker.
# --partitions 3 : on découpe chaque topic en 3 pour permettre le parallélisme
#                  des consumers (et illustrer le partitionnement par clé).
$DC -f "$COMPOSE_FILE" exec "$BROKER" \
  rpk topic create air-quality-raw --partitions 3

$DC -f "$COMPOSE_FILE" exec "$BROKER" \
  rpk topic create air-quality-alerts --partitions 3

echo "--- Topics existants ---"
$DC -f "$COMPOSE_FILE" exec "$BROKER" rpk topic list
