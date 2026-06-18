# Image applicative unique, partagée par producer / processor / sink / dashboard.
# Basée sur l'image officielle uv (uv + Python 3.12 préinstallés).
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# UV_COMPILE_BYTECODE : compile les .pyc à l'install (démarrage plus rapide).
# UV_LINK_MODE=copy   : évite les avertissements de hardlink dans le conteneur.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# 1) Dépendances seules : cette couche reste en cache tant que pyproject.toml
#    et uv.lock ne changent pas (rebuilds bien plus rapides).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# 2) Code source, puis installation du paquet lui-même (crée les commandes
#    aq-producer / aq-processor / aq-sink dans le venv).
COPY . .
RUN uv sync --frozen --no-dev

# Le venv est dans /app/.venv : on l'ajoute au PATH pour appeler directement
# aq-producer, aq-processor, aq-sink, streamlit...
ENV PATH="/app/.venv/bin:$PATH"

# Pas de CMD : la commande est fournie par chaque service docker-compose.
