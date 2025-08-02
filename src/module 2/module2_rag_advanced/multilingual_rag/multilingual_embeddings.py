#!/usr/bin/env python3
"""
Embeddings Multilingues

Objectif 11: Implémenter embeddings multilingues

Ce module implémente un système d'embeddings optimisé pour le multilinguisme,
avec support spécial pour le français et les langues camerounaises.

Auteur: Équipe Hackathon Hôpital Général de Douala
Module: 2 - RAG Avancé & Multilingue
Version: 2.0.0
"""

import asyncio
import logging
import numpy as np
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import pickle
import hashlib
from collections import defaultdict

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
    import torch
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning("sentence-transformers non disponible, utilisation du mode simulation")
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    logger.warning("FAISS non disponible, utilisation d'une recherche simple")
    FAISS_AVAILABLE = False

class EmbeddingModel(Enum):
    """Modèles d'embeddings disponibles"""
    MULTILINGUAL_MINILM = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    MULTILINGUAL_MPNET = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    DISTILUSE_MULTILINGUAL = "sentence-transformers/distiluse-base-multilingual-cased"
    LABSE = "sentence-transformers/LaBSE"
    MULTILINGUAL_E5_SMALL = "intfloat/multilingual-e5-small"
    MULTILINGUAL_E5_BASE = "intfloat/multilingual-e5-base"
    MULTILINGUAL_E5_LARGE = "intfloat/multilingual-e5-large"
    CUSTOM_MEDICAL = "custom_medical_multilingual"  # Modèle personnalisé

class LanguageFamily(Enum):
    """Familles de langues pour optimisation"""
    ROMANCE = "romance"  # Français, Espagnol, Italien
    GERMANIC = "germanic"  # Anglais, Allemand
    AFROASIATIC = "afroasiatic"  # Arabe, Hausa
    NIGER_CONGO = "niger_congo"  # Fulfulde, Ewondo, Duala, Bamiléké
    MIXED = "mixed"  # Langues mixtes ou non classifiées

@dataclass
class LanguageConfig:
    """Configuration pour une langue spécifique"""
    code: str
    name: str
    family: LanguageFamily
    embedding_weight: float = 1.0  # Poids pour cette langue
    preprocessing_rules: List[str] = field(default_factory=list)
    special_tokens: Dict[str, str] = field(default_factory=dict)
    medical_terms_boost: float = 1.2  # Boost pour termes médicaux
    chunking_strategy: str = "sentence"  # sentence, paragraph, custom
    max_sequence_length: int = 512

@dataclass
class EmbeddingResult:
    """Résultat d'embedding"""
    text: str
    language: str
    embedding: np.ndarray
    confidence: float
    processing_time: float
    model_used: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SimilarityResult:
    """Résultat de similarité"""
    query_text: str
    target_text: str
    similarity_score: float
    query_language: str
    target_language: str
    cross_lingual: bool
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class EmbeddingStats:
    """Statistiques des embeddings"""
    total_embeddings: int = 0
    embeddings_by_language: Dict[str, int] = field(default_factory=dict)
    avg_processing_time: float = 0.0
    avg_confidence: float = 0.0
    cache_hit_rate: float = 0.0
    model_performance: Dict[str, float] = field(default_factory=dict)
    cross_lingual_queries: int = 0
    processing_time: float = 0.0

