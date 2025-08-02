#!/usr/bin/env python3
"""
Processeur de données médicales pour la préparation et le nettoyage
Traite les documents collectés pour les optimiser pour les embeddings et l'indexation
"""

import json
import re
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
from collections import Counter

# Imports pour le traitement de texte
try:
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords
    from nltk.stem import SnowballStemmer
except ImportError:
    nltk = None

try:
    from textblob import TextBlob
except ImportError:
    TextBlob = None

try:
    import spacy
except ImportError:
    spacy = None

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ProcessedDocument:
    """Structure pour un document médical traité"""
    # Informations de base
    title: str
    content: str
    cleaned_content: str
    summary: str
    
    # Métadonnées originales
    original_url: str
    source: str
    category: str
    specialty: Optional[str]
    document_type: str
    language: str
    
    # Traitement
    keywords: List[str]
    medical_terms: List[str]
    key_sentences: List[str]
    content_sections: Dict[str, str]
    
    # Qualité et validation
    quality_score: float
    readability_score: float
    medical_accuracy_score: float
    content_length: int
    
    # Métadonnées de traitement
    processing_date: datetime
    processing_version: str
    file_hash: str
    
    # Structuration
    structured_data: Dict[str, Any]
    target_audience: str
    complexity_level: str

class MedicalDataProcessor:
    """Processeur principal pour les données médicales"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.processing_version = "1.0.0"
        
        # Configuration de traitement
        self.min_content_length = config.get('min_content_length', 300)
        self.max_content_length = config.get('max_content_length', 50000)
        self.target_summary_length = config.get('target_summary_length', 200)
        
        # Initialiser les outils NLP
        self._initialize_nlp_tools()
        
        # Dictionnaires médicaux
        self.medical_terms = self._load_medical_terms()
        self.medical_abbreviations = self._load_medical_abbreviations()
        self.stopwords_fr = self._load_french_stopwords()
        self.stopwords_en = self._load_english_stopwords()
        
        # Statistiques de traitement
        self.processing_stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'quality_distribution': Counter(),
            'categories': Counter(),
            'languages': Counter()
        }
    
    def _initialize_nlp_tools(self):
        """Initialise les outils de traitement NLP"""
        logger.info("🔧 Initialisation des outils NLP...")
        
        # Télécharger les ressources NLTK si nécessaire
        if nltk:
            try:
                nltk.download('punkt', quiet=True)
                nltk.download('stopwords', quiet=True)
                nltk.download('averaged_perceptron_tagger', quiet=True)
                self.nltk_available = True
                logger.info("✅ NLTK initialisé")
            except Exception as e:
                logger.warning(f"⚠️ Erreur NLTK: {e}")
                self.nltk_available = False
        else:
            self.nltk_available = False
        
        # Initialiser spaCy si disponible
        if spacy:
            try:
                # Essayer de charger le modèle français
                try:
                    self.nlp_fr = spacy.load("fr_core_news_sm")
                except OSError:
                    logger.warning("⚠️ Modèle spaCy français non trouvé")
                    self.nlp_fr = None
                
                # Essayer de charger le modèle anglais
                try:
                    self.nlp_en = spacy.load("en_core_web_sm")
                except OSError:
                    logger.warning("⚠️ Modèle spaCy anglais non trouvé")
                    self.nlp_en = None
                
                self.spacy_available = self.nlp_fr is not None or self.nlp_en is not None
                if self.spacy_available:
                    logger.info("✅ spaCy initialisé")
            except Exception as e:
                logger.warning(f"⚠️ Erreur spaCy: {e}")
                self.spacy_available = False
        else:
            self.spacy_available = False
    
    def _load_medical_terms(self) -> List[str]:
        """Charge la liste des termes médicaux importants"""
        return [
            # Termes généraux
            'diagnostic', 'traitement', 'symptôme', 'maladie', 'infection',
            'virus', 'bactérie', 'antibiotique', 'vaccin', 'immunisation',
            'prévention', 'dépistage', 'thérapie', 'médicament', 'posologie',
            
            # Anatomie
            'cœur', 'poumon', 'foie', 'rein', 'cerveau', 'estomac',
            'intestin', 'muscle', 'os', 'sang', 'artère', 'veine',
            
            # Spécialités
            'cardiologie', 'pneumologie', 'neurologie', 'pédiatrie',
            'gynécologie', 'psychiatrie', 'dermatologie', 'ophtalmologie',
            
            # Maladies courantes
            'hypertension', 'diabète', 'asthme', 'cancer', 'tuberculose',
            'paludisme', 'hépatite', 'pneumonie', 'méningite', 'anémie',
            
            # Procédures
            'chirurgie', 'opération', 'examen', 'analyse', 'radiographie',
            'échographie', 'scanner', 'IRM', 'biopsie', 'endoscopie'
        ]
    
    def _load_medical_abbreviations(self) -> Dict[str, str]:
        """Charge les abréviations médicales courantes"""
        return {
            # Unités
            'mg': 'milligramme',
            'ml': 'millilitre',
            'kg': 'kilogramme',
            'g': 'gramme',
            'l': 'litre',
            
            # Examens
            'ECG': 'électrocardiogramme',
            'IRM': 'imagerie par résonance magnétique',
            'TDM': 'tomodensitométrie',
            'RX': 'radiographie',
            'EEG': 'électroencéphalogramme',
            
            # Analyses
            'NFS': 'numération formule sanguine',
            'VS': 'vitesse de sédimentation',
            'CRP': 'protéine C réactive',
            'TP': 'taux de prothrombine',
            'INR': 'international normalized ratio',
            
            # Signes vitaux
            'TA': 'tension artérielle',
            'FC': 'fréquence cardiaque',
            'FR': 'fréquence respiratoire',
            'SpO2': 'saturation en oxygène',
            
            # Voies d'administration
            'PO': 'per os',
            'IV': 'intraveineux',
            'IM': 'intramusculaire',
            'SC': 'sous-cutané'
        }
    
    def _load_french_stopwords(self) -> set:
        """Charge les mots vides français"""
        if self.nltk_available:
            try:
                return set(stopwords.words('french'))
            except:
                pass
        
        # Liste manuelle si NLTK non disponible
        return {
            'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'et', 'ou',
            'mais', 'donc', 'car', 'ni', 'or', 'ce', 'cette', 'ces', 'cet',
            'il', 'elle', 'ils', 'elles', 'je', 'tu', 'nous', 'vous',
            'mon', 'ma', 'mes', 'ton', 'ta', 'tes', 'son', 'sa', 'ses',
            'dans', 'sur', 'avec', 'sans', 'pour', 'par', 'vers', 'chez',
            'être', 'avoir', 'faire', 'aller', 'venir', 'voir', 'savoir',
            'très', 'plus', 'moins', 'bien', 'mal', 'beaucoup', 'peu'
        }
    
    def _load_english_stopwords(self) -> set:
        """Charge les mots vides anglais"""
        if self.nltk_available:
            try:
                return set(stopwords.words('english'))
            except:
                pass
        
        return {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'for', 'of', 'with', 'by', 'from', 'up', 'about', 'into',
            'through', 'during', 'before', 'after', 'above', 'below',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'this', 'that',
            'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'
        }
    
    def process_document(self, raw_document: Dict[str, Any]) -> Optional[ProcessedDocument]:
        """Traite un document brut"""
        try:
            self.processing_stats['total_processed'] += 1
            
            # Validation initiale
            if not self._validate_raw_document(raw_document):
                logger.warning(f"⚠️ Document invalide: {raw_document.get('title', 'Sans titre')[:50]}")
                self.processing_stats['failed'] += 1
                return None
            
            # Extraction des données de base
            title = raw_document.get('title', '').strip()
            content = raw_document.get('content', '').strip()
            
            # Nettoyage du contenu
            cleaned_content = self._clean_content(content)
            
            # Vérification de la longueur après nettoyage
            if len(cleaned_content) < self.min_content_length:
                logger.warning(f"⚠️ Contenu trop court après nettoyage: {title[:50]}")
                self.processing_stats['failed'] += 1
                return None
            
            # Détection de la langue
            language = self._detect_language(cleaned_content)
            
            # Extraction des informations structurées
            structured_data = self._extract_structured_data(cleaned_content, language)
            
            # Génération du résumé
            summary = self._generate_summary(cleaned_content, language)
            
            # Extraction des mots-clés et termes médicaux
            keywords = self._extract_keywords(title, cleaned_content, language)
            medical_terms = self._extract_medical_terms(cleaned_content)
            
            # Extraction des phrases clés
            key_sentences = self._extract_key_sentences(cleaned_content, language)
            
            # Segmentation en sections
            content_sections = self._segment_content(cleaned_content)
            
            # Calcul des scores de qualité
            quality_score = self._calculate_quality_score(cleaned_content, structured_data)
            readability_score = self._calculate_readability_score(cleaned_content, language)
            medical_accuracy_score = self._calculate_medical_accuracy_score(cleaned_content, medical_terms)
            
            # Détermination de l'audience et complexité
            target_audience = self._determine_target_audience(cleaned_content)
            complexity_level = self._determine_complexity_level(cleaned_content, readability_score)
            
            # Calcul du hash
            content_hash = hashlib.sha256(cleaned_content.encode('utf-8')).hexdigest()
            
            # Création du document traité
            processed_doc = ProcessedDocument(
                title=title,
                content=content,
                cleaned_content=cleaned_content,
                summary=summary,
                original_url=raw_document.get('url', ''),
                source=raw_document.get('source', ''),
                category=raw_document.get('category', 'general'),
                specialty=raw_document.get('specialty'),
                document_type=raw_document.get('document_type', 'unknown'),
                language=language,
                keywords=keywords,
                medical_terms=medical_terms,
                key_sentences=key_sentences,
                content_sections=content_sections,
                quality_score=quality_score,
                readability_score=readability_score,
                medical_accuracy_score=medical_accuracy_score,
                content_length=len(cleaned_content),
                processing_date=datetime.now(),
                processing_version=self.processing_version,
                file_hash=content_hash,
                structured_data=structured_data,
                target_audience=target_audience,
                complexity_level=complexity_level
            )
            
            # Mise à jour des statistiques
            self.processing_stats['successful'] += 1
            self.processing_stats['quality_distribution'][int(quality_score * 10)] += 1
            self.processing_stats['categories'][processed_doc.category] += 1
            self.processing_stats['languages'][language] += 1
            
            logger.info(f"✅ Traité: {title[:60]}... (Q:{quality_score:.2f})")
            return processed_doc
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du traitement: {e}")
            self.processing_stats['failed'] += 1
            return None
    
    def _validate_raw_document(self, doc: Dict[str, Any]) -> bool:
        """Valide un document brut"""
        required_fields = ['title', 'content']
        
        for field in required_fields:
            if not doc.get(field) or not isinstance(doc[field], str):
                return False
        
        # Vérification de la longueur minimale
        content = doc['content'].strip()
        if len(content) < self.min_content_length:
            return False
        
        return True
    
    def _clean_content(self, content: str) -> str:
        """Nettoie le contenu du document"""
        # Supprimer les caractères de contrôle
        content = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]', '', content)
        
        # Normaliser les espaces
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'\n\s*\n', '\n\n', content)
        
        # Supprimer les URLs
        content = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', content)
        
        # Supprimer les emails
        content = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', content)
        
        # Nettoyer les caractères spéciaux répétitifs
        content = re.sub(r'[.]{3,}', '...', content)
        content = re.sub(r'[-]{3,}', '---', content)
        
        # Supprimer les lignes vides multiples
        lines = [line.strip() for line in content.split('\n')]
        content = '\n'.join(line for line in lines if line)
        
        return content.strip()
    
    def _detect_language(self, content: str) -> str:
        """Détecte la langue du contenu"""
        try:
            # Utiliser langdetect si disponible
            from langdetect import detect
            detected = detect(content[:2000])
            return detected
        except:
            # Détection simple basée sur des mots courants
            content_lower = content.lower()
            
            french_indicators = ['le ', 'la ', 'les ', 'de ', 'du ', 'des ', 'et ', 'ou ', 'mais ']
            english_indicators = ['the ', 'and ', 'or ', 'but ', 'of ', 'in ', 'to ', 'for ']
            
            french_count = sum(content_lower.count(indicator) for indicator in french_indicators)
            english_count = sum(content_lower.count(indicator) for indicator in english_indicators)
            
            if french_count > english_count:
                return 'fr'
            elif english_count > 0:
                return 'en'
            else:
                return 'unknown'
    
    def _extract_structured_data(self, content: str, language: str) -> Dict[str, Any]:
        """Extrait les données structurées du contenu"""
        structured = {
            'sections': [],
            'lists': [],
            'definitions': [],
            'procedures': [],
            'symptoms': [],
            'treatments': [],
            'medications': []
        }
        
        # Détecter les sections (titres)
        section_pattern = r'^([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][^\n]{10,100})$'
        sections = re.findall(section_pattern, content, re.MULTILINE)
        structured['sections'] = sections[:10]  # Limiter à 10 sections
        
        # Détecter les listes
        list_pattern = r'^\s*[-•*]\s+(.+)$'
        lists = re.findall(list_pattern, content, re.MULTILINE)
        structured['lists'] = lists[:20]  # Limiter à 20 éléments
        
        # Détecter les définitions (patterns simples)
        if language == 'fr':
            definition_patterns = [
                r'([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþ]+)\s+est\s+([^.]+)',
                r'([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ][a-zàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþ]+)\s*:\s*([^.]+)'
            ]
        else:
            definition_patterns = [
                r'([A-Z][a-z]+)\s+is\s+([^.]+)',
                r'([A-Z][a-z]+)\s*:\s*([^.]+)'
            ]
        
        for pattern in definition_patterns:
            matches = re.findall(pattern, content)
            for match in matches[:10]:
                structured['definitions'].append({
                    'term': match[0],
                    'definition': match[1].strip()
                })
        
        return structured
    
    def _generate_summary(self, content: str, language: str) -> str:
        """Génère un résumé du contenu"""
        # Méthode simple : prendre les premières phrases importantes
        sentences = self._split_into_sentences(content, language)
        
        if not sentences:
            return content[:self.target_summary_length] + "..."
        
        # Sélectionner les phrases les plus importantes
        important_sentences = []
        current_length = 0
        
        for sentence in sentences:
            if current_length + len(sentence) > self.target_summary_length:
                break
            
            # Critères de sélection des phrases importantes
            if self._is_important_sentence(sentence, language):
                important_sentences.append(sentence)
                current_length += len(sentence)
        
        if important_sentences:
            return ' '.join(important_sentences)
        else:
            # Fallback : premières phrases
            summary = ''
            for sentence in sentences:
                if len(summary) + len(sentence) > self.target_summary_length:
                    break
                summary += sentence + ' '
            return summary.strip()
    
    def _split_into_sentences(self, content: str, language: str) -> List[str]:
        """Divise le contenu en phrases"""
        if self.nltk_available:
            try:
                if language == 'fr':
                    return sent_tokenize(content, language='french')
                else:
                    return sent_tokenize(content, language='english')
            except:
                pass
        
        # Méthode simple de division
        sentences = re.split(r'[.!?]+\s+', content)
        return [s.strip() for s in sentences if len(s.strip()) > 10]
    
    def _is_important_sentence(self, sentence: str, language: str) -> bool:
        """Détermine si une phrase est importante"""
        sentence_lower = sentence.lower()
        
        # Mots-clés importants selon la langue
        if language == 'fr':
            important_keywords = [
                'diagnostic', 'traitement', 'symptôme', 'cause', 'prévention',
                'important', 'essentiel', 'principal', 'recommandé', 'nécessaire'
            ]
        else:
            important_keywords = [
                'diagnosis', 'treatment', 'symptom', 'cause', 'prevention',
                'important', 'essential', 'main', 'recommended', 'necessary'
            ]
        
        # Vérifier la présence de mots-clés importants
        keyword_count = sum(1 for keyword in important_keywords if keyword in sentence_lower)
        
        # Vérifier la présence de termes médicaux
        medical_count = sum(1 for term in self.medical_terms if term in sentence_lower)
        
        # Critères de sélection
        return (
            keyword_count > 0 or
            medical_count > 1 or
            len(sentence) > 50  # Phrases substantielles
        )
    
    def _extract_keywords(self, title: str, content: str, language: str) -> List[str]:
        """Extrait les mots-clés du document"""
        keywords = []
        
        # Combiner titre et contenu
        text = f"{title} {content}"
        text_lower = text.lower()
        
        # Extraire les termes médicaux présents
        for term in self.medical_terms:
            if term in text_lower:
                keywords.append(term)
        
        # Extraire les mots fréquents (après suppression des mots vides)
        if language == 'fr':
            stopwords_set = self.stopwords_fr
        else:
            stopwords_set = self.stopwords_en
        
        # Tokenisation simple
        words = re.findall(r'\b[a-zA-ZàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞ]{3,}\b', text_lower)
        
        # Compter les mots (en excluant les mots vides)
        word_counts = Counter(word for word in words if word not in stopwords_set)
        
        # Ajouter les mots les plus fréquents
        for word, count in word_counts.most_common(10):
            if count > 1 and word not in keywords:
                keywords.append(word)
        
        return keywords[:15]  # Limiter à 15 mots-clés
    
    def _extract_medical_terms(self, content: str) -> List[str]:
        """Extrait les termes médicaux spécifiques"""
        content_lower = content.lower()
        found_terms = []
        
        for term in self.medical_terms:
            if term in content_lower:
                found_terms.append(term)
        
        return found_terms
    
    def _extract_key_sentences(self, content: str, language: str) -> List[str]:
        """Extrait les phrases clés du document"""
        sentences = self._split_into_sentences(content, language)
        
        # Scorer les phrases
        scored_sentences = []
        for sentence in sentences:
            score = self._score_sentence(sentence, language)
            if score > 0.3:  # Seuil de qualité
                scored_sentences.append((sentence, score))
        
        # Trier par score et prendre les meilleures
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        
        return [sentence for sentence, score in scored_sentences[:5]]
    
    def _score_sentence(self, sentence: str, language: str) -> float:
        """Score une phrase selon son importance"""
        sentence_lower = sentence.lower()
        score = 0.0
        
        # Points pour les termes médicaux
        medical_count = sum(1 for term in self.medical_terms if term in sentence_lower)
        score += medical_count * 0.2
        
        # Points pour les mots-clés importants
        if language == 'fr':
            important_words = ['diagnostic', 'traitement', 'symptôme', 'important', 'essentiel']
        else:
            important_words = ['diagnosis', 'treatment', 'symptom', 'important', 'essential']
        
        keyword_count = sum(1 for word in important_words if word in sentence_lower)
        score += keyword_count * 0.3
        
        # Pénalité pour les phrases trop courtes ou trop longues
        length = len(sentence)
        if length < 20:
            score *= 0.5
        elif length > 200:
            score *= 0.7
        
        return min(score, 1.0)
    
    def _segment_content(self, content: str) -> Dict[str, str]:
        """Segmente le contenu en sections logiques"""
        sections = {}
        
        # Patterns pour identifier les sections
        section_patterns = [
            (r'(?i)(symptômes?|symptoms?)\s*:?\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\s*[A-Z]|$)', 'symptoms'),
            (r'(?i)(traitements?|treatments?)\s*:?\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\s*[A-Z]|$)', 'treatment'),
            (r'(?i)(diagnostics?|diagnosis)\s*:?\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\s*[A-Z]|$)', 'diagnosis'),
            (r'(?i)(préventions?|prevention)\s*:?\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\s*[A-Z]|$)', 'prevention'),
            (r'(?i)(causes?|causes?)\s*:?\s*([^\n]+(?:\n[^\n]+)*?)(?=\n\s*[A-Z]|$)', 'causes')
        ]
        
        for pattern, section_name in section_patterns:
            matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
            if matches:
                # Prendre le premier match trouvé
                sections[section_name] = matches[0][1].strip()
        
        return sections
    
    def _calculate_quality_score(self, content: str, structured_data: Dict[str, Any]) -> float:
        """Calcule un score de qualité du document"""
        score = 0.0
        
        # Points pour la longueur (optimal entre 1000-5000 caractères)
        length = len(content)
        if 1000 <= length <= 5000:
            score += 0.3
        elif 500 <= length < 1000 or 5000 < length <= 10000:
            score += 0.2
        elif length > 10000:
            score += 0.1
        
        # Points pour la structure
        if structured_data['sections']:
            score += 0.2
        if structured_data['lists']:
            score += 0.1
        if structured_data['definitions']:
            score += 0.1
        
        # Points pour le contenu médical
        medical_term_count = len([term for term in self.medical_terms if term in content.lower()])
        if medical_term_count > 5:
            score += 0.2
        elif medical_term_count > 2:
            score += 0.1
        
        # Points pour la cohérence (phrases complètes)
        sentence_count = len(re.findall(r'[.!?]+', content))
        if sentence_count > 5:
            score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_readability_score(self, content: str, language: str) -> float:
        """Calcule un score de lisibilité"""
        # Méthode simple basée sur la longueur des phrases et des mots
        sentences = self._split_into_sentences(content, language)
        if not sentences:
            return 0.0
        
        words = re.findall(r'\b\w+\b', content)
        if not words:
            return 0.0
        
        avg_sentence_length = len(words) / len(sentences)
        avg_word_length = sum(len(word) for word in words) / len(words)
        
        # Score basé sur la complexité (plus c'est simple, plus le score est élevé)
        readability = 1.0 - min((avg_sentence_length / 30 + avg_word_length / 10) / 2, 1.0)
        
        return max(readability, 0.0)
    
    def _calculate_medical_accuracy_score(self, content: str, medical_terms: List[str]) -> float:
        """Calcule un score d'exactitude médicale"""
        # Score basé sur la densité de termes médicaux et la cohérence
        content_length = len(content)
        if content_length == 0:
            return 0.0
        
        # Densité de termes médicaux
        medical_density = len(medical_terms) / (content_length / 1000)  # par 1000 caractères
        
        # Présence d'abréviations médicales
        abbrev_count = sum(1 for abbrev in self.medical_abbreviations.keys() 
                          if abbrev in content)
        
        # Score combiné
        score = min(medical_density / 5 + abbrev_count / 10, 1.0)
        
        return score
    
    def _determine_target_audience(self, content: str) -> str:
        """Détermine l'audience cible du document"""
        content_lower = content.lower()
        
        # Indicateurs pour professionnels de santé
        professional_indicators = [
            'diagnostic différentiel', 'étiologie', 'physiopathologie',
            'anamnèse', 'examen clinique', 'thérapeutique',
            'differential diagnosis', 'etiology', 'pathophysiology',
            'clinical examination', 'therapeutic'
        ]
        
        # Indicateurs pour patients
        patient_indicators = [
            'que faire si', 'comment reconnaître', 'conseils pratiques',
            'what to do if', 'how to recognize', 'practical advice',
            'quand consulter', 'when to see a doctor'
        ]
        
        professional_count = sum(1 for indicator in professional_indicators 
                               if indicator in content_lower)
        patient_count = sum(1 for indicator in patient_indicators 
                          if indicator in content_lower)
        
        if professional_count > patient_count:
            return 'healthcare_professionals'
        elif patient_count > 0:
            return 'patients_families'
        else:
            return 'general_public'
    
    def _determine_complexity_level(self, content: str, readability_score: float) -> str:
        """Détermine le niveau de complexité du document"""
        # Basé sur le score de lisibilité et la présence de termes techniques
        technical_terms = sum(1 for term in self.medical_terms if term in content.lower())
        
        if readability_score > 0.7 and technical_terms < 5:
            return 'simple'
        elif readability_score > 0.5 and technical_terms < 15:
            return 'intermediate'
        else:
            return 'advanced'
    
    def process_batch(self, raw_documents: List[Dict[str, Any]]) -> List[ProcessedDocument]:
        """Traite un lot de documents"""
        logger.info(f"🔄 Traitement de {len(raw_documents)} documents...")
        
        processed_documents = []
        
        for i, raw_doc in enumerate(raw_documents):
            logger.info(f"📄 Traitement {i+1}/{len(raw_documents)}: {raw_doc.get('title', 'Sans titre')[:50]}...")
            
            processed_doc = self.process_document(raw_doc)
            if processed_doc:
                processed_documents.append(processed_doc)
        
        logger.info(f"✅ Traitement terminé: {len(processed_documents)}/{len(raw_documents)} documents traités avec succès")
        
        return processed_documents
    
    def save_processed_documents(self, documents: List[ProcessedDocument], output_path: Path) -> bool:
        """Sauvegarde les documents traités"""
        try:
            output_path.mkdir(parents=True, exist_ok=True)
            
            for i, doc in enumerate(documents):
                filename = f"processed_document_{i+1:03d}_{doc.file_hash[:8]}.json"
                filepath = output_path / filename
                
                # Convertir en dictionnaire pour la sérialisation
                doc_dict = asdict(doc)
                
                # Convertir les dates en ISO format
                doc_dict['processing_date'] = doc.processing_date.isoformat()
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(doc_dict, f, ensure_ascii=False, indent=2)
            
            # Sauvegarder les statistiques
            stats_path = output_path / "processing_statistics.json"
            with open(stats_path, 'w', encoding='utf-8') as f:
                json.dump(self.processing_stats, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 Documents traités sauvegardés dans {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde: {e}")
            return False
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques de traitement"""
        stats = self.processing_stats.copy()
        
        if stats['total_processed'] > 0:
            stats['success_rate'] = stats['successful'] / stats['total_processed'] * 100
        else:
            stats['success_rate'] = 0
        
        return stats

def main():
    """Fonction principale pour tester le processeur"""
    # Configuration de test
    config = {
        'min_content_length': 300,
        'max_content_length': 50000,
        'target_summary_length': 200
    }
    
    processor = MedicalDataProcessor(config)
    
    # Document de test
    test_document = {
        'title': 'Hypertension artérielle : diagnostic et traitement',
        'content': '''
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
        ''',
        'url': 'https://example.com/hypertension',
        'source': 'Test',
        'category': 'maladies_chroniques',
        'specialty': 'Cardiologie',
        'document_type': 'guideline'
    }
    
    logger.info("🧪 Test du processeur de données...")
    
    processed_doc = processor.process_document(test_document)
    
    if processed_doc:
        logger.info(f"✅ Document traité avec succès")
        logger.info(f"📊 Score de qualité: {processed_doc.quality_score:.2f}")
        logger.info(f"📖 Score de lisibilité: {processed_doc.readability_score:.2f}")
        logger.info(f"🏥 Score médical: {processed_doc.medical_accuracy_score:.2f}")
        logger.info(f"🎯 Audience: {processed_doc.target_audience}")
        logger.info(f"📚 Complexité: {processed_doc.complexity_level}")
        logger.info(f"🔑 Mots-clés: {processed_doc.keywords[:5]}")
        
        # Sauvegarder le test
        output_path = Path("../data/processed/test")
        processor.save_processed_documents([processed_doc], output_path)
    else:
        logger.error("❌ Échec du traitement")
    
    # Afficher les statistiques
    stats = processor.get_processing_statistics()
    logger.info(f"📈 Statistiques: {stats}")

if __name__ == "__main__":
    main()