# 🏥 Module 1 - RAG Médical de Base

## 🎯 Objectif

Système RAG médical fonctionnel avec API REST

## 🚀 Démarrage Rapide

```bash
# Installation
pip install -r requirements.txt

# Démarrage rapide
python quick_start.py

# API Server
cd api && python main.py

# Tests
python test_rag_system.py
```

## 📋 Composants

### API REST (Port 8000)
- `api/main.py` - Serveur FastAPI
- `api/start_api.py` - Script démarrage
- Endpoints: `/query`, `/health`, `/docs`

### RAG Pipeline
- `rag/langchain_rag.py` - Pipeline principal
- `rag/semantic_search.py` - Recherche sémantique
- `rag/context_retrieval.py` - Récupération contexte
- `rag/intelligent_chunker.py` - Découpage intelligent

### Embeddings
- `embeddings/embedding_manager.py` - Gestion embeddings
- `embeddings/chroma_manager.py` - Base vectorielle
- Support OpenAI, HuggingFace

### Base de Données
- `database/database.py` - Connexion DB
- `database/models.py` - Modèles données
- Support PostgreSQL, SQLite

### Collection Données
- `data_collection/` - Collecteurs automatisés
- Sources: PubMed, WHO, CDC
- Traduction multilingue
- Validation qualité

## 🔧 Configuration

```bash
# Variables d'environnement
OPENAI_API_KEY=your_key
CHROMA_PERSIST_DIRECTORY=./chroma_db
DATABASE_URL=postgresql://...
API_HOST=0.0.0.0
API_PORT=8000
```

## 📊 Endpoints API

```bash
# Requête RAG
POST /query
{
  "query": "traitement paludisme enfant",
  "max_results": 5
}

# Santé API
GET /health

# Documentation
GET /docs
```

## 🧪 Tests

```bash
# Test complet
python test_rag_system.py

# Test API
cd api && python test_api.py

# Test connexions
cd scripts && python test_connections.py
```

## 📈 Performance

- **Latence:** < 2s
- **Précision:** > 80%
- **Sources:** 500+ documents
- **Langues:** FR, EN, ES

## 🏆 Fonctionnalités

✅ **RAG médical fonctionnel**
✅ **API REST complète**
✅ **Base vectorielle**
✅ **Collection automatisée**
✅ **Support multilingue**
✅ **Tests automatisés**