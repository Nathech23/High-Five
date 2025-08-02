#!/usr/bin/env python3
"""
Script de configuration des bases de données pour le module RAG médical
Configure PostgreSQL et Chroma DB avec les tables et collections nécessaires
"""

import sys
import logging
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import settings
from database.database import db_manager, init_database
from embeddings.chroma_manager import chroma_manager
from embeddings.embedding_manager import embedding_manager

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(settings.LOG_FILE)
    ]
)

logger = logging.getLogger(__name__)

def setup_postgresql():
    """Configure la base de données PostgreSQL"""
    logger.info("=== Configuration PostgreSQL ===")
    
    try:
        # Tester la connexion
        logger.info("Testing PostgreSQL connection...")
        if not db_manager.test_connection():
            logger.error("Failed to connect to PostgreSQL")
            return False
        
        # Initialiser la base de données
        logger.info("Initializing database schema...")
        init_database()
        
        # Vérifier les tables créées
        table_info = db_manager.get_table_info()
        logger.info(f"Created {len(table_info)} tables:")
        for table_name, info in table_info.items():
            logger.info(f"  - {table_name}: {len(info['columns'])} columns")
        
        logger.info("PostgreSQL setup completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"PostgreSQL setup failed: {e}")
        return False

def setup_chroma():
    """Configure la base de données vectorielle Chroma"""
    logger.info("=== Configuration Chroma DB ===")
    
    try:
        # Tester la connexion
        logger.info("Testing Chroma connection...")
        if not chroma_manager.test_connection():
            logger.error("Failed to connect to Chroma")
            return False
        
        # Obtenir les statistiques de la collection
        stats = chroma_manager.get_collection_stats()
        logger.info(f"Chroma collection stats:")
        logger.info(f"  - Collection: {stats.get('collection_name')}")
        logger.info(f"  - Documents: {stats.get('total_documents', 0)}")
        logger.info(f"  - Model: {stats.get('embedding_model')}")
        
        logger.info("Chroma setup completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Chroma setup failed: {e}")
        return False

def setup_embedding_model():
    """Configure et teste le modèle d'embedding"""
    logger.info("=== Configuration Embedding Model ===")
    
    try:
        # Obtenir les informations du modèle
        model_info = embedding_manager.get_model_info()
        logger.info(f"Embedding model info:")
        for key, value in model_info.items():
            logger.info(f"  - {key}: {value}")
        
        # Test d'encodage
        logger.info("Testing text encoding...")
        test_texts = [
            "Diagnostic de l'hypertension artérielle",
            "Traitement de la pneumonie communautaire",
            "Protocole de réanimation cardiaque"
        ]
        
        embeddings = embedding_manager.encode_medical_text(test_texts)
        logger.info(f"Successfully encoded {len(test_texts)} test texts")
        logger.info(f"Embedding shape: {embeddings.shape}")
        
        # Benchmark rapide
        benchmark = embedding_manager.benchmark_encoding(test_texts)
        logger.info(f"Encoding performance: {benchmark.get('texts_per_second', 0):.2f} texts/second")
        
        logger.info("Embedding model setup completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Embedding model setup failed: {e}")
        return False

def create_sample_data():
    """Crée des données d'exemple pour tester le système"""
    logger.info("=== Création de données d'exemple ===")
    
    try:
        from database.models import MedicalDocument, MedicalSpecialty
        
        # Données d'exemple
        sample_documents = [
            {
                "title": "Protocole de prise en charge de l'hypertension artérielle",
                "content": """
                L'hypertension artérielle (HTA) est définie par une pression artérielle systolique ≥ 140 mmHg 
                et/ou une pression artérielle diastolique ≥ 90 mmHg, mesurée au cabinet médical.
                
                Diagnostic:
                - Mesure de la pression artérielle au cabinet
                - Confirmation par MAPA ou automesure
                - Bilan initial: créatinine, ionogramme, glycémie, lipides
                
                Traitement:
                - Mesures hygiéno-diététiques en première intention
                - Monothérapie si PA > 140/90 mmHg après 3 mois
                - Bithérapie si PA > 160/100 mmHg d'emblée
                """,
                "document_type": "protocol",
                "specialty": "Cardiologie",
                "medical_level": "intermediate",
                "target_audience": "doctors",
                "keywords": ["hypertension", "pression artérielle", "diagnostic", "traitement"]
            },
            {
                "title": "Guide de prise en charge de la pneumonie communautaire",
                "content": """
                La pneumonie communautaire est une infection aiguë du parenchyme pulmonaire 
                contractée en dehors de l'hôpital.
                
                Diagnostic:
                - Signes cliniques: fièvre, toux, dyspnée, douleur thoracique
                - Radiographie thoracique: opacités alvéolaires
                - Biologie: hyperleucocytose, CRP élevée
                
                Traitement:
                - Amoxicilline 1g x3/j per os en première intention
                - Hospitalisation si critères de gravité
                - Durée: 7-10 jours selon évolution
                """,
                "document_type": "guideline",
                "specialty": "Pneumologie",
                "medical_level": "basic",
                "target_audience": "doctors",
                "keywords": ["pneumonie", "infection", "antibiotique", "radiographie"]
            }
        ]
        
        # Ajouter les documents à PostgreSQL
        with db_manager.get_session() as session:
            for doc_data in sample_documents:
                # Vérifier si le document existe déjà
                existing = session.query(MedicalDocument).filter_by(
                    title=doc_data["title"]
                ).first()
                
                if not existing:
                    doc = MedicalDocument(**doc_data)
                    session.add(doc)
                    logger.info(f"Added document: {doc_data['title']}")
        
        # Ajouter les documents à Chroma
        documents = [doc["content"] for doc in sample_documents]
        metadatas = [
            {
                "title": doc["title"],
                "document_type": doc["document_type"],
                "specialty": doc["specialty"],
                "medical_level": doc["medical_level"],
                "target_audience": doc["target_audience"]
            }
            for doc in sample_documents
        ]
        
        doc_ids = chroma_manager.add_documents(documents, metadatas)
        logger.info(f"Added {len(doc_ids)} documents to Chroma")
        
        logger.info("Sample data creation completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Sample data creation failed: {e}")
        return False

def main():
    """Fonction principale de configuration"""
    logger.info("Starting database setup for Medical RAG Module")
    logger.info(f"Project root: {settings.PROJECT_ROOT}")
    
    success_count = 0
    total_steps = 4
    
    # 1. Configuration PostgreSQL
    if setup_postgresql():
        success_count += 1
    
    # 2. Configuration Chroma
    if setup_chroma():
        success_count += 1
    
    # 3. Configuration du modèle d'embedding
    if setup_embedding_model():
        success_count += 1
    
    # 4. Création de données d'exemple
    if create_sample_data():
        success_count += 1
    
    # Résumé
    logger.info("=== Résumé de la configuration ===")
    logger.info(f"Étapes réussies: {success_count}/{total_steps}")
    
    if success_count == total_steps:
        logger.info("✅ Configuration complète réussie!")
        logger.info("Le système RAG médical est prêt à être utilisé.")
        return True
    else:
        logger.error("❌ Configuration incomplète")
        logger.error("Veuillez vérifier les erreurs ci-dessus.")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Configuration interrompue par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        sys.exit(1)