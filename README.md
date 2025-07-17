# Système de Rappels Médicaux

---

## 📋 Vue d'ensemble

Système complet de rappels médicaux automatisés avec support multilingue (Français, Anglais, Espagnol) et intégration Twilio pour SMS et appels vocaux.

## 🏗️ Structure du Projet

```
hackaton_HopitalGeneralDouala/
├── src/                          # Code source principal
│   ├── models/                   # Modèles de données
│   │   ├── models.py            # Modèles SQLAlchemy
│   │   └── reminder_models.py   # Modèles Pydantic API
│   ├── services/                # Services métier
│   │   ├── communication_service.py  # Service Twilio
│   │   ├── reminder_service.py      # Logique métier rappels
│   │   ├── redis_service.py         # Service Redis
│   │   ├── templates_manager.py     # Templates multilingues
│   │   ├── twiml_service.py         # Service TwiML
│   │   └── scheduler.py             # Planificateur
│   ├── api/                     # API REST
│   │   ├── reminder_api.py      # API FastAPI
│   │   └── start_api.py         # Point d'entrée API
│   ├── config/                  # Configuration
│   │   ├── config.py           # Configuration générale
│   │   └── config_api.py       # Configuration API
│   └── database/                # Base de données
│       ├── database.py         # Gestionnaire PostgreSQL
│       ├── database_schema.sql # Schéma de base
│       ├── reminder_schema.sql # Schéma optimisé
│       └── postgresql_config.sql # Configuration PostgreSQL
├── docs/                        # Documentation
│   ├── README.md               # Documentation principale
│   ├── DOCUMENTATION_COMPLETE.md # Documentation technique
│   └── etapes.md               # Historique des phases
├── scripts/                     # Scripts d'installation
│   ├── setup_postgresql.py    # Installation PostgreSQL
│   └── setup_twilio.py        # Configuration Twilio
├── tests/                       # Tests (exclus du déploiement)
│   ├── test_*.py              # Tests unitaires
│   └── test_*.json            # Résultats de tests
├── .env.example                # Exemple de configuration
├── .gitignore                  # Exclusions Git
├── requirements.txt            # Dépendances de base
├── requirements_api.txt        # Dépendances API
└── app.py                      # Application principale
```

## 🚀 Démarrage Rapide

### 1. Installation

```bash
# Cloner le projet
git clone <repository-url>
cd hackaton_HopitalGeneralDouala

# Créer l'environnement virtuel
python -m venv .venv
.venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements_api.txt
```

### 2. Configuration

```bash
# Copier le fichier de configuration
cp .env.example .env

# Configurer PostgreSQL
python scripts/setup_postgresql.py

# Configurer Twilio
python scripts/setup_twilio.py
```

### 3. Lancement

```bash
# Démarrer l'API
python src/api/start_api.py

# L'API sera disponible sur http://localhost:8000
# Documentation: http://localhost:8000/docs
```

## 📚 Documentation

- **[Documentation Complète](docs/DOCUMENTATION_COMPLETE.md)** - Guide technique détaillé
- **[Historique des Phases](docs/etapes.md)** - Développement par phases
- **[Documentation API](docs/README.md)** - Guide d'utilisation de l'API

## 🔧 Configuration Requise

### Services Externes
- **PostgreSQL** - Base de données principale
- **Redis** - Files d'attente et cache (optionnel)
- **Twilio** - SMS et appels vocaux

### Variables d'Environnement

```env
# Base de données
DATABASE_URL=postgresql://user:password@localhost:5432/reminders_db

# Twilio
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# Redis (optionnel)
REDIS_HOST=localhost
REDIS_PORT=6379

# API
API_HOST=0.0.0.0
API_PORT=8000
```

## 🌟 Fonctionnalités

### ✅ Implémentées
- 🏥 Gestion complète des patients et rappels
- 🌍 Templates multilingues (FR, EN, ES)
- 📱 Envoi SMS via Twilio
- 📞 Appels vocaux automatisés
- 🔄 Planification automatique avec retry
- 📊 API REST complète avec documentation
- 🔍 Monitoring et métriques
- 📋 Webhooks pour suivi des statuts

### 🎯 Types de Rappels
- **Rendez-vous médicaux** - Confirmations et rappels
- **Prise de médicaments** - Rappels de traitement
- **Suivi médical** - Consultations de contrôle
- **Urgences médicales** - Notifications prioritaires
- **Conseils santé** - Messages préventifs

## 🔒 Sécurité

- Variables d'environnement pour les secrets
- Validation des données d'entrée
- Gestion sécurisée des webhooks Twilio
- Logs structurés sans exposition de données sensibles
