#!/usr/bin/env python3
"""
Pipeline d'Embeddings Optimisé pour Documents Médicaux

Ce module implémente un pipeline complet d'embeddings utilisant sentence-transformers
avec des optimisations spécifiques pour le domaine médical.
"""

import os
import logging
import pickle
import json
from typing import List, Dict, Tuple, Optional, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
import torch
from sentence_transformers import SentenceTransformer, util
from sentence_transformers.evaluation import EmbeddingSimilarityEvaluator
import faiss
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import seaborn as sns
from tqdm import tqdm
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EmbeddingMetadata:
    """Métadonnées pour un embedding"""
    text_id: str
    text_hash: str
    embedding_model: str
    embedding_dimension: int
    creation_timestamp: float
    processing_time: float
    text_length: int
    word_count: int
    language: str
    medical_domain: str
    confidence_score: float

@dataclass
class ProcessedEmbedding:
    """Embedding traité avec métadonnées"""
    text: str
    embedding: np.ndarray
    metadata: EmbeddingMetadata
    normalized_embedding: Optional[np.ndarray] = None
    cluster_id: Optional[int] = None
    similarity_scores: Optional[Dict[str, float]] = None

class MedicalEmbeddingPipeline:
    """
    Pipeline d'embeddings optimisé pour documents médicaux
    
    Fonctionnalités:
    - Modèles sentence-transformers optimisés pour le médical
    - Traitement par batch pour performance
    - Cache intelligent des embeddings
    - Normalisation et clustering automatique
    - Métriques de qualité et monitoring
    """
    
    def __init__(self,
                 model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
                 cache_dir: str = "./embeddings_cache",
                 batch_size: int = 32,
                 max_seq_length: int = 512,
                 device: str = None,
                 normalize_embeddings: bool = True):
        """
        Initialise le pipeline d'embeddings
        
        Args:
            model_name: Nom du modèle sentence-transformers
            cache_dir: Répertoire de cache pour les embeddings
            batch_size: Taille des batches pour le traitement
            max_seq_length: Longueur maximale des séquences
            device: Device PyTorch (auto-détection si None)
            normalize_embeddings: Normaliser les embeddings
        """
        self.model_name = model_name
        self.cache_dir = Path(cache_dir)
        self.batch_size = batch_size
        self.max_seq_length = max_seq_length
        self.normalize_embeddings = normalize_embeddings
        
        # Création du répertoire de cache
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Détection du device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        # Initialisation du modèle
        self._init_model()
        
        # Cache des embeddings
        self.embedding_cache = {}
        self.metadata_cache = {}
        
        # Index FAISS pour recherche rapide
        self.faiss_index = None
        self.faiss_id_mapping = {}
        
        # Statistiques
        self.stats = {
            'total_embeddings': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_processing_time': 0.0,
            'avg_processing_time': 0.0
        }
        
        logger.info(f"Pipeline d'embeddings initialisé (modèle: {model_name}, device: {self.device})")
    
    def _init_model(self):
        """Initialise le modèle sentence-transformers"""
        try:
            logger.info(f"Chargement du modèle {self.model_name}...")
            
            self.model = SentenceTransformer(
                self.model_name,
                device=self.device
            )
            
            # Configuration de la longueur maximale
            if hasattr(self.model, 'max_seq_length'):
                self.model.max_seq_length = self.max_seq_length
            
            # Informations sur le modèle
            self.embedding_dimension = self.model.get_sentence_embedding_dimension()
            
            logger.info(f"Modèle chargé avec succès (dimension: {self.embedding_dimension})")
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement du modèle: {e}")
            raise
    
    def process_texts(self, 
                     texts: List[str],
                     text_ids: Optional[List[str]] = None,
                     metadata: Optional[List[Dict[str, Any]]] = None,
                     use_cache: bool = True,
                     show_progress: bool = True) -> List[ProcessedEmbedding]:
        """
        Traite une liste de textes pour créer des embeddings
        
        Args:
            texts: Liste des textes à traiter
            text_ids: Identifiants des textes (générés automatiquement si None)
            metadata: Métadonnées additionnelles pour chaque texte
            use_cache: Utiliser le cache des embeddings
            show_progress: Afficher la barre de progression
            
        Returns:
            Liste des embeddings traités
        """
        if not texts:
            return []
        
        # Génération des IDs si nécessaire
        if text_ids is None:
            text_ids = [f"text_{i}" for i in range(len(texts))]
        
        if metadata is None:
            metadata = [{}] * len(texts)
        
        logger.info(f"Traitement de {len(texts)} textes...")
        start_time = time.time()
        
        processed_embeddings = []
        texts_to_process = []
        indices_to_process = []
        
        # Vérification du cache
        for i, (text, text_id) in enumerate(zip(texts, text_ids)):
            text_hash = self._get_text_hash(text)
            
            if use_cache and text_hash in self.embedding_cache:
                # Récupération depuis le cache
                cached_embedding = self.embedding_cache[text_hash]
                cached_metadata = self.metadata_cache[text_hash]
                
                processed_embedding = ProcessedEmbedding(
                    text=text,
                    embedding=cached_embedding,
                    metadata=cached_metadata
                )
                processed_embeddings.append(processed_embedding)
                self.stats['cache_hits'] += 1
            else:
                # Ajout à la liste de traitement
                texts_to_process.append(text)
                indices_to_process.append(i)
                processed_embeddings.append(None)  # Placeholder
        
        # Traitement des textes non cachés
        if texts_to_process:
            logger.info(f"Calcul de {len(texts_to_process)} nouveaux embeddings...")
            
            new_embeddings = self._compute_embeddings(
                texts_to_process, 
                show_progress=show_progress
            )
            
            # Création des objets ProcessedEmbedding
            for i, (text, embedding) in enumerate(zip(texts_to_process, new_embeddings)):
                original_index = indices_to_process[i]
                text_id = text_ids[original_index]
                text_metadata = metadata[original_index]
                
                # Création des métadonnées
                embedding_metadata = self._create_embedding_metadata(
                    text, text_id, embedding, text_metadata
                )
                
                # Normalisation si demandée
                normalized_embedding = None
                if self.normalize_embeddings:
                    normalized_embedding = util.normalize_embeddings(embedding.reshape(1, -1))[0]
                
                processed_embedding = ProcessedEmbedding(
                    text=text,
                    embedding=embedding,
                    metadata=embedding_metadata,
                    normalized_embedding=normalized_embedding
                )
                
                processed_embeddings[original_index] = processed_embedding
                
                # Mise en cache
                if use_cache:
                    text_hash = self._get_text_hash(text)
                    self.embedding_cache[text_hash] = embedding
                    self.metadata_cache[text_hash] = embedding_metadata
                
                self.stats['cache_misses'] += 1
        
        # Mise à jour des statistiques
        processing_time = time.time() - start_time
        self.stats['total_embeddings'] += len(texts)
        self.stats['total_processing_time'] += processing_time
        self.stats['avg_processing_time'] = (
            self.stats['total_processing_time'] / self.stats['total_embeddings']
        )
        
        logger.info(f"Traitement terminé en {processing_time:.2f}s")
        return processed_embeddings
    
    def _compute_embeddings(self, 
                           texts: List[str], 
                           show_progress: bool = True) -> np.ndarray:
        """Calcule les embeddings pour une liste de textes"""
        try:
            # Préprocessing des textes
            preprocessed_texts = [self._preprocess_text(text) for text in texts]
            
            # Calcul des embeddings par batch
            embeddings = self.model.encode(
                preprocessed_texts,
                batch_size=self.batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True,
                normalize_embeddings=False  # Nous normalisons manuellement
            )
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul des embeddings: {e}")
            raise
    
    def _preprocess_text(self, text: str) -> str:
        """Préprocessing spécialisé pour textes médicaux"""
        # Nettoyage de base
        text = text.strip()
        
        # Limitation de la longueur
        if len(text) > self.max_seq_length * 4:  # Approximation caractères -> tokens
            text = text[:self.max_seq_length * 4]
        
        # Normalisation des espaces
        text = ' '.join(text.split())
        
        return text
    
    def _create_embedding_metadata(self, 
                                  text: str, 
                                  text_id: str, 
                                  embedding: np.ndarray,
                                  additional_metadata: Dict[str, Any]) -> EmbeddingMetadata:
        """Crée les métadonnées pour un embedding"""
        text_hash = self._get_text_hash(text)
        
        return EmbeddingMetadata(
            text_id=text_id,
            text_hash=text_hash,
            embedding_model=self.model_name,
            embedding_dimension=len(embedding),
            creation_timestamp=time.time(),
            processing_time=0.0,  # Sera calculé globalement
            text_length=len(text),
            word_count=len(text.split()),
            language=additional_metadata.get('language', 'unknown'),
            medical_domain=additional_metadata.get('medical_domain', 'general'),
            confidence_score=1.0  # Score par défaut
        )
    
    def _get_text_hash(self, text: str) -> str:
        """Génère un hash unique pour un texte"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def build_faiss_index(self, 
                         embeddings: List[ProcessedEmbedding],
                         index_type: str = "flat") -> None:
        """
        Construit un index FAISS pour recherche rapide
        
        Args:
            embeddings: Liste des embeddings à indexer
            index_type: Type d'index FAISS (flat, ivf, hnsw)
        """
        if not embeddings:
            logger.warning("Aucun embedding fourni pour l'indexation")
            return
        
        logger.info(f"Construction de l'index FAISS ({index_type})...")
        
        # Extraction des vecteurs
        vectors = np.array([
            emb.normalized_embedding if emb.normalized_embedding is not None else emb.embedding
            for emb in embeddings
        ]).astype('float32')
        
        dimension = vectors.shape[1]
        
        # Création de l'index selon le type
        if index_type == "flat":
            self.faiss_index = faiss.IndexFlatIP(dimension)  # Inner Product pour cosine similarity
        elif index_type == "ivf":
            nlist = min(100, len(embeddings) // 10)  # Nombre de clusters
            quantizer = faiss.IndexFlatIP(dimension)
            self.faiss_index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
            self.faiss_index.train(vectors)
        elif index_type == "hnsw":
            self.faiss_index = faiss.IndexHNSWFlat(dimension, 32)
            self.faiss_index.hnsw.efConstruction = 200
        else:
            raise ValueError(f"Type d'index non supporté: {index_type}")
        
        # Ajout des vecteurs à l'index
        self.faiss_index.add(vectors)
        
        # Mapping des IDs
        self.faiss_id_mapping = {
            i: emb.metadata.text_id for i, emb in enumerate(embeddings)
        }
        
        logger.info(f"Index FAISS construit avec {len(embeddings)} vecteurs")
    
    def search_similar(self, 
                      query_embedding: np.ndarray,
                      k: int = 10,
                      threshold: float = 0.0) -> List[Tuple[str, float]]:
        """
        Recherche les embeddings les plus similaires
        
        Args:
            query_embedding: Embedding de la requête
            k: Nombre de résultats à retourner
            threshold: Seuil de similarité minimum
            
        Returns:
            Liste de tuples (text_id, score)
        """
        if self.faiss_index is None:
            raise ValueError("Index FAISS non construit. Appelez build_faiss_index() d'abord.")
        
        # Normalisation de la requête si nécessaire
        if self.normalize_embeddings:
            query_embedding = util.normalize_embeddings(query_embedding.reshape(1, -1))[0]
        
        # Recherche
        scores, indices = self.faiss_index.search(
            query_embedding.reshape(1, -1).astype('float32'), k
        )
        
        # Filtrage et formatage des résultats
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1 and score >= threshold:
                text_id = self.faiss_id_mapping.get(idx, f"unknown_{idx}")
                results.append((text_id, float(score)))
        
        return results
    
    def cluster_embeddings(self, 
                          embeddings: List[ProcessedEmbedding],
                          n_clusters: int = None,
                          method: str = "kmeans") -> Dict[int, List[str]]:
        """
        Clustering des embeddings
        
        Args:
            embeddings: Liste des embeddings à clustériser
            n_clusters: Nombre de clusters (auto si None)
            method: Méthode de clustering
            
        Returns:
            Dictionnaire cluster_id -> liste des text_ids
        """
        if not embeddings:
            return {}
        
        logger.info(f"Clustering de {len(embeddings)} embeddings...")
        
        # Extraction des vecteurs
        vectors = np.array([
            emb.normalized_embedding if emb.normalized_embedding is not None else emb.embedding
            for emb in embeddings
        ])
        
        # Détermination automatique du nombre de clusters
        if n_clusters is None:
            n_clusters = min(10, max(2, len(embeddings) // 20))
        
        # Clustering
        if method == "kmeans":
            clusterer = KMeans(n_clusters=n_clusters, random_state=42)
            cluster_labels = clusterer.fit_predict(vectors)
        else:
            raise ValueError(f"Méthode de clustering non supportée: {method}")
        
        # Mise à jour des embeddings avec les labels de cluster
        for emb, label in zip(embeddings, cluster_labels):
            emb.cluster_id = int(label)
        
        # Création du dictionnaire de résultats
        clusters = {}
        for emb, label in zip(embeddings, cluster_labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(emb.metadata.text_id)
        
        logger.info(f"Clustering terminé: {len(clusters)} clusters créés")
        return clusters
    
    def evaluate_embeddings(self, 
                           embeddings: List[ProcessedEmbedding],
                           test_pairs: Optional[List[Tuple[str, str, float]]] = None) -> Dict[str, float]:
        """
        Évalue la qualité des embeddings
        
        Args:
            embeddings: Liste des embeddings à évaluer
            test_pairs: Paires de test (text1, text2, similarité_attendue)
            
        Returns:
            Métriques d'évaluation
        """
        logger.info("Évaluation de la qualité des embeddings...")
        
        metrics = {}
        
        # Statistiques de base
        if embeddings:
            dimensions = [emb.embedding.shape[0] for emb in embeddings]
            metrics['avg_dimension'] = np.mean(dimensions)
            metrics['std_dimension'] = np.std(dimensions)
            
            # Norme des vecteurs
            norms = [np.linalg.norm(emb.embedding) for emb in embeddings]
            metrics['avg_norm'] = np.mean(norms)
            metrics['std_norm'] = np.std(norms)
            
            # Diversité des embeddings
            if len(embeddings) > 1:
                vectors = np.array([emb.embedding for emb in embeddings])
                similarity_matrix = cosine_similarity(vectors)
                
                # Similarité moyenne (hors diagonale)
                mask = ~np.eye(similarity_matrix.shape[0], dtype=bool)
                avg_similarity = np.mean(similarity_matrix[mask])
                metrics['avg_pairwise_similarity'] = avg_similarity
                metrics['embedding_diversity'] = 1 - avg_similarity
        
        # Évaluation sur paires de test si fournies
        if test_pairs and embeddings:
            embedding_dict = {emb.metadata.text_id: emb.embedding for emb in embeddings}
            
            predicted_similarities = []
            expected_similarities = []
            
            for text1_id, text2_id, expected_sim in test_pairs:
                if text1_id in embedding_dict and text2_id in embedding_dict:
                    emb1 = embedding_dict[text1_id]
                    emb2 = embedding_dict[text2_id]
                    
                    predicted_sim = cosine_similarity(
                        emb1.reshape(1, -1), 
                        emb2.reshape(1, -1)
                    )[0][0]
                    
                    predicted_similarities.append(predicted_sim)
                    expected_similarities.append(expected_sim)
            
            if predicted_similarities:
                # Corrélation de Pearson
                correlation = np.corrcoef(predicted_similarities, expected_similarities)[0, 1]
                metrics['pearson_correlation'] = correlation
                
                # Erreur moyenne absolue
                mae = np.mean(np.abs(np.array(predicted_similarities) - np.array(expected_similarities)))
                metrics['mean_absolute_error'] = mae
        
        return metrics
    
    def save_embeddings(self, 
                       embeddings: List[ProcessedEmbedding],
                       filepath: str,
                       format: str = "pickle") -> None:
        """
        Sauvegarde les embeddings
        
        Args:
            embeddings: Liste des embeddings à sauvegarder
            filepath: Chemin du fichier de sauvegarde
            format: Format de sauvegarde (pickle, json, npz)
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Sauvegarde de {len(embeddings)} embeddings vers {filepath}...")
        
        if format == "pickle":
            with open(filepath, 'wb') as f:
                pickle.dump(embeddings, f)
        
        elif format == "json":
            # Conversion en format JSON-sérialisable
            json_data = []
            for emb in embeddings:
                json_emb = {
                    'text': emb.text,
                    'embedding': emb.embedding.tolist(),
                    'metadata': asdict(emb.metadata)
                }
                if emb.normalized_embedding is not None:
                    json_emb['normalized_embedding'] = emb.normalized_embedding.tolist()
                json_data.append(json_emb)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        elif format == "npz":
            # Sauvegarde des vecteurs et métadonnées séparément
            vectors = np.array([emb.embedding for emb in embeddings])
            metadata = [asdict(emb.metadata) for emb in embeddings]
            
            np.savez_compressed(
                filepath,
                embeddings=vectors,
                metadata=metadata,
                texts=[emb.text for emb in embeddings]
            )
        
        else:
            raise ValueError(f"Format non supporté: {format}")
        
        logger.info(f"Sauvegarde terminée: {filepath}")
    
    def load_embeddings(self, filepath: str, format: str = "pickle") -> List[ProcessedEmbedding]:
        """
        Charge les embeddings depuis un fichier
        
        Args:
            filepath: Chemin du fichier
            format: Format du fichier
            
        Returns:
            Liste des embeddings chargés
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"Fichier non trouvé: {filepath}")
        
        logger.info(f"Chargement des embeddings depuis {filepath}...")
        
        if format == "pickle":
            with open(filepath, 'rb') as f:
                embeddings = pickle.load(f)
        
        elif format == "json":
            with open(filepath, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            embeddings = []
            for item in json_data:
                metadata = EmbeddingMetadata(**item['metadata'])
                embedding = np.array(item['embedding'])
                normalized_embedding = None
                if 'normalized_embedding' in item:
                    normalized_embedding = np.array(item['normalized_embedding'])
                
                emb = ProcessedEmbedding(
                    text=item['text'],
                    embedding=embedding,
                    metadata=metadata,
                    normalized_embedding=normalized_embedding
                )
                embeddings.append(emb)
        
        elif format == "npz":
            data = np.load(filepath, allow_pickle=True)
            vectors = data['embeddings']
            metadata_list = data['metadata']
            texts = data['texts']
            
            embeddings = []
            for i, (vector, metadata_dict, text) in enumerate(zip(vectors, metadata_list, texts)):
                metadata = EmbeddingMetadata(**metadata_dict)
                emb = ProcessedEmbedding(
                    text=text,
                    embedding=vector,
                    metadata=metadata
                )
                embeddings.append(emb)
        
        else:
            raise ValueError(f"Format non supporté: {format}")
        
        logger.info(f"Chargement terminé: {len(embeddings)} embeddings")
        return embeddings
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du pipeline"""
        return {
            'model_info': {
                'name': self.model_name,
                'dimension': self.embedding_dimension,
                'device': self.device,
                'max_seq_length': self.max_seq_length
            },
            'processing_stats': self.stats.copy(),
            'cache_info': {
                'cache_size': len(self.embedding_cache),
                'hit_rate': self.stats['cache_hits'] / max(1, self.stats['cache_hits'] + self.stats['cache_misses'])
            },
            'index_info': {
                'has_faiss_index': self.faiss_index is not None,
                'indexed_vectors': len(self.faiss_id_mapping) if self.faiss_index else 0
            }
        }
    
    def visualize_embeddings(self, 
                           embeddings: List[ProcessedEmbedding],
                           output_path: str = None,
                           method: str = "pca") -> None:
        """
        Visualise les embeddings en 2D
        
        Args:
            embeddings: Liste des embeddings à visualiser
            output_path: Chemin de sauvegarde du graphique
            method: Méthode de réduction de dimension (pca, tsne)
        """
        if not embeddings:
            logger.warning("Aucun embedding à visualiser")
            return
        
        logger.info(f"Visualisation de {len(embeddings)} embeddings...")
        
        # Extraction des vecteurs
        vectors = np.array([emb.embedding for emb in embeddings])
        
        # Réduction de dimension
        if method == "pca":
            reducer = PCA(n_components=2, random_state=42)
            reduced_vectors = reducer.fit_transform(vectors)
        else:
            raise ValueError(f"Méthode non supportée: {method}")
        
        # Création du graphique
        plt.figure(figsize=(12, 8))
        
        # Coloration par cluster si disponible
        colors = [emb.cluster_id if emb.cluster_id is not None else 0 for emb in embeddings]
        
        scatter = plt.scatter(
            reduced_vectors[:, 0], 
            reduced_vectors[:, 1],
            c=colors,
            cmap='tab10',
            alpha=0.7,
            s=50
        )
        
        plt.title(f'Visualisation des Embeddings ({method.upper()})')
        plt.xlabel('Composante 1')
        plt.ylabel('Composante 2')
        
        # Légende si clusters disponibles
        if any(emb.cluster_id is not None for emb in embeddings):
            plt.colorbar(scatter, label='Cluster ID')
        
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            logger.info(f"Graphique sauvegardé: {output_path}")
        
        plt.show()

