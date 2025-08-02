# Dockerfile pour le service ML de prédiction des stocks de sang
FROM python:3.9-slim

# Métadonnées
LABEL maintainer="Hackathon Hôpital Général Douala"
LABEL description="Service ML pour la prédiction des stocks de sang"
LABEL version="1.0.0"

# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV MODEL_PATH=/app/models
ENV DATA_PATH=/app/data
ENV PORT=8000

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Créer un utilisateur non-root
RUN useradd --create-home --shell /bin/bash mluser

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers de requirements
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY src/ ./src/
COPY models/ ./models/
COPY data/ ./data/

# Créer les répertoires nécessaires
RUN mkdir -p /app/logs /app/cache /app/mlruns

# Changer la propriété des fichiers
RUN chown -R mluser:mluser /app

# Passer à l'utilisateur non-root
USER mluser

# Exposer le port
EXPOSE $PORT

# Healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1

# Script de démarrage
COPY --chown=mluser:mluser docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Commande par défaut
CMD ["/app/docker-entrypoint.sh"]