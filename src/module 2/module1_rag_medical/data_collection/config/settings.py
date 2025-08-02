import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Dict, List, Optional

class DataCollectionSettings(BaseSettings):
    """Configuration pour la collecte de données médicales"""
    
    # Chemins du projet
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    DATA_ROOT: Path = PROJECT_ROOT / "data"
    RAW_DATA_PATH: Path = DATA_ROOT / "raw"
    PROCESSED_DATA_PATH: Path = DATA_ROOT / "processed"
    VALIDATED_DATA_PATH: Path = DATA_ROOT / "validated"
    FINAL_DATA_PATH: Path = DATA_ROOT / "final"
    
    # Configuration de collecte
    TARGET_DOCUMENTS: int = 200
    MAX_DOCUMENTS_PER_SOURCE: int = 50
    COLLECTION_TIMEOUT: int = 300  # 5 minutes par document
    RETRY_ATTEMPTS: int = 3
    DELAY_BETWEEN_REQUESTS: float = 1.0  # secondes
    
    # Sources de données médicales
    WHO_BASE_URL: str = "https://www.who.int"
    CDC_BASE_URL: str = "https://www.cdc.gov"
    PUBMED_BASE_URL: str = "https://pubmed.ncbi.nlm.nih.gov"
    MEDLINEPLUS_BASE_URL: str = "https://medlineplus.gov"
    CAMEROON_MOH_URL: str = "https://www.minsante.cm"
    
    # Configuration des langues
    PRIMARY_LANGUAGE: str = "fr"  # Français
    SECONDARY_LANGUAGES: List[str] = ["en", "es"]  # Anglais, Espagnol
    LOCAL_LANGUAGES: List[str] = ["fr", "en"]  # Langues locales Cameroun
    
    # Catégories médicales
    MEDICAL_CATEGORIES: List[str] = [
        "diagnostics",
        "traitements", 
        "medicaments",
        "prevention",
        "urgences",
        "pediatrie",
        "maladies_infectieuses",
        "maladies_chroniques",
        "sante_mentale",
        "nutrition"
    ]
    
    # Spécialités médicales prioritaires
    PRIORITY_SPECIALTIES: List[str] = [
        "Médecine Générale",
        "Pédiatrie", 
        "Cardiologie",
        "Maladies Infectieuses",
        "Urgences",
        "Gynécologie-Obstétrique",
        "Pneumologie",
        "Gastroentérologie",
        "Neurologie",
        "Psychiatrie"
    ]
    
    # Maladies courantes en Afrique/Cameroun
    COMMON_DISEASES: List[str] = [
        "Paludisme",
        "Tuberculose", 
        "VIH/SIDA",
        "Hypertension",
        "Diabète",
        "Diarrhée",
        "Pneumonie",
        "Malnutrition",
        "Anémie",
        "Méningite",
        "Fièvre typhoïde",
        "Hépatite B",
        "Dengue",
        "Choléra",
        "Onchocercose"
    ]
    
    # Configuration de traitement de texte
    MIN_DOCUMENT_LENGTH: int = 500  # caractères minimum
    MAX_DOCUMENT_LENGTH: int = 50000  # caractères maximum
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    
    # Configuration de validation
    MEDICAL_ACCURACY_THRESHOLD: float = 0.8
    SOURCE_RELIABILITY_THRESHOLD: float = 0.7
    CONTENT_FRESHNESS_DAYS: int = 365  # 1 an
    
    # Configuration de traduction
    TRANSLATION_SERVICE: str = "google"  # google, deepl, azure
    TRANSLATION_BATCH_SIZE: int = 10
    TRANSLATION_CACHE_ENABLED: bool = True
    
    # Headers pour web scraping
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    
    # Configuration base de données
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/medical_data_collection"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = str(PROJECT_ROOT / "logs" / "data_collection.log")
    
    # Sécurité et éthique
    RESPECT_ROBOTS_TXT: bool = True
    MAX_CONCURRENT_REQUESTS: int = 5
    RATE_LIMIT_ENABLED: bool = True
    
    # APIs externes (optionnel)
    GOOGLE_TRANSLATE_API_KEY: Optional[str] = None
    DEEPL_API_KEY: Optional[str] = None
    PUBMED_API_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Sources de données détaillées