def main():
    """Fonction de test du pipeline d'embeddings"""
    # Initialisation du pipeline
    pipeline = MedicalEmbeddingPipeline(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        batch_size=16,
        normalize_embeddings=True
    )
    
    # Textes de test médicaux
    test_texts = [
        "Le paludisme est une maladie transmise par les moustiques anophèles.",
        "Les symptômes du paludisme incluent fièvre, frissons et maux de tête.",
        "Le diagnostic du paludisme se fait par examen microscopique du sang.",
        "Le traitement du paludisme utilise des médicaments antipaludiques.",
        "La prévention du paludisme passe par l'utilisation de moustiquaires.",
        "Le diabète est une maladie métabolique chronique.",
        "L'hypertension artérielle est un facteur de risque cardiovasculaire.",
        "La vaccination est un moyen efficace de prévention des maladies."
    ]
    
    # Traitement des textes
    embeddings = pipeline.process_texts(
        test_texts,
        text_ids=[f"medical_text_{i}" for i in range(len(test_texts))]
    )
    
    print(f"\n=== RÉSULTATS DU PIPELINE D'EMBEDDINGS ===")
    print(f"Nombre d'embeddings créés: {len(embeddings)}")
    print(f"Dimension des embeddings: {embeddings[0].embedding.shape[0]}")
    
    # Construction de l'index FAISS
    pipeline.build_faiss_index(embeddings)
    
    # Test de recherche
    query_text = "symptômes et diagnostic du paludisme"
    query_embedding = pipeline.model.encode([query_text])[0]
    
    similar_results = pipeline.search_similar(query_embedding, k=3)
    print(f"\n=== RECHERCHE SIMILAIRE ===")
    print(f"Requête: {query_text}")
    for text_id, score in similar_results:
        print(f"  {text_id}: {score:.3f}")
    
    # Clustering
    clusters = pipeline.cluster_embeddings(embeddings, n_clusters=3)
    print(f"\n=== CLUSTERING ===")
    for cluster_id, text_ids in clusters.items():
        print(f"Cluster {cluster_id}: {text_ids}")
    
    # Évaluation
    metrics = pipeline.evaluate_embeddings(embeddings)
    print(f"\n=== MÉTRIQUES D'ÉVALUATION ===")
    for metric, value in metrics.items():
        print(f"{metric}: {value:.3f}")
    
    # Statistiques du pipeline
    stats = pipeline.get_pipeline_stats()
    print(f"\n=== STATISTIQUES DU PIPELINE ===")
    print(f"Modèle: {stats['model_info']['name']}")
    print(f"Device: {stats['model_info']['device']}")
    print(f"Embeddings traités: {stats['processing_stats']['total_embeddings']}")
    print(f"Taux de cache: {stats['cache_info']['hit_rate']:.2%}")

if __name__ == "__main__":
    main()