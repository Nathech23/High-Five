import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional, Tuple
import logging
import uuid
import numpy as np
from config.settings import settings

logger = logging.getLogger(__name__)

class ChromaManager:
    """Gestionnaire pour la base de données vectorielle Chroma"""
    
    def __init__(self):
        self.client = None
        self.collection = None
        self.embedding_function = None
        self._initialize_chroma()
    
    def _initialize_chroma(self):
        """Initialise la connexion à Chroma"""
        try:
            # Configuration Chroma
            chroma_settings = ChromaSettings(
                persist_directory=settings.CHROMA_PERSIST_DIRECTORY,
                anonymized_telemetry=False
            )
            
            # Créer le client Chroma
            self.client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIRECTORY,
                settings=chroma_settings
            )
            
            # Configurer la fonction d'embedding
            self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=settings.EMBEDDING_MODEL_NAME,
                device=settings.EMBEDDING_DEVICE
            )
            
            # Créer ou récupérer la collection
            self._setup_collection()
            
            logger.info(f"Chroma initialized successfully with collection '{settings.CHROMA_COLLECTION_NAME}'")
            
        except Exception as e:
            logger.error(f"Failed to initialize Chroma: {e}")
            raise
    
    def _setup_collection(self):
        """Configure la collection Chroma"""
        try:
            # Essayer de récupérer la collection existante
            try:
                self.collection = self.client.get_collection(
                    name=settings.CHROMA_COLLECTION_NAME,
                    embedding_function=self.embedding_function
                )
                logger.info(f"Retrieved existing collection '{settings.CHROMA_COLLECTION_NAME}'")
            except:
                # Créer une nouvelle collection si elle n'existe pas
                self.collection = self.client.create_collection(
                    name=settings.CHROMA_COLLECTION_NAME,
                    embedding_function=self.embedding_function,
                    metadata={"description": "Medical knowledge base for Hôpital Général Douala"}
                )
                logger.info(f"Created new collection '{settings.CHROMA_COLLECTION_NAME}'")
                
        except Exception as e:
            logger.error(f"Failed to setup collection: {e}")
            raise
    
    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """Ajoute des documents à la collection"""
        try:
            if ids is None:
                ids = [str(uuid.uuid4()) for _ in documents]
            
            # Valider les données
            if len(documents) != len(metadatas) or len(documents) != len(ids):
                raise ValueError("Documents, metadatas, and ids must have the same length")
            
            # Ajouter à la collection
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Added {len(documents)} documents to collection")
            return ids
            
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise
    
    def search_similar(
        self,
        query: str,
        n_results: int = None,
        where: Optional[Dict[str, Any]] = None,
        include: List[str] = None
    ) -> Dict[str, Any]:
        """Recherche des documents similaires"""
        try:
            if n_results is None:
                n_results = settings.TOP_K_RETRIEVAL
            
            if include is None:
                include = ["documents", "metadatas", "distances"]
            
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where,
                include=include
            )
            
            logger.info(f"Search completed: found {len(results['documents'][0])} results")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search similar documents: {e}")
            raise
    
    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un document par son ID"""
        try:
            results = self.collection.get(
                ids=[doc_id],
                include=["documents", "metadatas"]
            )
            
            if results['documents']:
                return {
                    'id': doc_id,
                    'document': results['documents'][0],
                    'metadata': results['metadatas'][0]
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to get document by ID {doc_id}: {e}")
            return None
    
    def update_document(
        self,
        doc_id: str,
        document: str = None,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Met à jour un document existant"""
        try:
            update_data = {'ids': [doc_id]}
            
            if document is not None:
                update_data['documents'] = [document]
            
            if metadata is not None:
                update_data['metadatas'] = [metadata]
            
            self.collection.update(**update_data)
            logger.info(f"Updated document {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update document {doc_id}: {e}")
            return False
    
    def delete_document(self, doc_id: str) -> bool:
        """Supprime un document"""
        try:
            self.collection.delete(ids=[doc_id])
            logger.info(f"Deleted document {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de la collection"""
        try:
            count = self.collection.count()
            
            # Récupérer quelques échantillons pour analyser les métadonnées
            sample_results = self.collection.peek(limit=10)
            
            stats = {
                'total_documents': count,
                'collection_name': settings.CHROMA_COLLECTION_NAME,
                'embedding_model': settings.EMBEDDING_MODEL_NAME,
                'sample_metadatas': sample_results.get('metadatas', [])
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {}
    
    def reset_collection(self) -> bool:
        """Remet à zéro la collection (ATTENTION: destructif!)"""
        try:
            # Supprimer la collection existante
            self.client.delete_collection(name=settings.CHROMA_COLLECTION_NAME)
            
            # Recréer la collection
            self._setup_collection()
            
            logger.warning(f"Collection '{settings.CHROMA_COLLECTION_NAME}' has been reset")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset collection: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Teste la connexion à Chroma"""
        try:
            # Test simple: compter les documents
            count = self.collection.count()
            logger.info(f"Chroma connection test successful. Collection has {count} documents")
            return True
            
        except Exception as e:
            logger.error(f"Chroma connection test failed: {e}")
            return False
    
    def backup_embeddings(self, backup_path: str) -> bool:
        """Sauvegarde les embeddings"""
        try:
            # Cette méthode sera implémentée selon les besoins spécifiques
            # Pour l'instant, on peut exporter les métadonnées
            all_data = self.collection.get(include=["documents", "metadatas"])
            
            import json
            backup_data = {
                'collection_name': settings.CHROMA_COLLECTION_NAME,
                'embedding_model': settings.EMBEDDING_MODEL_NAME,
                'documents': all_data['documents'],
                'metadatas': all_data['metadatas'],
                'ids': all_data['ids']
            }
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Embeddings backed up to {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to backup embeddings: {e}")
            return False

# Instance globale du gestionnaire Chroma
chroma_manager = ChromaManager()