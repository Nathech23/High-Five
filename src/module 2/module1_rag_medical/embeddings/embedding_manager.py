from sentence_transformers import SentenceTransformer
from typing import List, Union, Dict, Any, Optional
import numpy as np
import torch
import logging
from pathlib import Path
import pickle
from config.settings import settings

logger = logging.getLogger(__name__)

class EmbeddingManager:
    """Gestionnaire pour les embeddings de texte médical"""
    
    def __init__(self):
        self.model = None
        self.model_name = settings.EMBEDDING_MODEL_NAME
        self.device = settings.EMBEDDING_DEVICE
        self.batch_size = settings.EMBEDDING_BATCH_SIZE
        self._load_model()
    
    def _load_model(self):
        """Charge le modèle d'embedding"""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            
            # Vérifier la disponibilité du GPU
            if self.device == "cuda" and not torch.cuda.is_available():
                logger.warning("CUDA not available, falling back to CPU")
                self.device = "cpu"
            
            # Charger le modèle
            self.model = SentenceTransformer(
                self.model_name,
                device=self.device
            )
            
            # Optimiser pour l'inférence
            if self.device == "cuda":
                self.model.half()  # Utiliser la précision half pour économiser la mémoire GPU
            
            logger.info(f"Model loaded successfully on {self.device}")
            logger.info(f"Model max sequence length: {self.model.max_seq_length}")
            
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def encode_text(
        self,
        texts: Union[str, List[str]],
        normalize_embeddings: bool = True,
        show_progress_bar: bool = False
    ) -> np.ndarray:
        """Encode du texte en embeddings"""
        try:
            if isinstance(texts, str):
                texts = [texts]
            
            # Encoder les textes
            embeddings = self.model.encode(
                texts,
                batch_size=self.batch_size,
                normalize_embeddings=normalize_embeddings,
                show_progress_bar=show_progress_bar,
                convert_to_numpy=True
            )
            
            logger.debug(f"Encoded {len(texts)} texts to embeddings of shape {embeddings.shape}")
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to encode texts: {e}")
            raise
    
    def encode_medical_text(
        self,
        texts: Union[str, List[str]],
        preprocess: bool = True
    ) -> np.ndarray:
        """Encode du texte médical avec préprocessing spécialisé"""
        try:
            if isinstance(texts, str):
                texts = [texts]
            
            # Préprocessing spécialisé pour le texte médical
            if preprocess:
                texts = [self._preprocess_medical_text(text) for text in texts]
            
            return self.encode_text(texts)
            
        except Exception as e:
            logger.error(f"Failed to encode medical texts: {e}")
            raise
    
    def _preprocess_medical_text(self, text: str) -> str:
        """Préprocessing spécialisé pour le texte médical"""
        # Nettoyer le texte
        text = text.strip()
        
        # Remplacer les abréviations médicales courantes
        medical_abbreviations = {
            'mg': 'milligramme',
            'ml': 'millilitre',
            'kg': 'kilogramme',
            'bpm': 'battements par minute',
            'mmHg': 'millimètres de mercure',
            'ECG': 'électrocardiogramme',
            'IRM': 'imagerie par résonance magnétique',
            'TDM': 'tomodensitométrie',
            'VS': 'vitesse de sédimentation',
            'CRP': 'protéine C réactive',
            'NFS': 'numération formule sanguine',
            'TP': 'taux de prothrombine',
            'INR': 'international normalized ratio'
        }
        
        for abbrev, full_form in medical_abbreviations.items():
            text = text.replace(f' {abbrev} ', f' {full_form} ')
            text = text.replace(f' {abbrev}.', f' {full_form}.')
        
        return text
    
    def compute_similarity(
        self,
        embeddings1: np.ndarray,
        embeddings2: np.ndarray,
        metric: str = "cosine"
    ) -> np.ndarray:
        """Calcule la similarité entre embeddings"""
        try:
            if metric == "cosine":
                # Similarité cosinus
                similarity = np.dot(embeddings1, embeddings2.T)
                if embeddings1.ndim == 1 and embeddings2.ndim == 1:
                    similarity = similarity.item()
            elif metric == "euclidean":
                # Distance euclidienne (convertie en similarité)
                distances = np.linalg.norm(embeddings1[:, None] - embeddings2, axis=2)
                similarity = 1 / (1 + distances)
            else:
                raise ValueError(f"Unsupported similarity metric: {metric}")
            
            return similarity
            
        except Exception as e:
            logger.error(f"Failed to compute similarity: {e}")
            raise
    
    def find_most_similar(
        self,
        query_embedding: np.ndarray,
        candidate_embeddings: np.ndarray,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Trouve les embeddings les plus similaires"""
        try:
            # Calculer les similarités
            similarities = self.compute_similarity(
                query_embedding.reshape(1, -1),
                candidate_embeddings
            ).flatten()
            
            # Trier par similarité décroissante
            sorted_indices = np.argsort(similarities)[::-1][:top_k]
            
            results = []
            for idx in sorted_indices:
                results.append({
                    'index': int(idx),
                    'similarity': float(similarities[idx])
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to find most similar embeddings: {e}")
            raise
    
    def save_embeddings(
        self,
        embeddings: np.ndarray,
        metadata: Dict[str, Any],
        filepath: str
    ) -> bool:
        """Sauvegarde les embeddings sur disque"""
        try:
            save_data = {
                'embeddings': embeddings,
                'metadata': metadata,
                'model_name': self.model_name,
                'embedding_dimension': embeddings.shape[-1]
            }
            
            with open(filepath, 'wb') as f:
                pickle.dump(save_data, f)
            
            logger.info(f"Embeddings saved to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save embeddings: {e}")
            return False
    
    def load_embeddings(self, filepath: str) -> Optional[Dict[str, Any]]:
        """Charge les embeddings depuis le disque"""
        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
            
            # Vérifier la compatibilité du modèle
            if data.get('model_name') != self.model_name:
                logger.warning(
                    f"Model mismatch: saved with {data.get('model_name')}, "
                    f"current model is {self.model_name}"
                )
            
            logger.info(f"Embeddings loaded from {filepath}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to load embeddings: {e}")
            return None
    
    def get_model_info(self) -> Dict[str, Any]:
        """Retourne les informations sur le modèle"""
        return {
            'model_name': self.model_name,
            'device': self.device,
            'batch_size': self.batch_size,
            'max_sequence_length': self.model.max_seq_length,
            'embedding_dimension': self.model.get_sentence_embedding_dimension(),
            'tokenizer': str(type(self.model.tokenizer).__name__)
        }
    
    def benchmark_encoding(self, sample_texts: List[str]) -> Dict[str, Any]:
        """Benchmark des performances d'encodage"""
        import time
        
        try:
            start_time = time.time()
            embeddings = self.encode_text(sample_texts, show_progress_bar=True)
            end_time = time.time()
            
            total_time = end_time - start_time
            texts_per_second = len(sample_texts) / total_time
            
            benchmark_results = {
                'total_texts': len(sample_texts),
                'total_time_seconds': total_time,
                'texts_per_second': texts_per_second,
                'average_time_per_text': total_time / len(sample_texts),
                'embedding_shape': embeddings.shape,
                'device_used': self.device
            }
            
            logger.info(f"Encoding benchmark: {texts_per_second:.2f} texts/second")
            return benchmark_results
            
        except Exception as e:
            logger.error(f"Failed to run encoding benchmark: {e}")
            return {}

# Instance globale du gestionnaire d'embeddings
embedding_manager = EmbeddingManager()