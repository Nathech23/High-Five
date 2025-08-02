# 🩸 Blood Bank Optimization Service

Service d'optimisation intelligent pour banques de sang avec algorithmes avancés et recommandations LLM.

## 🚀 Features

- Algorithmes EOQ modifiés pour produits périssables
- Optimisation multi-contraintes (coût, gaspillage, service)
- Allocation FEFO avec gestion d'urgences  
- Recommandations LLM intelligentes
- API FastAPI production-ready
- CI/CD automatique Google Cloud Run

## 🏃‍♂️ Quick Start

```bash
pip install -r requirements.txt
uvicorn src.api.main:app --reload
```

## 📚 Documentation
API Documentation: `/docs`
Health Check: `/health` 
Metrics: `/metrics`