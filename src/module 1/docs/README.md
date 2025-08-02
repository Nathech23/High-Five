# Système de Rappels - Hôpital Général de Douala

## Fonctionnalités

### Phase 1 - Base de données
- Gestion des types de rappels avec templates multilingues
- Planification de rappels avec préférences patients
- Support multicanal (SMS, email, appel, WhatsApp)
- Base de données PostgreSQL optimisée

### Phase 2 - Services externes
- Service Twilio (SMS + appels vocaux)
- Traduction automatique Google Translate
- Webhooks pour tracking de statut
- API REST Flask
- Tests de communication

## 🗄️ Modèles de Données

### 1. ReminderType (Types de Rappels)
- **Templates multilingues** (français, anglais, espagnol)
- Types prédéfinis: `appointment`, `medication`, `follow_up`
- Support de l'activation/désactivation

### 2. Patient (Patients)
- Informations personnelles complètes
- Contacts d'urgence
- Relations avec rappels et préférences

### 3. Reminder (Rappels)
- **12 champs de planification**:
  - `scheduled_date`, `scheduled_time`, `timezone`
  - `priority_level`, `status`, `retry_count`, `max_retries`
  - `last_attempt_at`, `sent_at`, `delivered_at`
  - `created_at`, `updated_at`
- Statuts: `pending`, `sent`, `delivered`, `failed`, `cancelled`
- Niveaux de priorité: 1-5

### 4. ContactPreference (Préférences de Contact)
- **Canaux de communication**: SMS, Email, Appel, WhatsApp
- **Préférences temporelles**: heures de contact préférées
- **Langue préférée**: français, anglais, espagnol
- **Jours à éviter**: configuration flexible

## 🔗 Relations

- `Patient` ↔ `Reminder` (1:N)
- `Patient` ↔ `ContactPreference` (1:1)
- `ReminderType` ↔ `Reminder` (1:N)

## 📊 Index de Performance

Index optimisés pour les requêtes de planification:
- `idx_reminders_scheduled_date`
- `idx_reminders_status`
- `idx_reminders_planning` (composé)
- `idx_patients_phone`
- Et plus...

## 🚀 Installation et Utilisation

### Phase 1 - Base de données

#### 1. Installation des dépendances
```bash
pip install -r requirements.txt
```

#### 2. Configuration PostgreSQL
```bash
# Installation automatique avec PostgreSQL
python setup_postgresql.py
```

#### 3. Exécution des tests
```bash
python test_models.py
```

#### 4. Configuration manuelle (optionnelle)
```bash
# Initialisation manuelle si nécessaire
python database.py
```

### Phase 2 - Services externes

#### 1. Configurer Twilio
```bash
# Configuration interactive
python setup_twilio.py

# Ou manuellement :
# - Créer un compte sur twilio.com
# - Obtenir Account SID, Auth Token, et numéro de téléphone
# - Mettre à jour le fichier .env
```

#### 2. Démarrer le serveur
```bash
python app.py
```

#### 3. Tester les services
```bash
# Test SMS simple
python test_sms_simple.py

# Tests complets
python test_communication.py
```

## 💡 Exemples d'Utilisation

### Créer un patient
```python
from src.models import Patient
from src.database import get_db_session

session = get_db_session()
patient = Patient(
    first_name="Marie",
    last_name="Kamga",
    phone_number="+237123456789",
    email="marie.kamga@email.com"
)
session.add(patient)
session.commit()
```

### Créer un rappel
```python
from src.models import Reminder
from datetime import date, time

reminder = Reminder(
    patient_id=patient.id,
    reminder_type_id=1,  # appointment
    title="Consultation cardiologie",
    scheduled_date=date(2025, 12, 25),
    scheduled_time=time(14, 30),
    priority_level=2
)
session.add(reminder)
session.commit()
```

### Configurer les préférences de contact
```python
from models import ContactPreference

preferences = ContactPreference(
    patient_id=patient.id,
    preferred_language="fr",
    sms_enabled=True,
    email_enabled=True,
    preferred_time_start=time(8, 0),
    preferred_time_end=time(18, 0)
)
session.add(preferences)
session.commit()
```

## 🌐 Support Multilingue

Templates de rappels disponibles en:
- **Français** (par défaut)
- **Anglais**
- **Espagnol**

Exemple de template:
```python
reminder_type = session.query(ReminderType).filter_by(name='appointment').first()
template_fr = reminder_type.get_template('fr')
template_en = reminder_type.get_template('en')
```

## 🔧 Configuration

### Base de données
- **Production**: PostgreSQL (configuré)
- **Serveur**: 192.168.1.101:5432
- **Base de données**: hospital_reminders
- **Utilisateur**: postgres

### Variables d'environnement
```bash
# Copiez .env.example vers .env et modifiez selon vos besoins
DB_HOST=192.168.1.101
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=12345
DB_NAME=hospital_reminders
```

## ✅ Tests

Les tests couvrent:
- Création des tables et données prédéfinies
- Relations entre modèles
- Fonctionnalités des templates multilingues
- Validation des contraintes
- Performance des index