class MultilingualEmbeddings:
    """
    Système d'embeddings multilingues optimisé
    
    Objectif couvert:
    - 11. Implémenter embeddings multilingues
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.stats = EmbeddingStats()
        
        # Configuration des modèles
        self.primary_model_name = self.config.get(
            "primary_model", 
            EmbeddingModel.MULTILINGUAL_MINILM.value
        )
        self.fallback_model_name = self.config.get(
            "fallback_model",
            EmbeddingModel.DISTILUSE_MULTILINGUAL.value
        )
        
        # Modèles d'embeddings
        self.primary_model = None
        self.fallback_model = None
        self.custom_models = {}
        
        # Configuration des langues
        self.language_configs = self._init_language_configs()
        
        # Cache des embeddings
        self.embedding_cache = {}
        self.cache_enabled = self.config.get("cache_enabled", True)
        self.max_cache_size = self.config.get("max_cache_size", 10000)
        
        # Index FAISS pour recherche rapide
        self.faiss_index = None
        self.faiss_texts = []
        self.faiss_metadata = []
        
        # Statistiques
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Initialiser les modèles
        self._init_models()
        
        logger.info("Système d'embeddings multilingues initialisé")
    
    def _init_language_configs(self) -> Dict[str, LanguageConfig]:
        """Initialise les configurations des langues"""
        configs = {
            "fr": LanguageConfig(
                code="fr",
                name="Français",
                family=LanguageFamily.ROMANCE,
                embedding_weight=1.0,
                preprocessing_rules=["lowercase", "remove_accents_optional"],
                special_tokens={"medical_prefix": "[MED_FR]"},
                medical_terms_boost=1.3,
                chunking_strategy="sentence",
                max_sequence_length=512
            ),
            
            "en": LanguageConfig(
                code="en",
                name="English",
                family=LanguageFamily.GERMANIC,
                embedding_weight=0.9,
                preprocessing_rules=["lowercase"],
                special_tokens={"medical_prefix": "[MED_EN]"},
                medical_terms_boost=1.2,
                chunking_strategy="sentence",
                max_sequence_length=512
            ),
            
            "ff": LanguageConfig(
                code="ff",
                name="Fulfulde",
                family=LanguageFamily.NIGER_CONGO,
                embedding_weight=1.1,  # Boost pour langue locale
                preprocessing_rules=["preserve_tone", "handle_diacritics"],
                special_tokens={"medical_prefix": "[MED_FF]"},
                medical_terms_boost=1.4,  # Boost élevé pour termes médicaux locaux
                chunking_strategy="custom",
                max_sequence_length=256  # Séquences plus courtes
            ),
            
            "ewondo": LanguageConfig(
                code="ewondo",
                name="Ewondo",
                family=LanguageFamily.NIGER_CONGO,
                embedding_weight=1.1,
                preprocessing_rules=["preserve_tone", "handle_nasalization"],
                special_tokens={"medical_prefix": "[MED_EWO]"},
                medical_terms_boost=1.4,
                chunking_strategy="custom",
                max_sequence_length=256
            ),
            
            "duala": LanguageConfig(
                code="duala",
                name="Duala",
                family=LanguageFamily.NIGER_CONGO,
                embedding_weight=1.1,
                preprocessing_rules=["preserve_tone"],
                special_tokens={"medical_prefix": "[MED_DUA]"},
                medical_terms_boost=1.4,
                chunking_strategy="custom",
                max_sequence_length=256
            ),
            
            "bamileke": LanguageConfig(
                code="bamileke",
                name="Bamiléké",
                family=LanguageFamily.NIGER_CONGO,
                embedding_weight=1.1,
                preprocessing_rules=["preserve_tone", "handle_variants"],
                special_tokens={"medical_prefix": "[MED_BAM]"},
                medical_terms_boost=1.4,
                chunking_strategy="custom",
                max_sequence_length=256
            ),
            
            "ha": LanguageConfig(
                code="ha",
                name="Hausa",
                family=LanguageFamily.AFROASIATIC,
                embedding_weight=1.0,
                preprocessing_rules=["handle_arabic_script", "preserve_tone"],
                special_tokens={"medical_prefix": "[MED_HA]"},
                medical_terms_boost=1.3,
                chunking_strategy="sentence",
                max_sequence_length=384
            ),
            
            "ar": LanguageConfig(
                code="ar",
                name="العربية",
                family=LanguageFamily.AFROASIATIC,
                embedding_weight=0.9,
                preprocessing_rules=["handle_rtl", "normalize_arabic"],
                special_tokens={"medical_prefix": "[MED_AR]"},
                medical_terms_boost=1.2,
                chunking_strategy="sentence",
                max_sequence_length=512
            )
        }
        
        return configs
    
    def _init_models(self):
        """Initialise les modèles d'embeddings"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.warning("Mode simulation activé - sentence-transformers non disponible")
            return
        
        try:
            # Modèle principal
            logger.info(f"Chargement du modèle principal: {self.primary_model_name}")
            self.primary_model = SentenceTransformer(self.primary_model_name)
            
            # Modèle de fallback
            if self.fallback_model_name != self.primary_model_name:
                logger.info(f"Chargement du modèle de fallback: {self.fallback_model_name}")
                self.fallback_model = SentenceTransformer(self.fallback_model_name)
            
            # Optimisations GPU si disponible
            if torch.cuda.is_available():
                device = torch.device('cuda')
                self.primary_model = self.primary_model.to(device)
                if self.fallback_model:
                    self.fallback_model = self.fallback_model.to(device)
                logger.info("Modèles déplacés sur GPU")
            
            logger.info("Modèles d'embeddings initialisés avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des modèles: {e}")
            self.primary_model = None
            self.fallback_model = None
    
    def _preprocess_text(self, text: str, language: str) -> str:
        """Préprocesse le texte selon la langue"""
        if language not in self.language_configs:
            return text
        
        config = self.language_configs[language]
        processed_text = text
        
        # Appliquer les règles de préprocessing
        for rule in config.preprocessing_rules:
            if rule == "lowercase":
                processed_text = processed_text.lower()
            elif rule == "remove_accents_optional":
                # Garder les accents pour le français médical
                pass
            elif rule == "preserve_tone":
                # Préserver les marques tonales pour les langues camerounaises
                pass
            elif rule == "handle_diacritics":
                # Normaliser les diacritiques
                import unicodedata
                processed_text = unicodedata.normalize('NFC', processed_text)
            elif rule == "handle_rtl":
                # Gérer le texte de droite à gauche (arabe)
                processed_text = processed_text.strip()
            elif rule == "normalize_arabic":
                # Normalisation spécifique à l'arabe
                processed_text = processed_text.replace('ي', 'ى').replace('ك', 'ک')
        
        # Ajouter le préfixe médical si configuré
        if "medical_prefix" in config.special_tokens:
            if self._is_medical_text(processed_text):
                prefix = config.special_tokens["medical_prefix"]
                processed_text = f"{prefix} {processed_text}"
        
        return processed_text
    
    def _is_medical_text(self, text: str) -> bool:
        """Détermine si un texte est médical"""
        medical_keywords = {
            "fr": ["maladie", "symptôme", "traitement", "diagnostic", "patient", "médecin", 
                   "hôpital", "médicament", "thérapie", "clinique", "pathologie", "syndrome"],
            "en": ["disease", "symptom", "treatment", "diagnosis", "patient", "doctor",
                   "hospital", "medication", "therapy", "clinic", "pathology", "syndrome"],
            "ff": ["nayeejo", "alamaaji", "fuɗɗoode", "dokotoro", "jammirgal"],
            "ewondo": ["bela", "dokita", "bilinga", "nkukuma"],
            "duala": ["bwele", "dokita", "ndimba", "lopital"],
            "bamileke": ["nkeng", "dokita", "nda", "lopital"],
            "ha": ["cuta", "alamomi", "magani", "likita", "asibiti"],
            "ar": ["مرض", "عرض", "علاج", "تشخيص", "مريض", "طبيب", "مستشفى"]
        }
        
        text_lower = text.lower()
        
        # Vérifier dans toutes les langues
        for lang_keywords in medical_keywords.values():
            if any(keyword.lower() in text_lower for keyword in lang_keywords):
                return True
        
        return False
    
    def _get_text_hash(self, text: str, language: str, model_name: str) -> str:
        """Génère un hash pour le cache"""
        content = f"{text}_{language}_{model_name}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _simulate_embedding(self, text: str, language: str) -> np.ndarray:
        """Simule un embedding quand les modèles ne sont pas disponibles"""
        # Générer un embedding simulé basé sur le texte et la langue
        import random
        random.seed(hash(text + language) % (2**32))
        
        # Dimension standard pour les modèles multilingues
        dimension = 384
        embedding = np.array([random.gauss(0, 1) for _ in range(dimension)])
        
        # Normaliser
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding.astype(np.float32)
    
    async def encode_text(self, text: str, language: str = "fr", 
                         model_preference: Optional[str] = None) -> EmbeddingResult:
        """
        Encode un texte en embedding multilingue
        
        Args:
            text: Texte à encoder
            language: Langue du texte
            model_preference: Modèle préféré (optionnel)
        
        Returns:
            EmbeddingResult: Résultat de l'encoding
        """
        import time
        start_time = time.time()
        
        try:
            # Vérifier le cache
            model_name = model_preference or self.primary_model_name
            cache_key = self._get_text_hash(text, language, model_name)
            
            if self.cache_enabled and cache_key in self.embedding_cache:
                self.cache_hits += 1
                cached_result = self.embedding_cache[cache_key]
                cached_result.metadata["from_cache"] = True
                return cached_result
            
            self.cache_misses += 1
            
            # Préprocesser le texte
            processed_text = self._preprocess_text(text, language)
            
            # Choisir le modèle
            model = self.primary_model
            model_used = self.primary_model_name
            
            if model_preference and model_preference in self.custom_models:
                model = self.custom_models[model_preference]
                model_used = model_preference
            elif not model and self.fallback_model:
                model = self.fallback_model
                model_used = self.fallback_model_name
            
            # Générer l'embedding
            if model and SENTENCE_TRANSFORMERS_AVAILABLE:
                embedding = model.encode(processed_text, convert_to_numpy=True)
                confidence = 0.9  # Confiance élevée pour les vrais modèles
            else:
                # Mode simulation
                embedding = self._simulate_embedding(processed_text, language)
                confidence = 0.5  # Confiance réduite pour la simulation
                model_used = "simulation"
            
            # Appliquer le poids de la langue
            if language in self.language_configs:
                weight = self.language_configs[language].embedding_weight
                embedding = embedding * weight
            
            # Boost médical si applicable
            if self._is_medical_text(text) and language in self.language_configs:
                boost = self.language_configs[language].medical_terms_boost
                embedding = embedding * boost
                confidence = min(confidence * 1.1, 1.0)
            
            processing_time = time.time() - start_time
            
            # Créer le résultat
            result = EmbeddingResult(
                text=text,
                language=language,
                embedding=embedding,
                confidence=confidence,
                processing_time=processing_time,
                model_used=model_used,
                metadata={
                    "processed_text": processed_text,
                    "embedding_dimension": len(embedding),
                    "language_family": self.language_configs.get(language, LanguageConfig("", "", LanguageFamily.MIXED)).family.value,
                    "from_cache": False
                }
            )
            
            # Mettre en cache
            if self.cache_enabled and len(self.embedding_cache) < self.max_cache_size:
                self.embedding_cache[cache_key] = result
            
            # Mettre à jour les statistiques
            self.stats.total_embeddings += 1
            self.stats.embeddings_by_language[language] = self.stats.embeddings_by_language.get(language, 0) + 1
            
            return result
        
        except Exception as e:
            logger.error(f"Erreur lors de l'encoding: {e}")
            # Retourner un embedding par défaut
            return EmbeddingResult(
                text=text,
                language=language,
                embedding=np.zeros(384, dtype=np.float32),
                confidence=0.0,
                processing_time=time.time() - start_time,
                model_used="error",
                metadata={"error": str(e)}
            )
    
    async def encode_batch(self, texts: List[str], languages: List[str] = None,
                          model_preference: Optional[str] = None) -> List[EmbeddingResult]:
        """
        Encode un batch de textes
        
        Args:
            texts: Liste de textes à encoder
            languages: Langues correspondantes (optionnel)
            model_preference: Modèle préféré (optionnel)
        
        Returns:
            List[EmbeddingResult]: Résultats d'encoding
        """
        if languages is None:
            languages = ["fr"] * len(texts)
        elif len(languages) == 1:
            languages = languages * len(texts)
        
        # Traitement en parallèle
        tasks = [
            self.encode_text(text, lang, model_preference)
            for text, lang in zip(texts, languages)
        ]
        
        results = await asyncio.gather(*tasks)
        return results
    
    def calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray,
                           language1: str = "fr", language2: str = "fr") -> SimilarityResult:
        """
        Calcule la similarité entre deux embeddings
        
        Args:
            embedding1: Premier embedding
            embedding2: Deuxième embedding
            language1: Langue du premier texte
            language2: Langue du deuxième texte
        
        Returns:
            SimilarityResult: Résultat de similarité
        """
        try:
            # Similarité cosinus
            dot_product = np.dot(embedding1, embedding2)
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                similarity = 0.0
            else:
                similarity = dot_product / (norm1 * norm2)
            
            # Ajustement pour les langues différentes
            cross_lingual = language1 != language2
            if cross_lingual:
                # Réduction de la similarité pour les langues différentes
                family1 = self.language_configs.get(language1, LanguageConfig("", "", LanguageFamily.MIXED)).family
                family2 = self.language_configs.get(language2, LanguageConfig("", "", LanguageFamily.MIXED)).family
                
                if family1 == family2:
                    # Même famille de langues
                    similarity *= 0.9
                else:
                    # Familles différentes
                    similarity *= 0.8
                
                self.stats.cross_lingual_queries += 1
            
            # Confiance basée sur la similarité
            confidence = abs(similarity)
            
            return SimilarityResult(
                query_text="",  # Sera rempli par l'appelant
                target_text="",
                similarity_score=float(similarity),
                query_language=language1,
                target_language=language2,
                cross_lingual=cross_lingual,
                confidence=confidence,
                metadata={
                    "language_family_match": family1 == family2 if cross_lingual else True,
                    "embedding_dimensions": (len(embedding1), len(embedding2))
                }
            )
        
        except Exception as e:
            logger.error(f"Erreur lors du calcul de similarité: {e}")
            return SimilarityResult(
                query_text="",
                target_text="",
                similarity_score=0.0,
                query_language=language1,
                target_language=language2,
                cross_lingual=cross_lingual,
                confidence=0.0,
                metadata={"error": str(e)}
            )
    
    def build_faiss_index(self, embeddings: List[np.ndarray], texts: List[str],
                         metadata: List[Dict[str, Any]] = None):
        """
        Construit un index FAISS pour la recherche rapide
        
        Args:
            embeddings: Liste d'embeddings
            texts: Textes correspondants
            metadata: Métadonnées optionnelles
        """
        if not FAISS_AVAILABLE:
            logger.warning("FAISS non disponible, index non créé")
            return
        
        try:
            if not embeddings:
                logger.warning("Aucun embedding fourni pour l'index")
                return
            
            # Convertir en matrice numpy
            embedding_matrix = np.vstack(embeddings).astype('float32')
            dimension = embedding_matrix.shape[1]
            
            # Créer l'index FAISS
            self.faiss_index = faiss.IndexFlatIP(dimension)  # Inner Product (cosine similarity)
            
            # Normaliser les embeddings pour la similarité cosinus
            faiss.normalize_L2(embedding_matrix)
            
            # Ajouter à l'index
            self.faiss_index.add(embedding_matrix)
            
            # Stocker les textes et métadonnées
            self.faiss_texts = texts.copy()
            self.faiss_metadata = metadata.copy() if metadata else [{} for _ in texts]
            
            logger.info(f"Index FAISS créé avec {len(embeddings)} embeddings")
        
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'index FAISS: {e}")
    
    def search_similar(self, query_embedding: np.ndarray, top_k: int = 10,
                      threshold: float = 0.7) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Recherche les embeddings les plus similaires
        
        Args:
            query_embedding: Embedding de requête
            top_k: Nombre de résultats à retourner
            threshold: Seuil de similarité minimum
        
        Returns:
            List[Tuple[str, float, Dict]]: (texte, score, métadonnées)
        """
        if not self.faiss_index:
            logger.warning("Index FAISS non disponible")
            return []
        
        try:
            # Normaliser l'embedding de requête
            query_norm = query_embedding.copy().astype('float32')
            query_norm = query_norm.reshape(1, -1)
            faiss.normalize_L2(query_norm)
            
            # Rechercher
            scores, indices = self.faiss_index.search(query_norm, top_k)
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx != -1 and score >= threshold:
                    text = self.faiss_texts[idx]
                    metadata = self.faiss_metadata[idx]
                    results.append((text, float(score), metadata))
            
            return results
        
        except Exception as e:
            logger.error(f"Erreur lors de la recherche: {e}")
            return []
    
    def add_custom_model(self, name: str, model_path: str):
        """
        Ajoute un modèle personnalisé
        
        Args:
            name: Nom du modèle
            model_path: Chemin vers le modèle
        """
        try:
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                model = SentenceTransformer(model_path)
                self.custom_models[name] = model
                logger.info(f"Modèle personnalisé ajouté: {name}")
            else:
                logger.warning("sentence-transformers non disponible")
        
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du modèle {name}: {e}")
    
    def generate_stats(self) -> EmbeddingStats:
        """Génère les statistiques des embeddings"""
        import time
        start_time = time.time()
        
        # Calculer le taux de cache
        total_requests = self.cache_hits + self.cache_misses
        if total_requests > 0:
            self.stats.cache_hit_rate = self.cache_hits / total_requests
        
        # Moyennes (simulées pour l'exemple)
        if self.stats.total_embeddings > 0:
            self.stats.avg_processing_time = 0.1  # Moyenne simulée
            self.stats.avg_confidence = 0.85  # Confiance moyenne simulée
        
        # Performance des modèles
        self.stats.model_performance = {
            self.primary_model_name: 0.9,
            "simulation": 0.5
        }
        
        self.stats.processing_time = time.time() - start_time
        
        return self.stats
    
    def export_embeddings(self, output_path: str):
        """Exporte les embeddings et métadonnées"""
        export_data = {
            "metadata": {
                "total_embeddings": self.stats.total_embeddings,
                "supported_languages": list(self.language_configs.keys()),
                "primary_model": self.primary_model_name,
                "export_date": datetime.now().isoformat(),
                "version": "2.0.0"
            },
            "language_configs": {
                lang: {
                    "name": config.name,
                    "family": config.family.value,
                    "embedding_weight": config.embedding_weight,
                    "medical_terms_boost": config.medical_terms_boost,
                    "max_sequence_length": config.max_sequence_length
                }
                for lang, config in self.language_configs.items()
            },
            "statistics": {
                "embeddings_by_language": self.stats.embeddings_by_language,
                "cache_hit_rate": self.stats.cache_hit_rate,
                "cross_lingual_queries": self.stats.cross_lingual_queries,
                "avg_confidence": self.stats.avg_confidence
            },
            "cache_info": {
                "cache_size": len(self.embedding_cache),
                "max_cache_size": self.max_cache_size,
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Embeddings exportés: {output_path}")
    
    def clear_cache(self):
        """Vide le cache des embeddings"""
        self.embedding_cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        logger.info("Cache des embeddings vidé")

# Test de démonstration
async def main():
    """Fonction de test principale"""
    print("🌍 Test des Embeddings Multilingues")
    
    # Créer le système d'embeddings
    embeddings = MultilingualEmbeddings({
        "cache_enabled": True,
        "max_cache_size": 1000
    })
    
    # Textes de test multilingues
    test_texts = [
        ("Le paludisme est une maladie parasitaire transmise par les moustiques.", "fr"),
        ("Malaria is a parasitic disease transmitted by mosquitoes.", "en"),
        ("Nayeejo paludisme ko nayeejo ɓurɗo mo anopheles ɗon haɓa.", "ff"),
        ("Bela paludisme e bela be ba kobe na nyon anopheles.", "ewondo"),
        ("المالاريا مرض طفيلي ينتقل عن طريق البعوض.", "ar")
    ]
    
    print(f"\n📝 Test d'encoding de {len(test_texts)} textes:")
    
    # Encoder les textes
    results = []
    for text, lang in test_texts:
        result = await embeddings.encode_text(text, lang)
        results.append(result)
        
        print(f"  {embeddings.language_configs[lang].name}: {text[:50]}...")
        print(f"    Dimension: {len(result.embedding)}, Confiance: {result.confidence:.2f}")
        print(f"    Temps: {result.processing_time:.3f}s, Modèle: {result.model_used}")
    
    # Test de similarité cross-linguale
    print("\n🔗 Test de similarité cross-linguale:")
    fr_embedding = results[0].embedding
    en_embedding = results[1].embedding
    
    similarity = embeddings.calculate_similarity(fr_embedding, en_embedding, "fr", "en")
    print(f"  Français ↔ Anglais: {similarity.similarity_score:.3f}")
    print(f"  Cross-lingual: {similarity.cross_lingual}")
    print(f"  Confiance: {similarity.confidence:.3f}")
    
    # Test de batch encoding
    print("\n📦 Test d'encoding en batch:")
    batch_texts = [text for text, _ in test_texts[:3]]
    batch_langs = [lang for _, lang in test_texts[:3]]
    
    batch_results = await embeddings.encode_batch(batch_texts, batch_langs)
    print(f"  {len(batch_results)} textes encodés en batch")
    
    # Test de l'index FAISS
    print("\n🔍 Test de l'index FAISS:")
    all_embeddings = [r.embedding for r in results]
    all_texts = [text for text, _ in test_texts]
    all_metadata = [{"language": lang, "medical": True} for _, lang in test_texts]
    
    embeddings.build_faiss_index(all_embeddings, all_texts, all_metadata)
    
    # Recherche similaire
    query_embedding = results[0].embedding  # Texte français
    similar_results = embeddings.search_similar(query_embedding, top_k=3, threshold=0.5)
    
    print(f"  Résultats similaires trouvés: {len(similar_results)}")
    for text, score, metadata in similar_results:
        print(f"    Score: {score:.3f} - {text[:50]}... ({metadata.get('language', 'unknown')})")
    
    # Générer les statistiques
    stats = embeddings.generate_stats()
    print(f"\n📊 Statistiques:")
    print(f"  Embeddings totaux: {stats.total_embeddings}")
    print(f"  Taux de cache: {stats.cache_hit_rate:.1%}")
    print(f"  Requêtes cross-linguales: {stats.cross_lingual_queries}")
    print(f"  Confiance moyenne: {stats.avg_confidence:.2f}")
    
    print(f"\n🌐 Répartition par langue:")
    for lang, count in stats.embeddings_by_language.items():
        lang_name = embeddings.language_configs[lang].name
        print(f"  {lang_name} ({lang}): {count} embeddings")
    
    # Exporter les données
    embeddings.export_embeddings("multilingual_embeddings_export.json")
    print("\n✅ Données exportées: multilingual_embeddings_export.json")

if __name__ == "__main__":
    asyncio.run(main())