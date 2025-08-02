# API d'Analyse de Feedback Patient (Analysis Engine)

Ce service est le moteur d'analyse NLP du projet "Patient Feedback and Reminder Management System". Sa responsabilité principale est de recevoir un feedback patient (texte), de l'analyser pour en extraire le sentiment, les thèmes et le caractère d'urgence, puis de retourner une analyse structurée.



## 1. Stack Technique

* **Langage** : Python 3.9+
* **Framework API** : FastAPI
* **Dépendances Principales** :
   * `uvicorn` : Serveur ASGI pour FastAPI
   * `spacy` : Traitement NLP de base (tokenisation, etc.)
      * Modèle : `en_core_web_sm`
   * `transformers` : Accès aux modèles Hugging Face
   * `torch` : Backend pour les modèles transformers
   * `pandas` : Manipulation des données pour les scripts d'analyse

## 2. Structure du Projet

```
analysis-engine/
├── app/
│   ├── __init__.py
│   ├── main.py             # Point d'entrée de l'API (endpoints FastAPI)
│   ├── nlp_analyzer.py     # Classe principale pour l'analyse NLP
│   └── data/
│       ├── patient_feedback.csv    # Données brutes
│       ├── patient_feedback_clean.csv # Données nettoyées
│       └── manual_labels.py        # Dictionnaires pour les règles manuelles
│
├── scripts/                # Scripts utilitaires (pas servis par l'API)
│   ├── data_explorer.py    # Script pour analyser le dataset initial
│   └── rating_analysis.py  # Script pour visualiser la distribution des notes
│
├── tests/
│   └── test_api.py         # Script de test basique pour l'endpoint
│
├── .env.example            # Fichier d'exemple pour les variables d'environnement
├── Dockerfile              # Instructions pour builder l'image Docker du service
└── requirements.txt        # Liste des dépendances Python
```

## 3. Configuration

Le service peut être configuré via des variables d'environnement.

* Copiez le fichier d'exemple :

```bash
cp .env.example .env
```

* Remplissez les valeurs dans le fichier `.env`. 

## 4. Endpoints de l'API

### POST /analyze

Analyse un seul feedback textuel et retourne une analyse complète.

* **Request Body** :

```json
{
  "text": "The doctor was very helpful and kind.",
  "method": "hybrid"
}
```

   * `text` (str, requis) : Le feedback du patient.
   * `method` (str, optionnel) : La méthode d'analyse à forcer. Valeurs possibles :
      * `hybrid` : Utilise les labels manuels si possible, sinon le modèle ML.
      * `huggingface` : Force l'utilisation du modèle Hugging Face.
      * `fallback` : Force l'utilisation du système de règles basique.
   * Par défaut : `hybrid`.

* **Success Response (200 OK)** :

```json
{
    "original_text": "The doctor was very helpful and kind.",
    "language": "en",
    "sentiment": "positive",
    "predicted_rating": 5,
    "themes": ["Staff Interaction"],
    "keywords": ["doctor", "helpful", "kind"],
    "is_urgent": false,
    "method_used": "huggingface"
}
```

## 5. Installation et Lancement

1. Installez les dépendances :

```bash
pip install -r requirements.txt
```

2. Téléchargez les modèles spaCy :

```bash
python -m spacy download en_core_web_sm
```

3. Lancez le serveur FastAPI :

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

   * Le service sera accessible sur `http://localhost:8001`.
   * L'interface de documentation interactive (Swagger UI) est disponible sur `http://localhost:8001/docs`.

## 6. Lancer les Tests

Pour vérifier que l'API fonctionne comme attendu, vous pouvez lancer les scripts de test.

1. Assurez-vous que le serveur FastAPI est en cours d'exécution dans un terminal.
2. Ouvrez un second terminal et exécutez :

```bash
python tests/test_api.py
```

   * Ce script enverra une requête à votre API locale et affichera la réponse.

**Note** : Ce README est basé sur la version 0.1 du service. Des mises à jour seront apportées au fur et à mesure de l'avancement du projet.