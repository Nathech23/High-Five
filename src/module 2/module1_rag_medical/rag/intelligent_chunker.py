#!/usr/bin/env python3
"""
Chunking Intelligent pour Documents Médicaux

Ce module implémente un système de chunking intelligent spécialement conçu
pour les documents médicaux, prenant en compte la structure sémantique
et les spécificités du domaine médical.
"""

import re
import logging
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import spacy
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ChunkMetadata:
    """Métadonnées pour un chunk de document"""
    chunk_id: str
    document_id: str
    chunk_index: int
    start_char: int
    end_char: int
    word_count: int
    sentence_count: int
    medical_terms: List[str]
    section_type: str  # introduction, symptoms, treatment, etc.
    importance_score: float
    semantic_density: float
    overlap_with_previous: int
    overlap_with_next: int

@dataclass
class IntelligentChunk:
    """Chunk intelligent avec métadonnées enrichies"""
    content: str
    metadata: ChunkMetadata
    embedding_vector: Optional[np.ndarray] = None
    semantic_keywords: List[str] = None
    medical_entities: List[Dict[str, Any]] = None

class MedicalDocumentChunker:
    """
    Chunker intelligent pour documents médicaux
    
    Utilise une approche hybride combinant:
    - Segmentation basée sur la structure du document
    - Analyse sémantique pour préserver la cohérence
    - Reconnaissance d'entités médicales
    - Optimisation de la taille des chunks
    """
    
    def __init__(self, 
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200,
                 min_chunk_size: int = 100,
                 max_chunk_size: int = 2000,
                 language: str = "fr"):
        """
        Initialise le chunker intelligent
        
        Args:
            chunk_size: Taille cible des chunks en caractères
            chunk_overlap: Chevauchement entre chunks en caractères
            min_chunk_size: Taille minimale d'un chunk
            max_chunk_size: Taille maximale d'un chunk
            language: Langue du document (fr, en)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.language = language
        
        # Initialisation des outils NLP
        self._init_nlp_tools()
        
        # Patterns médicaux
        self._init_medical_patterns()
        
        # Splitter de base
        self.base_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", "! ", "? ", "; ", ": ", " ", ""]
        )
        
        logger.info(f"Chunker intelligent initialisé (taille: {chunk_size}, overlap: {chunk_overlap})")
    
    def _init_nlp_tools(self):
        """Initialise les outils de traitement du langage naturel"""
        try:
            # Modèle spaCy
            if self.language == "fr":
                self.nlp = spacy.load("fr_core_news_sm")
            else:
                self.nlp = spacy.load("en_core_web_sm")
            
            # Données NLTK
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt')
            
            try:
                nltk.data.find('corpora/stopwords')
            except LookupError:
                nltk.download('stopwords')
            
            self.stop_words = set(stopwords.words('french' if self.language == 'fr' else 'english'))
            
        except Exception as e:
            logger.warning(f"Erreur lors de l'initialisation NLP: {e}")
            self.nlp = None
            self.stop_words = set()
    
    def _init_medical_patterns(self):
        """Initialise les patterns pour la reconnaissance médicale"""
        # Patterns pour sections médicales
        self.section_patterns = {
            'symptoms': re.compile(r'(symptômes?|signes?|manifestations?|présentation clinique)', re.IGNORECASE),
            'diagnosis': re.compile(r'(diagnostic|diagnose|identification|détection)', re.IGNORECASE),
            'treatment': re.compile(r'(traitement|thérapie|médication|prescription|soins)', re.IGNORECASE),
            'prevention': re.compile(r'(prévention|prophylaxie|mesures préventives)', re.IGNORECASE),
            'causes': re.compile(r'(causes?|étiologie|facteurs de risque|origine)', re.IGNORECASE),
            'complications': re.compile(r'(complications?|séquelles|effets secondaires)', re.IGNORECASE)
        }
        
        # Termes médicaux importants
        self.medical_terms = {
            'fr': [
                'maladie', 'pathologie', 'syndrome', 'infection', 'inflammation',
                'diagnostic', 'traitement', 'médicament', 'posologie', 'dosage',
                'symptôme', 'signe', 'manifestation', 'complication', 'séquelle',
                'prévention', 'prophylaxie', 'vaccination', 'immunisation',
                'patient', 'malade', 'sujet', 'cas', 'individu',
                'médecin', 'docteur', 'praticien', 'spécialiste', 'clinicien'
            ],
            'en': [
                'disease', 'pathology', 'syndrome', 'infection', 'inflammation',
                'diagnosis', 'treatment', 'medication', 'dosage', 'dose',
                'symptom', 'sign', 'manifestation', 'complication', 'sequela',
                'prevention', 'prophylaxis', 'vaccination', 'immunization',
                'patient', 'subject', 'case', 'individual',
                'doctor', 'physician', 'practitioner', 'specialist', 'clinician'
            ]
        }
    
    def chunk_document(self, 
                      document: str, 
                      document_id: str = None,
                      metadata: Dict[str, Any] = None) -> List[IntelligentChunk]:
        """
        Découpe un document en chunks intelligents
        
        Args:
            document: Texte du document à découper
            document_id: Identifiant unique du document
            metadata: Métadonnées du document
            
        Returns:
            Liste de chunks intelligents
        """
        if not document or len(document.strip()) < self.min_chunk_size:
            return []
        
        logger.info(f"Début du chunking pour document {document_id} ({len(document)} caractères)")
        
        # Préprocessing du document
        cleaned_document = self._preprocess_document(document)
        
        # Détection de la structure du document
        document_structure = self._analyze_document_structure(cleaned_document)
        
        # Chunking adaptatif basé sur la structure
        if document_structure['has_clear_sections']:
            chunks = self._chunk_by_sections(cleaned_document, document_structure)
        else:
            chunks = self._chunk_by_semantics(cleaned_document)
        
        # Post-traitement et optimisation
        optimized_chunks = self._optimize_chunks(chunks)
        
        # Création des chunks intelligents avec métadonnées
        intelligent_chunks = []
        for i, chunk_content in enumerate(optimized_chunks):
            chunk_metadata = self._create_chunk_metadata(
                chunk_content, i, document_id, document, metadata
            )
            
            intelligent_chunk = IntelligentChunk(
                content=chunk_content,
                metadata=chunk_metadata,
                semantic_keywords=self._extract_semantic_keywords(chunk_content),
                medical_entities=self._extract_medical_entities(chunk_content)
            )
            
            intelligent_chunks.append(intelligent_chunk)
        
        # Calcul des overlaps entre chunks adjacents
        self._calculate_overlaps(intelligent_chunks)
        
        logger.info(f"Chunking terminé: {len(intelligent_chunks)} chunks créés")
        return intelligent_chunks
    
    def _preprocess_document(self, document: str) -> str:
        """Préprocessing du document"""
        # Normalisation des espaces
        document = re.sub(r'\s+', ' ', document)
        
        # Suppression des caractères de contrôle
        document = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', document)
        
        # Normalisation des sauts de ligne
        document = re.sub(r'\n\s*\n', '\n\n', document)
        
        return document.strip()
    
    def _analyze_document_structure(self, document: str) -> Dict[str, Any]:
        """Analyse la structure du document"""
        structure = {
            'has_clear_sections': False,
            'sections': [],
            'section_boundaries': [],
            'avg_paragraph_length': 0,
            'total_paragraphs': 0
        }
        
        # Détection des sections
        lines = document.split('\n')
        section_headers = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Détection des en-têtes de section
            if (len(line) < 100 and 
                (line.isupper() or 
                 re.match(r'^\d+\.\s+[A-Z]', line) or
                 re.match(r'^[A-Z][^.!?]*:?$', line))):
                section_headers.append((i, line))
        
        if len(section_headers) >= 2:
            structure['has_clear_sections'] = True
            structure['sections'] = [header[1] for header in section_headers]
            structure['section_boundaries'] = [header[0] for header in section_headers]
        
        # Analyse des paragraphes
        paragraphs = [p.strip() for p in document.split('\n\n') if p.strip()]
        structure['total_paragraphs'] = len(paragraphs)
        if paragraphs:
            structure['avg_paragraph_length'] = sum(len(p) for p in paragraphs) / len(paragraphs)
        
        return structure
    
    def _chunk_by_sections(self, document: str, structure: Dict[str, Any]) -> List[str]:
        """Chunking basé sur les sections du document"""
        chunks = []
        lines = document.split('\n')
        section_boundaries = structure['section_boundaries'] + [len(lines)]
        
        for i in range(len(section_boundaries) - 1):
            start_line = section_boundaries[i]
            end_line = section_boundaries[i + 1]
            
            section_content = '\n'.join(lines[start_line:end_line]).strip()
            
            if len(section_content) > self.max_chunk_size:
                # Section trop grande, la subdiviser
                section_chunks = self._chunk_by_semantics(section_content)
                chunks.extend(section_chunks)
            elif len(section_content) >= self.min_chunk_size:
                chunks.append(section_content)
        
        return chunks
    
    def _chunk_by_semantics(self, text: str) -> List[str]:
        """Chunking basé sur la sémantique"""
        # Utilisation du splitter de base avec optimisations
        base_chunks = self.base_splitter.split_text(text)
        
        # Optimisation sémantique
        optimized_chunks = []
        
        for chunk in base_chunks:
            if len(chunk) < self.min_chunk_size and optimized_chunks:
                # Fusionner avec le chunk précédent si trop petit
                optimized_chunks[-1] += " " + chunk
            else:
                optimized_chunks.append(chunk)
        
        return optimized_chunks
    
    def _optimize_chunks(self, chunks: List[str]) -> List[str]:
        """Optimise les chunks pour améliorer la cohérence sémantique"""
        if not chunks:
            return chunks
        
        optimized = []
        
        for chunk in chunks:
            # Vérification de la cohérence sémantique
            if self._is_semantically_coherent(chunk):
                optimized.append(chunk)
            else:
                # Tentative de réorganisation
                reorganized = self._reorganize_chunk(chunk)
                optimized.extend(reorganized)
        
        return optimized
    
    def _is_semantically_coherent(self, chunk: str) -> bool:
        """Vérifie la cohérence sémantique d'un chunk"""
        if not self.nlp:
            return True
        
        sentences = sent_tokenize(chunk, language='french' if self.language == 'fr' else 'english')
        
        if len(sentences) < 2:
            return True
        
        # Analyse de la cohérence thématique
        try:
            vectorizer = TfidfVectorizer(stop_words=list(self.stop_words), max_features=100)
            sentence_vectors = vectorizer.fit_transform(sentences)
            
            # Calcul de la similarité moyenne entre phrases
            similarities = []
            for i in range(len(sentences) - 1):
                sim = cosine_similarity(
                    sentence_vectors[i:i+1], 
                    sentence_vectors[i+1:i+2]
                )[0][0]
                similarities.append(sim)
            
            avg_similarity = np.mean(similarities) if similarities else 0
            return avg_similarity > 0.1  # Seuil de cohérence
            
        except Exception:
            return True
    
    def _reorganize_chunk(self, chunk: str) -> List[str]:
        """Réorganise un chunk incohérent"""
        sentences = sent_tokenize(chunk, language='french' if self.language == 'fr' else 'english')
        
        if len(sentences) <= 2:
            return [chunk]
        
        # Regroupement par similarité sémantique
        reorganized_chunks = []
        current_chunk = sentences[0]
        
        for i in range(1, len(sentences)):
            if len(current_chunk) + len(sentences[i]) < self.max_chunk_size:
                current_chunk += " " + sentences[i]
            else:
                if len(current_chunk) >= self.min_chunk_size:
                    reorganized_chunks.append(current_chunk)
                current_chunk = sentences[i]
        
        if current_chunk and len(current_chunk) >= self.min_chunk_size:
            reorganized_chunks.append(current_chunk)
        elif reorganized_chunks:
            reorganized_chunks[-1] += " " + current_chunk
        
        return reorganized_chunks or [chunk]
    
    def _create_chunk_metadata(self, 
                              chunk_content: str, 
                              chunk_index: int, 
                              document_id: str,
                              full_document: str,
                              doc_metadata: Dict[str, Any] = None) -> ChunkMetadata:
        """Crée les métadonnées pour un chunk"""
        # Position dans le document
        start_char = full_document.find(chunk_content[:50])  # Approximation
        end_char = start_char + len(chunk_content)
        
        # Statistiques de base
        word_count = len(chunk_content.split())
        sentence_count = len(sent_tokenize(chunk_content, language='french' if self.language == 'fr' else 'english'))
        
        # Extraction des termes médicaux
        medical_terms = self._extract_medical_terms(chunk_content)
        
        # Type de section
        section_type = self._identify_section_type(chunk_content)
        
        # Score d'importance
        importance_score = self._calculate_importance_score(chunk_content, medical_terms)
        
        # Densité sémantique
        semantic_density = self._calculate_semantic_density(chunk_content)
        
        return ChunkMetadata(
            chunk_id=f"{document_id}_{chunk_index}" if document_id else f"chunk_{chunk_index}",
            document_id=document_id or "unknown",
            chunk_index=chunk_index,
            start_char=max(0, start_char),
            end_char=end_char,
            word_count=word_count,
            sentence_count=sentence_count,
            medical_terms=medical_terms,
            section_type=section_type,
            importance_score=importance_score,
            semantic_density=semantic_density,
            overlap_with_previous=0,  # Sera calculé plus tard
            overlap_with_next=0       # Sera calculé plus tard
        )
    
    def _extract_medical_terms(self, text: str) -> List[str]:
        """Extrait les termes médicaux du texte"""
        terms = []
        text_lower = text.lower()
        
        medical_vocab = self.medical_terms.get(self.language, [])
        
        for term in medical_vocab:
            if term.lower() in text_lower:
                terms.append(term)
        
        return list(set(terms))
    
    def _identify_section_type(self, text: str) -> str:
        """Identifie le type de section du chunk"""
        for section_type, pattern in self.section_patterns.items():
            if pattern.search(text):
                return section_type
        
        return "general"
    
    def _calculate_importance_score(self, text: str, medical_terms: List[str]) -> float:
        """Calcule un score d'importance pour le chunk"""
        score = 0.0
        
        # Bonus pour les termes médicaux
        score += len(medical_terms) * 0.1
        
        # Bonus pour la longueur optimale
        if self.chunk_size * 0.8 <= len(text) <= self.chunk_size * 1.2:
            score += 0.2
        
        # Bonus pour les phrases complètes
        sentences = sent_tokenize(text, language='french' if self.language == 'fr' else 'english')
        if sentences and text.strip().endswith(('.', '!', '?')):
            score += 0.1
        
        return min(1.0, score)
    
    def _calculate_semantic_density(self, text: str) -> float:
        """Calcule la densité sémantique du chunk"""
        if not text.strip():
            return 0.0
        
        words = word_tokenize(text.lower())
        content_words = [w for w in words if w not in self.stop_words and w.isalpha()]
        
        if not words:
            return 0.0
        
        return len(content_words) / len(words)
    
    def _extract_semantic_keywords(self, text: str) -> List[str]:
        """Extrait les mots-clés sémantiques du chunk"""
        if not self.nlp:
            return []
        
        try:
            doc = self.nlp(text)
            keywords = []
            
            # Extraction des entités nommées
            for ent in doc.ents:
                if ent.label_ in ['PERSON', 'ORG', 'MISC', 'LOC']:
                    keywords.append(ent.text)
            
            # Extraction des termes importants (noms et adjectifs)
            for token in doc:
                if (token.pos_ in ['NOUN', 'ADJ'] and 
                    not token.is_stop and 
                    not token.is_punct and 
                    len(token.text) > 3):
                    keywords.append(token.lemma_)
            
            return list(set(keywords))[:10]  # Limiter à 10 mots-clés
            
        except Exception as e:
            logger.warning(f"Erreur lors de l'extraction des mots-clés: {e}")
            return []
    
    def _extract_medical_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extrait les entités médicales du chunk"""
        if not self.nlp:
            return []
        
        try:
            doc = self.nlp(text)
            entities = []
            
            for ent in doc.ents:
                entity_info = {
                    'text': ent.text,
                    'label': ent.label_,
                    'start': ent.start_char,
                    'end': ent.end_char,
                    'confidence': getattr(ent, 'confidence', 1.0)
                }
                entities.append(entity_info)
            
            return entities
            
        except Exception as e:
            logger.warning(f"Erreur lors de l'extraction des entités: {e}")
            return []
    
    def _calculate_overlaps(self, chunks: List[IntelligentChunk]):
        """Calcule les chevauchements entre chunks adjacents"""
        for i in range(len(chunks)):
            if i > 0:
                # Overlap avec le chunk précédent
                prev_content = chunks[i-1].content
                current_content = chunks[i].content
                
                overlap = self._calculate_text_overlap(prev_content, current_content)
                chunks[i].metadata.overlap_with_previous = overlap
            
            if i < len(chunks) - 1:
                # Overlap avec le chunk suivant
                current_content = chunks[i].content
                next_content = chunks[i+1].content
                
                overlap = self._calculate_text_overlap(current_content, next_content)
                chunks[i].metadata.overlap_with_next = overlap
    
    def _calculate_text_overlap(self, text1: str, text2: str) -> int:
        """Calcule le chevauchement en caractères entre deux textes"""
        # Recherche du plus long suffixe de text1 qui est préfixe de text2
        max_overlap = min(len(text1), len(text2), self.chunk_overlap * 2)
        
        for i in range(max_overlap, 0, -1):
            if text1[-i:] == text2[:i]:
                return i
        
        return 0
    
    def get_chunk_statistics(self, chunks: List[IntelligentChunk]) -> Dict[str, Any]:
        """Calcule les statistiques des chunks"""
        if not chunks:
            return {}
        
        chunk_sizes = [len(chunk.content) for chunk in chunks]
        word_counts = [chunk.metadata.word_count for chunk in chunks]
        importance_scores = [chunk.metadata.importance_score for chunk in chunks]
        semantic_densities = [chunk.metadata.semantic_density for chunk in chunks]
        
        return {
            'total_chunks': len(chunks),
            'avg_chunk_size': np.mean(chunk_sizes),
            'min_chunk_size': np.min(chunk_sizes),
            'max_chunk_size': np.max(chunk_sizes),
            'std_chunk_size': np.std(chunk_sizes),
            'avg_word_count': np.mean(word_counts),
            'avg_importance_score': np.mean(importance_scores),
            'avg_semantic_density': np.mean(semantic_densities),
            'section_types': [chunk.metadata.section_type for chunk in chunks],
            'total_medical_terms': sum(len(chunk.metadata.medical_terms) for chunk in chunks)
        }

def main():
    """Fonction de test du chunker intelligent"""
    # Exemple d'utilisation
    chunker = MedicalDocumentChunker(
        chunk_size=800,
        chunk_overlap=150,
        language="fr"
    )
    
    # Document de test
    test_document = """
    Le paludisme est une maladie potentiellement mortelle causée par des parasites 
    transmis aux humains par des piqûres de moustiques anophèles femelles infectés.
    
    SYMPTÔMES
    Les premiers symptômes du paludisme incluent la fièvre, les maux de tête et les frissons.
    Ces symptômes apparaissent généralement 10 à 15 jours après la piqûre de moustique infecté.
    
    DIAGNOSTIC
    Le diagnostic du paludisme repose sur l'examen microscopique du sang ou sur des tests 
    de diagnostic rapide. Un diagnostic précoce et un traitement approprié sont essentiels.
    
    TRAITEMENT
    Le traitement du paludisme dépend du type de parasite et de la gravité de la maladie.
    Les médicaments antipaludiques sont efficaces lorsqu'ils sont administrés rapidement.
    
    PRÉVENTION
    La prévention du paludisme comprend l'utilisation de moustiquaires imprégnées d'insecticide,
    la pulvérisation d'insecticides à l'intérieur des habitations et la chimioprophylaxie.
    """
    
    # Test du chunking
    chunks = chunker.chunk_document(test_document, "test_malaria_doc")
    
    # Affichage des résultats
    print(f"\n=== RÉSULTATS DU CHUNKING INTELLIGENT ===")
    print(f"Document original: {len(test_document)} caractères")
    print(f"Nombre de chunks créés: {len(chunks)}")
    
    for i, chunk in enumerate(chunks):
        print(f"\n--- Chunk {i+1} ---")
        print(f"Taille: {len(chunk.content)} caractères")
        print(f"Mots: {chunk.metadata.word_count}")
        print(f"Type de section: {chunk.metadata.section_type}")
        print(f"Score d'importance: {chunk.metadata.importance_score:.2f}")
        print(f"Densité sémantique: {chunk.metadata.semantic_density:.2f}")
        print(f"Termes médicaux: {chunk.metadata.medical_terms}")
        print(f"Mots-clés: {chunk.semantic_keywords}")
        print(f"Contenu: {chunk.content[:200]}...")
    
    # Statistiques globales
    stats = chunker.get_chunk_statistics(chunks)
    print(f"\n=== STATISTIQUES GLOBALES ===")
    for key, value in stats.items():
        print(f"{key}: {value}")

if __name__ == "__main__":
    main()