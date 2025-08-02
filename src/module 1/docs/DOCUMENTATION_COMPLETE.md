# 🏥 Système de Rappels Médicaux

## 📋 Table des Matières
1. [Vue d'ensemble](#vue-densemble)
2. [Installation et Configuration](#installation-et-configuration)
3. [Configuration Twilio](#configuration-twilio)
4. [Tests et Validation](#tests-et-validation)
5. [Déploiement Production](#déploiement-production)
6. [API et Endpoints](#api-et-endpoints)
7. [Dépannage](#dépannage)
8. [Améliorations Futures](#améliorations-futures)

## 🎯 Vue d'ensemble

### Fonctionnalités
- **SMS multilingues** : Français, Anglais, Espagnol
- **Appels vocaux automatisés** avec TwiML
- **Traduction automatique** des messages
- **Webhooks Twilio** pour suivi des statuts
- **Base de données** SQLite/PostgreSQL
- **API REST** pour intégration


## 🚀 Installation et Configuration

### Prérequis
- Python 3.8+
- Compte Twilio
- Ngrok (pour webhooks)

### Installation
```bash
# Cloner le projet
git clone <repository>
cd hackaton_HopitalGeneralDouala

# Installer les dépendances
pip install -r requirements.txt

# Copier la configuration
cp .env.example .env
```

### Configuration Environnement
Éditer le fichier `.env` :
```env
# Configuration Twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+1xxxxxxxxxx

# Configuration Application
BASE_URL=https://votre-ngrok-url.ngrok-free.app
TWILIO_WEBHOOK_URL=https://votre-ngrok-url.ngrok-free.app
TEST_PHONE_NUMBER=+237xxxxxxxxx

# Base de données
DATABASE_URL=sqlite:///hospital.db

# Sécurité
SECRET_KEY=votre-clé-secrète-très-longue
```

## 📞 Configuration Twilio

### Étape 1 : Créer un Compte Twilio
1. Aller sur https://www.twilio.com
2. Créer un compte gratuit
3. Vérifier votre numéro de téléphone

### Étape 2 : Obtenir les Identifiants
1. **Console Twilio** : https://console.twilio.com
2. Copier :
   - **Account SID**
   - **Auth Token**

### Étape 3 : Acheter un Numéro Twilio
1. **Phone Numbers > Manage > Buy a number**
2. Choisir un numéro (recommandé : USA pour tests)
3. Activer SMS et Voice

### Étape 4 : Configuration Automatique
```bash
# Script interactif de configuration
python setup_twilio.py
```

### Étape 5 : Permissions Géographiques
Pour appeler le Cameroun :
1. Aller sur : https://www.twilio.com/console/voice/calls/geo-permissions/low-risk
2. Activer "Cameroon (CM)"
3. Sauvegarder

### Étape 6 : Configurer Webhooks
Dans la Console Twilio > Phone Numbers :
- **SMS Webhook** : `https://votre-url.ngrok-free.app/webhook/sms`
- **Voice Webhook** : `https://votre-url.ngrok-free.app/webhook/voice`

## 🧪 Tests et Validation

### Test Rapide
```bash
# Test SMS simple
python test_sms_simple.py

# Tests complets du système
python tests_complets.py
```

### Tests Manuels

#### 1. Test SMS
```bash
curl -X POST http://localhost:5000/test/communication \
  -H "Content-Type: application/json" \
  -d '{
    "phone":"+237XXXXXXXX",
    "language":"fr",
    "message":"Test de rappel médical"
  }'
```

#### 2. Test TwiML
```bash
curl "http://localhost:5000/twiml/voice?message=Bonjour&lang=fr"
```

### Validation Système
```bash
# Validation complète
python validate_system.py
```

**Résultat attendu :** 8/8 tests réussis (100%)

## 🌐 Déploiement Production

### Étape 1 : Configurer Ngrok
```bash
# Installer ngrok
# Démarrer le tunnel
ngrok http 5000

# Copier l'URL https://xxxxxxxx.ngrok-free.app
```

### Étape 2 : Mettre à Jour la Configuration
```bash
# Mettre à jour .env avec l'URL ngrok
BASE_URL=https://xxxxxxxx.ngrok-free.app
TWILIO_WEBHOOK_URL=https://xxxxxxxx.ngrok-free.app
```

### Étape 3 : Démarrer le Serveur
```bash
# Démarrage production
python app.py

# Le serveur sera accessible :
# - Local: http://localhost:5000
# - Public: https://xxxxxxxx.ngrok-free.app
```

### Étape 4 : Tests de Production
```bash
# Validation finale
python tests_complets.py

# Test SMS réel
python test_sms_simple.py
```

## 🔌 API et Endpoints

### Endpoints Principaux

#### Health Check
```
GET /
Réponse : {"status": "ok", "service": "Hospital Reminder System"}
```

#### Test Communication
```
POST /test/communication
Body: {
  "phone": "+237XXXXXXXX",
  "language": "fr",
  "message": "Votre message"
}
```

#### TwiML Voice
```
GET /twiml/voice?message=Votre message&lang=fr
Réponse : XML TwiML pour Twilio
```

#### Webhooks
```
POST /webhook/sms     # Statut SMS
POST /webhook/voice   # Statut appels
```

### Utilisation Programmatique

```python
from communication_service import CommunicationManager

# Initialiser le service
comm = CommunicationManager()

# Envoyer SMS
result = comm.send_reminder_sms(
    phone="+237XXXXXXXX",
    message="Rappel: RDV demain 14h",
    language="fr"
)

# Envoyer appel vocal
result = comm.send_reminder_call(
    phone="+237XXXXXXXX",
    message="Rappel: RDV demain 14h",
    language="fr"
)
```

## 🔧 Dépannage

### Problèmes Courants

#### 1. SMS non reçu
**Causes possibles :**
- Numéro Twilio invalide
- Crédit Twilio insuffisant
- Numéro destinataire non vérifié (compte trial)

**Solutions :**
```bash
# Vérifier la configuration
python setup_twilio.py

# Tester avec un numéro vérifié
python test_sms_simple.py
```

#### 2. Appel vocal échoué
**Causes possibles :**
- Permissions géographiques non activées
- URL TwiML inaccessible
- Ngrok non configuré

**Solutions :**
1. Activer permissions Cameroun dans Console Twilio
2. Vérifier que ngrok fonctionne
3. Tester l'URL TwiML manuellement

#### 3. Erreur 405 sur endpoints
**Cause :** Mauvaise méthode HTTP
**Solution :** Utiliser POST pour `/test/communication`

#### 4. Erreur de traduction
**Cause :** Service Google Translate inaccessible
**Solution :** Vérifier la connexion internet

### Logs et Monitoring

```bash
# Voir les logs en temps réel
tail -f logs/app.log

# Logs Twilio
# Console: https://console.twilio.com/us1/monitor/logs
```

### Codes d'Erreur Twilio

| Code | Description | Solution |
|------|-------------|----------|
| 21211 | Numéro invalide | Vérifier format +237XXXXXXXX |
| 21215 | Permissions géographiques | Activer pays dans Console |
| 20429 | Rate limit | Attendre ou upgrader compte |
| 21205 | URL invalide | Vérifier URL ngrok |

## 📞 Support

### Ressources Twilio
- **Console** : https://console.twilio.com
- **Documentation** : https://www.twilio.com/docs
- **Support** : https://support.twilio.com

### Ressources Projet
- **Tests** : `python tests_complets.py`
- **Configuration** : `python setup_twilio.py`
- **Validation** : `python validate_system.py`