MEDICAL_DATA_SOURCES = {
    "who": {
        "name": "World Health Organization",
        "base_url": "https://www.who.int",
        "endpoints": [
            "/health-topics",
            "/news-room/fact-sheets",
            "/publications",
            "/emergencies/disease-outbreak-news"
        ],
        "languages": ["en", "fr", "es"],
        "reliability_score": 0.95,
        "update_frequency": "daily",
        "content_types": ["fact-sheets", "guidelines", "reports"]
    },
    "cdc": {
        "name": "Centers for Disease Control and Prevention",
        "base_url": "https://www.cdc.gov",
        "endpoints": [
            "/diseases-conditions",
            "/healthyplaces",
            "/travel/page/travel-health",
            "/vaccines"
        ],
        "languages": ["en"],
        "reliability_score": 0.93,
        "update_frequency": "weekly",
        "content_types": ["guidelines", "fact-sheets", "recommendations"]
    },
    "pubmed": {
        "name": "PubMed/NCBI",
        "base_url": "https://pubmed.ncbi.nlm.nih.gov",
        "api_endpoint": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils",
        "languages": ["en"],
        "reliability_score": 0.90,
        "update_frequency": "daily",
        "content_types": ["research", "reviews", "case-studies"]
    },
    "medlineplus": {
        "name": "MedlinePlus",
        "base_url": "https://medlineplus.gov",
        "endpoints": [
            "/healthtopics.html",
            "/druginformation.html",
            "/encyclopedia.html"
        ],
        "languages": ["en", "es"],
        "reliability_score": 0.88,
        "update_frequency": "monthly",
        "content_types": ["patient-info", "drug-info", "encyclopedia"]
    },
    "cameroon_moh": {
        "name": "Ministère de la Santé Publique du Cameroun",
        "base_url": "https://www.minsante.cm",
        "endpoints": [
            "/site/fr/actualites",
            "/site/fr/programmes",
            "/site/fr/documentation"
        ],
        "languages": ["fr"],
        "reliability_score": 0.85,
        "update_frequency": "weekly",
        "content_types": ["local-guidelines", "programs", "statistics"]
    },
    "pasteur_cameroon": {
        "name": "Centre Pasteur du Cameroun",
        "base_url": "https://www.pasteur-yaounde.org",
        "endpoints": [
            "/recherche",
            "/sante-publique",
            "/formation"
        ],
        "languages": ["fr"],
        "reliability_score": 0.87,
        "update_frequency": "monthly",
        "content_types": ["research", "public-health", "training"]
    }
}

# Templates de fiches explicatives
EXPLANATORY_TEMPLATES = {
    "disease_overview": {
        "sections": [
            "Qu'est-ce que c'est ?",
            "Causes principales",
            "Symptômes à surveiller", 
            "Quand consulter ?",
            "Traitements disponibles",
            "Prévention",
            "Conseils pratiques"
        ],
        "target_audience": "grand_public",
        "language_level": "simple"
    },
    "treatment_guide": {
        "sections": [
            "Objectif du traitement",
            "Médicaments prescrits",
            "Posologie et durée",
            "Effets secondaires possibles",
            "Précautions à prendre",
            "Suivi médical",
            "Que faire en cas de problème ?"
        ],
        "target_audience": "patients",
        "language_level": "accessible"
    },
    "diagnostic_procedure": {
        "sections": [
            "Pourquoi cet examen ?",
            "Comment se déroule l'examen ?",
            "Préparation nécessaire",
            "Durée et déroulement",
            "Résultats attendus",
            "Risques et complications",
            "Après l'examen"
        ],
        "target_audience": "patients",
        "language_level": "informatif"
    }
}

# Configuration de validation médicale
VALIDATION_CRITERIA = {
    "source_reliability": {
        "official_medical_org": 1.0,
        "peer_reviewed": 0.9,
        "government_health": 0.85,
        "academic_institution": 0.8,
        "medical_journal": 0.85,
        "unknown_source": 0.3
    },
    "content_freshness": {
        "less_than_1_year": 1.0,
        "1_to_2_years": 0.9,
        "2_to_5_years": 0.7,
        "more_than_5_years": 0.5
    },
    "medical_accuracy_indicators": [
        "references_cited",
        "author_credentials",
        "peer_review_status",
        "institutional_affiliation",
        "publication_date",
        "content_consistency"
    ]
}

# Instance globale des paramètres
settings = DataCollectionSettings()

# Créer les répertoires nécessaires
for path in [settings.DATA_ROOT, settings.RAW_DATA_PATH, settings.PROCESSED_DATA_PATH, 
             settings.VALIDATED_DATA_PATH, settings.FINAL_DATA_PATH]:
    path.mkdir(parents=True, exist_ok=True)

# Créer le répertoire de logs
(settings.PROJECT_ROOT / "logs").mkdir(parents=True, exist_ok=True)