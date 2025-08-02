#!/usr/bin/env python3
"""
Script de sauvegarde des embeddings pour le module RAG médical
Crée des sauvegardes complètes des embeddings et métadonnées
"""

import sys
import logging
import json
import pickle
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Ajouter le répertoire parent au path pour les imports
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import settings
from database.database import db_manager
from embeddings.chroma_manager import chroma_manager
from embeddings.embedding_manager import embedding_manager
from rag.langchain_rag import medical_rag

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class EmbeddingBackupManager:
    """Gestionnaire de sauvegarde des embeddings"""
    
    def __init__(self):
        self.backup_dir = settings.PROJECT_ROOT / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # Créer un dossier pour cette session de sauvegarde
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_backup_dir = self.backup_dir / f"backup_{timestamp}"
        self.session_backup_dir.mkdir(exist_ok=True)
        
        logger.info(f"Backup session directory: {self.session_backup_dir}")
    
    def backup_chroma_collection(self) -> bool:
        """Sauvegarde la collection Chroma"""
        logger.info("=== Backup Chroma Collection ===")
        
        try:
            # Obtenir toutes les données de la collection
            collection = chroma_manager.collection
            all_data = collection.get(include=["documents", "metadatas", "embeddings"])
            
            # Préparer les données de sauvegarde
            backup_data = {
                'collection_name': settings.CHROMA_COLLECTION_NAME,
                'embedding_model': settings.EMBEDDING_MODEL_NAME,
                'backup_timestamp': datetime.now().isoformat(),
                'total_documents': len(all_data['documents']),
                'documents': all_data['documents'],
                'metadatas': all_data['metadatas'],
                'ids': all_data['ids'],
                'embeddings': all_data['embeddings']
            }
            
            # Sauvegarder en JSON (sans embeddings pour la lisibilité)
            json_backup = backup_data.copy()
            del json_backup['embeddings']  # Trop volumineux pour JSON
            
            json_file = self.session_backup_dir / "chroma_metadata.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(json_backup, f, ensure_ascii=False, indent=2)
            
            # Sauvegarder en pickle (avec embeddings)
            pickle_file = self.session_backup_dir / "chroma_complete.pkl"
            with open(pickle_file, 'wb') as f:
                pickle.dump(backup_data, f)
            
            # Copier le répertoire de persistance Chroma
            chroma_persist_dir = Path(settings.CHROMA_PERSIST_DIRECTORY)
            if chroma_persist_dir.exists():
                backup_persist_dir = self.session_backup_dir / "chroma_persist"
                shutil.copytree(chroma_persist_dir, backup_persist_dir)
                logger.info(f"Copied Chroma persist directory to {backup_persist_dir}")
            
            logger.info(f"Chroma backup completed:")
            logger.info(f"  - Documents: {len(all_data['documents'])}")
            logger.info(f"  - JSON metadata: {json_file}")
            logger.info(f"  - Complete pickle: {pickle_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to backup Chroma collection: {e}")
            return False
    
    def backup_postgresql_data(self) -> bool:
        """Sauvegarde les données PostgreSQL"""
        logger.info("=== Backup PostgreSQL Data ===")
        
        try:
            from database.models import MedicalDocument, DocumentChunk, MedicalSpecialty, QueryLog
            
            backup_data = {
                'backup_timestamp': datetime.now().isoformat(),
                'database_url': settings.postgres_url.replace(settings.POSTGRES_PASSWORD, '***'),
                'tables': {}
            }
            
            with db_manager.get_session() as session:
                # Sauvegarder les documents médicaux
                documents = session.query(MedicalDocument).all()
                backup_data['tables']['medical_documents'] = [
                    {
                        'id': doc.id,
                        'title': doc.title,
                        'content': doc.content,
                        'document_type': doc.document_type,
                        'specialty': doc.specialty,
                        'language': doc.language,
                        'source_file': doc.source_file,
                        'file_hash': doc.file_hash,
                        'created_at': doc.created_at.isoformat() if doc.created_at else None,
                        'updated_at': doc.updated_at.isoformat() if doc.updated_at else None,
                        'published_date': doc.published_date.isoformat() if doc.published_date else None,
                        'is_validated': doc.is_validated,
                        'validation_status': doc.validation_status,
                        'validated_by': doc.validated_by,
                        'medical_level': doc.medical_level,
                        'target_audience': doc.target_audience,
                        'keywords': doc.keywords
                    }
                    for doc in documents
                ]
                
                # Sauvegarder les chunks
                chunks = session.query(DocumentChunk).all()
                backup_data['tables']['document_chunks'] = [
                    {
                        'id': chunk.id,
                        'document_id': chunk.document_id,
                        'chunk_index': chunk.chunk_index,
                        'content': chunk.content,
                        'chunk_size': chunk.chunk_size,
                        'overlap_size': chunk.overlap_size,
                        'start_position': chunk.start_position,
                        'end_position': chunk.end_position,
                        'section_title': chunk.section_title,
                        'created_at': chunk.created_at.isoformat() if chunk.created_at else None
                    }
                    for chunk in chunks
                ]
                
                # Sauvegarder les spécialités
                specialties = session.query(MedicalSpecialty).all()
                backup_data['tables']['medical_specialties'] = [
                    {
                        'id': spec.id,
                        'name': spec.name,
                        'description': spec.description,
                        'code': spec.code,
                        'is_active': spec.is_active,
                        'created_at': spec.created_at.isoformat() if spec.created_at else None
                    }
                    for spec in specialties
                ]
                
                # Sauvegarder les logs de requêtes (derniers 1000)
                query_logs = session.query(QueryLog).order_by(QueryLog.created_at.desc()).limit(1000).all()
                backup_data['tables']['query_logs'] = [
                    {
                        'id': log.id,
                        'query_text': log.query_text,
                        'user_id': log.user_id,
                        'session_id': log.session_id,
                        'results_count': log.results_count,
                        'top_similarity_score': log.top_similarity_score,
                        'response_time_ms': log.response_time_ms,
                        'embedding_model_used': log.embedding_model_used,
                        'retrieval_method': log.retrieval_method,
                        'created_at': log.created_at.isoformat() if log.created_at else None
                    }
                    for log in query_logs
                ]
            
            # Sauvegarder en JSON
            postgres_file = self.session_backup_dir / "postgresql_data.json"
            with open(postgres_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"PostgreSQL backup completed:")
            logger.info(f"  - Documents: {len(backup_data['tables']['medical_documents'])}")
            logger.info(f"  - Chunks: {len(backup_data['tables']['document_chunks'])}")
            logger.info(f"  - Specialties: {len(backup_data['tables']['medical_specialties'])}")
            logger.info(f"  - Query logs: {len(backup_data['tables']['query_logs'])}")
            logger.info(f"  - File: {postgres_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to backup PostgreSQL data: {e}")
            return False
    
    def backup_model_artifacts(self) -> bool:
        """Sauvegarde les artefacts du modèle"""
        logger.info("=== Backup Model Artifacts ===")
        
        try:
            # Informations sur le modèle
            model_info = embedding_manager.get_model_info()
            
            # Créer un test d'embedding pour vérifier la cohérence
            test_texts = [
                "Test de cohérence du modèle d'embedding",
                "Diagnostic médical de référence",
                "Protocole de traitement standard"
            ]
            
            test_embeddings = embedding_manager.encode_medical_text(test_texts)
            
            model_backup = {
                'backup_timestamp': datetime.now().isoformat(),
                'model_info': model_info,
                'test_texts': test_texts,
                'test_embeddings_shape': test_embeddings.shape,
                'test_embeddings_sample': test_embeddings[:, :10].tolist(),  # Premiers 10 dimensions
                'settings': {
                    'embedding_model_name': settings.EMBEDDING_MODEL_NAME,
                    'embedding_device': settings.EMBEDDING_DEVICE,
                    'embedding_batch_size': settings.EMBEDDING_BATCH_SIZE,
                    'chunk_size': settings.CHUNK_SIZE,
                    'chunk_overlap': settings.CHUNK_OVERLAP,
                    'top_k_retrieval': settings.TOP_K_RETRIEVAL
                }
            }
            
            # Sauvegarder les informations du modèle
            model_file = self.session_backup_dir / "model_info.json"
            with open(model_file, 'w', encoding='utf-8') as f:
                json.dump(model_backup, f, ensure_ascii=False, indent=2)
            
            # Sauvegarder les embeddings de test complets
            test_embeddings_file = self.session_backup_dir / "test_embeddings.pkl"
            with open(test_embeddings_file, 'wb') as f:
                pickle.dump({
                    'texts': test_texts,
                    'embeddings': test_embeddings,
                    'model_info': model_info
                }, f)
            
            logger.info(f"Model artifacts backup completed:")
            logger.info(f"  - Model: {model_info['model_name']}")
            logger.info(f"  - Device: {model_info['device']}")
            logger.info(f"  - Embedding dimension: {model_info['embedding_dimension']}")
            logger.info(f"  - Info file: {model_file}")
            logger.info(f"  - Test embeddings: {test_embeddings_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to backup model artifacts: {e}")
            return False
    
    def create_backup_archive(self) -> Optional[Path]:
        """Crée une archive ZIP de la sauvegarde"""
        logger.info("=== Creating Backup Archive ===")
        
        try:
            archive_name = f"medical_rag_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            archive_path = self.backup_dir / archive_name
            
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Ajouter tous les fichiers du répertoire de sauvegarde
                for file_path in self.session_backup_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(self.session_backup_dir)
                        zipf.write(file_path, arcname)
            
            # Calculer la taille de l'archive
            archive_size_mb = archive_path.stat().st_size / (1024 * 1024)
            
            logger.info(f"Backup archive created:")
            logger.info(f"  - File: {archive_path}")
            logger.info(f"  - Size: {archive_size_mb:.2f} MB")
            
            return archive_path
            
        except Exception as e:
            logger.error(f"Failed to create backup archive: {e}")
            return None
    
    def generate_backup_manifest(self) -> bool:
        """Génère un manifeste de la sauvegarde"""
        try:
            manifest = {
                'backup_info': {
                    'timestamp': datetime.now().isoformat(),
                    'backup_directory': str(self.session_backup_dir),
                    'system_info': {
                        'project_root': str(settings.PROJECT_ROOT),
                        'chroma_collection': settings.CHROMA_COLLECTION_NAME,
                        'embedding_model': settings.EMBEDDING_MODEL_NAME,
                        'postgres_db': settings.POSTGRES_DB
                    }
                },
                'files': [],
                'statistics': {}
            }
            
            # Lister tous les fichiers de sauvegarde
            total_size = 0
            for file_path in self.session_backup_dir.rglob('*'):
                if file_path.is_file():
                    file_size = file_path.stat().st_size
                    total_size += file_size
                    
                    manifest['files'].append({
                        'name': file_path.name,
                        'path': str(file_path.relative_to(self.session_backup_dir)),
                        'size_bytes': file_size,
                        'size_mb': file_size / (1024 * 1024)
                    })
            
            manifest['statistics'] = {
                'total_files': len(manifest['files']),
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024)
            }
            
            # Sauvegarder le manifeste
            manifest_file = self.session_backup_dir / "backup_manifest.json"
            with open(manifest_file, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Backup manifest created: {manifest_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate backup manifest: {e}")
            return False
    
    def cleanup_old_backups(self, keep_last_n: int = 5) -> bool:
        """Nettoie les anciennes sauvegardes"""
        try:
            # Lister tous les répertoires de sauvegarde
            backup_dirs = [d for d in self.backup_dir.iterdir() 
                          if d.is_dir() and d.name.startswith('backup_')]
            
            # Trier par date de création (plus récent en premier)
            backup_dirs.sort(key=lambda x: x.stat().st_ctime, reverse=True)
            
            # Supprimer les anciennes sauvegardes
            deleted_count = 0
            for old_backup in backup_dirs[keep_last_n:]:
                try:
                    shutil.rmtree(old_backup)
                    deleted_count += 1
                    logger.info(f"Deleted old backup: {old_backup.name}")
                except Exception as e:
                    logger.warning(f"Failed to delete {old_backup.name}: {e}")
            
            logger.info(f"Cleanup completed: deleted {deleted_count} old backups")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
            return False

def main():
    """Fonction principale de sauvegarde"""
    logger.info("Starting embeddings backup for Medical RAG Module")
    
    backup_manager = EmbeddingBackupManager()
    
    success_count = 0
    total_steps = 5
    
    # 1. Sauvegarder Chroma
    if backup_manager.backup_chroma_collection():
        success_count += 1
    
    # 2. Sauvegarder PostgreSQL
    if backup_manager.backup_postgresql_data():
        success_count += 1
    
    # 3. Sauvegarder les artefacts du modèle
    if backup_manager.backup_model_artifacts():
        success_count += 1
    
    # 4. Générer le manifeste
    if backup_manager.generate_backup_manifest():
        success_count += 1
    
    # 5. Créer l'archive
    archive_path = backup_manager.create_backup_archive()
    if archive_path:
        success_count += 1
    
    # Nettoyer les anciennes sauvegardes
    backup_manager.cleanup_old_backups()
    
    # Résumé
    logger.info("=== Backup Summary ===")
    logger.info(f"Steps completed: {success_count}/{total_steps}")
    
    if success_count == total_steps:
        logger.info("✅ Backup completed successfully!")
        logger.info(f"Backup directory: {backup_manager.session_backup_dir}")
        if archive_path:
            logger.info(f"Archive created: {archive_path}")
        return True
    else:
        logger.error("❌ Backup incomplete")
        logger.error("Please check the errors above.")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Backup interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)