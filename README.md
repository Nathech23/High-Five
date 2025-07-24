Service microservice pour les explications médicales diagnostiques et thérapeutiques.
Fait partie du Track 2 du Datathon DGH - "Large Language Model for Enhanced Patient Education and Support".

## 🎯 Objectifs

Ce service transforme les diagnostics et prescriptions médicales en explications simples et accessibles pour les patients, en respectant les contraintes de sécurité médicale.

## 🏗️ Architecture

```
Service LLM (Port 8004)
├── Gestion des modèles LLM (Mistral/LLaMA via Ollama)
├── Validation de sécurité médicale
├── Cache Redis pour performances
├── Métriques Prometheus
└── APIs RESTful documentées
```

## 🚀 Fonctionnalités

### Explications Diagnostiques
- Transformation des diagnostics médicaux en langage simple
- Adaptation au niveau d'éducation du patient
- Support multilingue (FR, EN, langues locales)
- Détection automatique d'urgences

### Explications Thérapeutiques
- Explication des traitements et médicaments
- Instructions de prise claires
- Effets attendus et secondaires
- Recommandations de style de vie

### Sécurité Médicale
- Validation automatique des réponses
- Filtres anti-prescription
- Avertissements médicaux obligatoires
- Détection de patterns dangereux

## 🛠️ Installation

### Prérequis
- Python 3.11+
- Docker & Docker Compose
- Ollama avec modèle Mistral-7B
- Redis

### Démarrage rapide

```bash
# Clone et setup
git clone https://github.com/Nathech23/High-Five.git
cd service_llm

# Variables d'environnement
cp .env.example .env
# Éditez .env avec vos configurations

# Démarrage avec Docker
docker-compose -f docker/docker-compose.yml up -d

# Ou installation locale
pip install -r requirements.txt
python -m app.main
```

## 📡 API Endpoints

### Explications Diagnostiques
```http
POST /api/v1/diagnostic/explain
Content-Type: application/json

{
  "diagnostic_text": "Hypertension artérielle modérée",
  "patient_context": {
    "age_group": "senior",
    "education_level": "basic"
  },
  "language": "fr",
  "explanation_level": "simple"
}
```

### Explications Thérapeutiques
```http
POST /api/v1/therapeutic/explain
Content-Type: application/json

{
  "treatment_text": "Prendre 1 comprimé matin et soir",
  "medication_name": "Lisinopril 10mg",
  "language": "fr",
  "include_side_effects": true
}
```

### Santé du Service
```http
GET /api/v1/health/
```

## 🔧 Configuration

### Variables d'environnement clés

```env
# LLM Configuration
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=mistral:7b
LLM_TEMPERATURE=0.3

# Redis Cache
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600

# Sécurité
SECRET_KEY=your-secret-key
ENABLE_SAFETY_FILTERS=true
```

## 📊 Monitoring

### Métriques Prometheus
- `diagnostic_explanations_total` - Nombre d'explications diagnostiques
- `therapeutic_explanations_total` - Nombre d'explications thérapeutiques  
- `llm_response_time_seconds` - Temps de réponse LLM
- `llm_confidence_scores` - Distribution des scores de confiance

### Logs Structurés
```json
{
  "timestamp": "2025-01-23T10:30:00Z",
  "level": "info",
  "event": "Diagnostic explanation generated",
  "response_id": "uuid-here",
  "language": "fr",
  "confidence": 0.85
}
```

## 🧪 Tests

```bash
# Tests unitaires
pytest tests/

# Test de charge
locust -f tests/load_test.py --host=http://localhost:8004
```

## 🛡️ Sécurité Médicale

### Validations Automatiques
- ❌ Pas de prescription de médicaments
- ❌ Pas de modification de diagnostics
- ❌ Pas d'arrêt de traitements
- ✅ Avertissements médicaux obligatoires
- ✅ Renvoi systématique vers professionnels

### Patterns Détectés
- Modifications de dosage
- Diagnostics directs
- Conseils d'arrêt de traitement
- Prescriptions non autorisées

## 🌍 Support Multilingue

- **Français** - Langue principale
- **Anglais** - Support complet
- **Langues locales** - Douala, Bassa, Ewondo (en développement)

## 📈 Performance

- **Temps de réponse** < 3 secondes
- **Cache hit ratio** > 70%
- **Disponibilité** > 99.5%
- **Précision médicale** > 90%

## 🔄 Intégration

### Avec autres services
- **API Chatbot (8003)** - Orchestration conversations
- **Service RAG (8005)** - Récupération connaissances
- **Frontend React (3001)** - Interface utilisateur

### Formats d'échange
```json
{
  "explanation": "Votre tension artérielle est un peu élevée...",
  "confidence_score": 0.85,
  "medical_disclaimer": "⚠️ Important: Cette explication...",
  "suggested_questions": ["Que dois-je éviter?", "..."],
  "urgency_level": "normal"
}
```

## 🚨 Gestion d'Urgences

Détection automatique de situations urgentes:
- Mots-clés d'urgence dans les questions
- Réponses standardisées de redirection
- Escalade vers services d'urgence (15)

## 📝 Développement

### Structure du code
```
app/
├── core/          # Configuration, LLM Manager
├── models/        # Modèles Pydantic
├── services/      # Logique métier
├── api/           # Endpoints FastAPI
├── prompts/       # Templates de prompts
└── utils/         # Utilitaires (cache, métriques)
```

### Ajout de nouvelles fonctionnalités
1. Créer les modèles dans `models/`
2. Implémenter la logique dans `services/`
3. Ajouter les endpoints dans `api/`
4. Créer les prompts dans `prompts/`
5. Ajouter les tests dans `tests/`

---

