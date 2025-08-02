#!/usr/bin/env python3
"""
Traducteur médical pour traduire les contenus essentiels vers les langues locales
Supporte la traduction vers le français, l'anglais et les langues camerounaises
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
from collections import defaultdict

# Imports pour la traduction
try:
    from googletrans import Translator as GoogleTranslator
    GOOGLE_TRANSLATE_AVAILABLE = True
except ImportError:
    GOOGLE_TRANSLATE_AVAILABLE = False
    GoogleTranslator = None

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TranslationResult:
    """Résultat de traduction d'un document"""
    document_id: str
    source_language: str
    target_language: str
    
    # Contenu traduit
    translated_title: str
    translated_content: str
    translated_summary: str
    translated_keywords: List[str]
    
    # Sections spécialisées
    translated_sections: Dict[str, str]
    medical_terms_glossary: Dict[str, str]
    
    # Qualité de traduction
    translation_quality_score: float
    confidence_score: float
    
    # Adaptations culturelles
    cultural_adaptations: List[Dict[str, str]]
    local_context_notes: List[str]
    
    # Métadonnées
    translation_date: datetime
    translator_version: str
    translation_method: str
    review_status: str

@dataclass
class MedicalTerm:
    """Terme médical avec ses traductions"""
    original_term: str
    translations: Dict[str, str]  # langue -> traduction
    definition: str
    category: str
    priority: int  # 1=essentiel, 2=important, 3=utile

class MedicalTranslator:
    """Traducteur principal pour les contenus médicaux"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.translator_version = "1.0.0"
        
        # Langues supportées
        self.supported_languages = {
            'fr': 'Français',
            'en': 'English',
            'bm': 'Bamoun',
            'ff': 'Fulfulde',
            'bss': 'Bassa',
            'ewo': 'Ewondo',
            'dua': 'Duala'
        }
        
        # Langues prioritaires pour le Cameroun
        self.priority_languages = ['fr', 'en', 'ff', 'ewo', 'dua']
        
        # Initialiser les traducteurs
        self._initialize_translators()
        
        # Charger les dictionnaires médicaux
        self.medical_dictionaries = self._load_medical_dictionaries()
        self.cultural_adaptations = self._load_cultural_adaptations()
        
        # Glossaire médical multilingue
        self.medical_glossary = self._build_medical_glossary()
        
        # Statistiques
        self.translation_stats = {
            'total_translated': 0,
            'successful_translations': 0,
            'failed_translations': 0,
            'languages_used': defaultdict(int),
            'translation_methods': defaultdict(int),
            'quality_scores': []
        }
    
    def _initialize_translators(self):
        """Initialise les services de traduction"""
        logger.info("🔧 Initialisation des services de traduction...")
        
        # Google Translate
        if GOOGLE_TRANSLATE_AVAILABLE:
            try:
                self.google_translator = GoogleTranslator()
                self.google_available = True
                logger.info("✅ Google Translate initialisé")
            except Exception as e:
                logger.warning(f"⚠️ Erreur Google Translate: {e}")
                self.google_available = False
        else:
            self.google_available = False
            logger.warning("⚠️ Google Translate non disponible")
        
        # Traducteur de base (dictionnaire)
        self.dictionary_translator = True
        logger.info("✅ Traducteur par dictionnaire initialisé")
    
    def _load_medical_dictionaries(self) -> Dict[str, Dict[str, str]]:
        """Charge les dictionnaires médicaux pour les langues locales"""
        return {
            # Français -> Langues locales
            'fr_to_ff': {  # Fulfulde
                'maladie': 'jukku',
                'douleur': 'ñaawu',
                'fièvre': 'yiite',
                'toux': 'kohol',
                'maux de tête': 'hoore ñaawi',
                'fatigue': 'nafoore',
                'médicament': 'lekki',
                'hôpital': 'duuɗal',
                'docteur': 'doktoor',
                'infirmier': 'neɗɗaaku',
                'traitement': 'feeñtaade',
                'symptôme': 'maandu',
                'diagnostic': 'ɓeydaade',
                'prévention': 'haɓɓitaade',
                'vaccination': 'dabaade',
                'hypertension': 'yiite ɗemngal',
                'diabète': 'sukkar jukku',
                'paludisme': 'malaaria',
                'tuberculose': 'tbc'
            },
            
            'fr_to_ewo': {  # Ewondo
                'maladie': 'bela',
                'douleur': 'nyolo',
                'fièvre': 'awu',
                'toux': 'sue',
                'maux de tête': 'nyolo nlo',
                'fatigue': 'kob',
                'médicament': 'bilamba',
                'hôpital': 'nda bekono',
                'docteur': 'bekono',
                'infirmier': 'moto bekono',
                'traitement': 'bekono',
                'symptôme': 'bibem bela',
                'diagnostic': 'yem bela',
                'prévention': 'kob bela',
                'vaccination': 'tob bilamba',
                'hypertension': 'awu makila',
                'diabète': 'bela sukre',
                'paludisme': 'malaria',
                'tuberculose': 'sue makila'
            },
            
            'fr_to_dua': {  # Duala
                'maladie': 'bwele',
                'douleur': 'mpasi',
                'fièvre': 'moto',
                'toux': 'koso',
                'maux de tête': 'mpasi moto',
                'fatigue': 'lembe',
                'médicament': 'kanya',
                'hôpital': 'ndako na bwele',
                'docteur': 'monganga',
                'infirmier': 'mosaleli monganga',
                'traitement': 'kosalela',
                'symptôme': 'bilembo bwele',
                'diagnostic': 'mona bwele',
                'prévention': 'kobatela',
                'vaccination': 'kanya kobatela',
                'hypertension': 'moto makila',
                'diabète': 'bwele sukre',
                'paludisme': 'malaria',
                'tuberculose': 'koso makila'
            },
            
            # Anglais -> Langues locales
            'en_to_ff': {
                'disease': 'jukku',
                'pain': 'ñaawu',
                'fever': 'yiite',
                'cough': 'kohol',
                'headache': 'hoore ñaawi',
                'fatigue': 'nafoore',
                'medicine': 'lekki',
                'hospital': 'duuɗal',
                'doctor': 'doktoor',
                'nurse': 'neɗɗaaku',
                'treatment': 'feeñtaade',
                'symptom': 'maandu',
                'diagnosis': 'ɓeydaade',
                'prevention': 'haɓɓitaade'
            }
        }
    
    def _load_cultural_adaptations(self) -> Dict[str, List[Dict[str, str]]]:
        """Charge les adaptations culturelles par langue"""
        return {
            'ff': [  # Fulfulde
                {
                    'concept': 'consultation médicale',
                    'adaptation': 'Aller voir le doktoor au duuɗal',
                    'cultural_note': 'Respecter les anciens et la hiérarchie familiale'
                },
                {
                    'concept': 'prise de médicaments',
                    'adaptation': 'Prendre le lekki comme dit le doktoor',
                    'cultural_note': 'Expliquer l\'importance de suivre le traitement complet'
                },
                {
                    'concept': 'prévention',
                    'adaptation': 'Haɓɓitaade ko waawi',
                    'cultural_note': 'Intégrer dans les pratiques quotidiennes'
                }
            ],
            
            'ewo': [  # Ewondo
                {
                    'concept': 'consultation médicale',
                    'adaptation': 'Ke nda bekono',
                    'cultural_note': 'Consulter aussi les guérisseurs traditionnels si nécessaire'
                },
                {
                    'concept': 'hygiène',
                    'adaptation': 'Suk nyo asu',
                    'cultural_note': 'Adapter aux ressources disponibles (eau, savon)'
                }
            ],
            
            'dua': [  # Duala
                {
                    'concept': 'urgence médicale',
                    'adaptation': 'Kende na ndako na bwele nooki',
                    'cultural_note': 'Expliquer les signes d\'urgence clairement'
                },
                {
                    'concept': 'vaccination',
                    'adaptation': 'Kanya kobatela',
                    'cultural_note': 'Rassurer sur la sécurité des vaccins'
                }
            ]
        }
    
    def _build_medical_glossary(self) -> Dict[str, MedicalTerm]:
        """Construit le glossaire médical multilingue"""
        glossary = {}
        
        # Termes essentiels avec traductions
        essential_terms = [
            {
                'term': 'hypertension',
                'definition': 'Pression artérielle élevée (≥140/90 mmHg)',
                'category': 'maladie_chronique',
                'priority': 1,
                'translations': {
                    'en': 'high blood pressure',
                    'ff': 'yiite ɗemngal',
                    'ewo': 'awu makila',
                    'dua': 'moto makila'
                }
            },
            {
                'term': 'diabète',
                'definition': 'Maladie caractérisée par un taux de sucre élevé dans le sang',
                'category': 'maladie_chronique',
                'priority': 1,
                'translations': {
                    'en': 'diabetes',
                    'ff': 'sukkar jukku',
                    'ewo': 'bela sukre',
                    'dua': 'bwele sukre'
                }
            },
            {
                'term': 'paludisme',
                'definition': 'Maladie transmise par les moustiques, causée par un parasite',
                'category': 'maladie_infectieuse',
                'priority': 1,
                'translations': {
                    'en': 'malaria',
                    'ff': 'malaaria',
                    'ewo': 'malaria',
                    'dua': 'malaria'
                }
            },
            {
                'term': 'vaccination',
                'definition': 'Injection pour protéger contre les maladies',
                'category': 'prevention',
                'priority': 1,
                'translations': {
                    'en': 'vaccination',
                    'ff': 'dabaade',
                    'ewo': 'tob bilamba',
                    'dua': 'kanya kobatela'
                }
            },
            {
                'term': 'fièvre',
                'definition': 'Température corporelle élevée (>37.5°C)',
                'category': 'symptome',
                'priority': 1,
                'translations': {
                    'en': 'fever',
                    'ff': 'yiite',
                    'ewo': 'awu',
                    'dua': 'moto'
                }
            }
        ]
        
        for term_data in essential_terms:
            term = MedicalTerm(
                original_term=term_data['term'],
                translations=term_data['translations'],
                definition=term_data['definition'],
                category=term_data['category'],
                priority=term_data['priority']
            )
            glossary[term_data['term']] = term
        
        return glossary
    
    def translate_document(self, document: Dict[str, Any], target_language: str) -> TranslationResult:
        """Traduit un document médical complet"""
        try:
            self.translation_stats['total_translated'] += 1
            
            doc_id = document.get('file_hash', f"doc_{self.translation_stats['total_translated']}")
            source_language = document.get('language', 'fr')
            
            logger.info(f"🌍 Traduction {source_language} -> {target_language}: {document.get('title', 'Sans titre')[:50]}...")
            
            # Vérifier si la langue cible est supportée
            if target_language not in self.supported_languages:
                raise ValueError(f"Langue non supportée: {target_language}")
            
            # Extraire le contenu à traduire
            title = document.get('title', '')
            content = document.get('cleaned_content', document.get('content', ''))
            summary = document.get('summary', '')
            keywords = document.get('keywords', [])
            
            # Traduction du titre
            translated_title = self._translate_text(title, source_language, target_language)
            
            # Traduction du contenu principal
            translated_content = self._translate_medical_content(content, source_language, target_language)
            
            # Traduction du résumé
            translated_summary = self._translate_text(summary, source_language, target_language)
            
            # Traduction des mots-clés
            translated_keywords = self._translate_keywords(keywords, source_language, target_language)
            
            # Traduction des sections spécialisées
            sections = document.get('content_sections', {})
            translated_sections = self._translate_sections(sections, source_language, target_language)
            
            # Création du glossaire pour ce document
            medical_terms_glossary = self._create_document_glossary(content, source_language, target_language)
            
            # Adaptations culturelles
            cultural_adaptations = self._apply_cultural_adaptations(translated_content, target_language)
            local_context_notes = self._generate_local_context_notes(document, target_language)
            
            # Calcul de la qualité de traduction
            translation_quality_score = self._calculate_translation_quality(
                content, translated_content, source_language, target_language
            )
            
            # Score de confiance
            confidence_score = self._calculate_confidence_score(
                translation_quality_score, source_language, target_language
            )
            
            # Détermination de la méthode de traduction utilisée
            translation_method = self._determine_translation_method(target_language)
            
            # Création du résultat
            result = TranslationResult(
                document_id=doc_id,
                source_language=source_language,
                target_language=target_language,
                translated_title=translated_title,
                translated_content=translated_content,
                translated_summary=translated_summary,
                translated_keywords=translated_keywords,
                translated_sections=translated_sections,
                medical_terms_glossary=medical_terms_glossary,
                translation_quality_score=translation_quality_score,
                confidence_score=confidence_score,
                cultural_adaptations=cultural_adaptations,
                local_context_notes=local_context_notes,
                translation_date=datetime.now(),
                translator_version=self.translator_version,
                translation_method=translation_method,
                review_status='automatic'
            )
            
            # Mise à jour des statistiques
            self.translation_stats['successful_translations'] += 1
            self.translation_stats['languages_used'][target_language] += 1
            self.translation_stats['translation_methods'][translation_method] += 1
            self.translation_stats['quality_scores'].append(translation_quality_score)
            
            logger.info(f"✅ Traduction terminée - Qualité: {translation_quality_score:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la traduction: {e}")
            self.translation_stats['failed_translations'] += 1
            return self._create_error_result(doc_id, source_language, target_language, str(e))
    
    def _translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """Traduit un texte simple"""
        if not text.strip():
            return text
        
        # Essayer la traduction par dictionnaire médical d'abord
        if target_lang in ['ff', 'ewo', 'dua']:
            dict_translation = self._translate_with_dictionary(text, source_lang, target_lang)
            if dict_translation != text:  # Si traduction trouvée
                return dict_translation
        
        # Essayer Google Translate pour les langues supportées
        if self.google_available and target_lang in ['en', 'fr']:
            try:
                result = self.google_translator.translate(text, src=source_lang, dest=target_lang)
                return result.text
            except Exception as e:
                logger.warning(f"⚠️ Erreur Google Translate: {e}")
        
        # Fallback : retourner le texte original avec note
        return f"{text} [Traduction non disponible]"
    
    def _translate_medical_content(self, content: str, source_lang: str, target_lang: str) -> str:
        """Traduit le contenu médical avec attention aux termes spécialisés"""
        if not content.strip():
            return content
        
        # Diviser en phrases pour traduction progressive
        sentences = self._split_into_sentences(content)
        translated_sentences = []
        
        for sentence in sentences:
            # Identifier les termes médicaux dans la phrase
            medical_terms = self._identify_medical_terms(sentence)
            
            # Traduire la phrase
            translated_sentence = self._translate_sentence_with_medical_terms(
                sentence, medical_terms, source_lang, target_lang
            )
            
            translated_sentences.append(translated_sentence)
        
        return ' '.join(translated_sentences)
    
    def _translate_with_dictionary(self, text: str, source_lang: str, target_lang: str) -> str:
        """Traduit en utilisant les dictionnaires médicaux"""
        dict_key = f"{source_lang}_to_{target_lang}"
        
        if dict_key not in self.medical_dictionaries:
            return text
        
        dictionary = self.medical_dictionaries[dict_key]
        text_lower = text.lower().strip()
        
        # Recherche exacte
        if text_lower in dictionary:
            return dictionary[text_lower]
        
        # Recherche partielle pour les phrases
        for term, translation in dictionary.items():
            if term in text_lower:
                text = text.replace(term, translation)
        
        return text
    
    def _translate_keywords(self, keywords: List[str], source_lang: str, target_lang: str) -> List[str]:
        """Traduit une liste de mots-clés"""
        translated = []
        
        for keyword in keywords:
            translated_keyword = self._translate_text(keyword, source_lang, target_lang)
            translated.append(translated_keyword)
        
        return translated
    
    def _translate_sections(self, sections: Dict[str, str], source_lang: str, target_lang: str) -> Dict[str, str]:
        """Traduit les sections spécialisées"""
        translated_sections = {}
        
        for section_name, section_content in sections.items():
            # Traduire le nom de la section
            translated_name = self._translate_text(section_name, source_lang, target_lang)
            
            # Traduire le contenu de la section
            translated_content = self._translate_medical_content(section_content, source_lang, target_lang)
            
            translated_sections[translated_name] = translated_content
        
        return translated_sections
    
    def _identify_medical_terms(self, text: str) -> List[str]:
        """Identifie les termes médicaux dans un texte"""
        medical_terms = []
        text_lower = text.lower()
        
        # Chercher dans le glossaire
        for term in self.medical_glossary.keys():
            if term.lower() in text_lower:
                medical_terms.append(term)
        
        # Chercher des patterns médicaux
        medical_patterns = [
            r'\b\d+(?:\.\d+)?\s*(?:mg|g|ml|l|UI)\b',  # Dosages
            r'\b\d+/\d+\s*mmHg\b',  # Tension artérielle
            r'\b\d+(?:\.\d+)?°C\b'  # Température
        ]
        
        for pattern in medical_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            medical_terms.extend(matches)
        
        return medical_terms
    
    def _translate_sentence_with_medical_terms(self, sentence: str, medical_terms: List[str], 
                                             source_lang: str, target_lang: str) -> str:
        """Traduit une phrase en préservant les termes médicaux"""
        # Remplacer temporairement les termes médicaux par des placeholders
        placeholders = {}
        modified_sentence = sentence
        
        for i, term in enumerate(medical_terms):
            placeholder = f"__MEDICAL_TERM_{i}__"
            placeholders[placeholder] = self._translate_medical_term(term, source_lang, target_lang)
            modified_sentence = modified_sentence.replace(term, placeholder)
        
        # Traduire la phrase modifiée
        translated_sentence = self._translate_text(modified_sentence, source_lang, target_lang)
        
        # Restaurer les termes médicaux traduits
        for placeholder, translated_term in placeholders.items():
            translated_sentence = translated_sentence.replace(placeholder, translated_term)
        
        return translated_sentence
    
    def _translate_medical_term(self, term: str, source_lang: str, target_lang: str) -> str:
        """Traduit un terme médical spécifique"""
        term_lower = term.lower()
        
        # Chercher dans le glossaire
        if term_lower in self.medical_glossary:
            glossary_term = self.medical_glossary[term_lower]
            if target_lang in glossary_term.translations:
                return glossary_term.translations[target_lang]
        
        # Utiliser le dictionnaire médical
        return self._translate_with_dictionary(term, source_lang, target_lang)
    
    def _create_document_glossary(self, content: str, source_lang: str, target_lang: str) -> Dict[str, str]:
        """Crée un glossaire pour le document"""
        glossary = {}
        
        # Identifier tous les termes médicaux dans le document
        medical_terms = self._identify_medical_terms(content)
        
        # Créer les traductions
        for term in set(medical_terms):  # Éviter les doublons
            translated_term = self._translate_medical_term(term, source_lang, target_lang)
            if translated_term != term:  # Si traduction disponible
                glossary[term] = translated_term
        
        return glossary
    
    def _apply_cultural_adaptations(self, content: str, target_lang: str) -> List[Dict[str, str]]:
        """Applique les adaptations culturelles"""
        adaptations = []
        
        if target_lang in self.cultural_adaptations:
            for adaptation in self.cultural_adaptations[target_lang]:
                if adaptation['concept'].lower() in content.lower():
                    adaptations.append(adaptation)
        
        return adaptations
    
    def _generate_local_context_notes(self, document: Dict[str, Any], target_lang: str) -> List[str]:
        """Génère des notes de contexte local"""
        notes = []
        
        # Notes générales selon la langue
        if target_lang == 'ff':  # Fulfulde
            notes.append("Consulter les anciens de la famille avant les décisions médicales importantes")
            notes.append("Respecter les pratiques religieuses lors des traitements")
        elif target_lang == 'ewo':  # Ewondo
            notes.append("Possibilité de combiner médecine moderne et traditionnelle")
            notes.append("Impliquer la communauté dans les soins de santé")
        elif target_lang == 'dua':  # Duala
            notes.append("Tenir compte des contraintes économiques pour les traitements")
            notes.append("Adapter les conseils aux conditions de vie urbaines")
        
        # Notes spécifiques selon le type de document
        doc_type = document.get('document_type', '')
        if doc_type == 'prevention':
            notes.append("Adapter les mesures préventives aux ressources locales disponibles")
        elif doc_type == 'treatment':
            notes.append("Vérifier la disponibilité des médicaments dans les pharmacies locales")
        
        return notes
    
    def _calculate_translation_quality(self, original: str, translated: str, 
                                     source_lang: str, target_lang: str) -> float:
        """Calcule la qualité de la traduction"""
        score = 0.0
        
        # Vérifier que la traduction n'est pas vide
        if not translated.strip():
            return 0.0
        
        # Vérifier que la traduction est différente de l'original (sauf si même langue)
        if source_lang != target_lang and original == translated:
            score += 0.2  # Traduction partielle
        else:
            score += 0.4
        
        # Vérifier la préservation de la longueur (approximative)
        length_ratio = len(translated) / len(original) if original else 0
        if 0.5 <= length_ratio <= 2.0:  # Longueur raisonnable
            score += 0.3
        
        # Vérifier la préservation des termes médicaux
        original_medical_terms = len(self._identify_medical_terms(original))
        translated_medical_terms = len(self._identify_medical_terms(translated))
        
        if original_medical_terms > 0:
            preservation_ratio = translated_medical_terms / original_medical_terms
            score += 0.3 * min(preservation_ratio, 1.0)
        else:
            score += 0.3
        
        return min(score, 1.0)
    
    def _calculate_confidence_score(self, quality_score: float, source_lang: str, target_lang: str) -> float:
        """Calcule le score de confiance de la traduction"""
        confidence = quality_score
        
        # Ajuster selon la disponibilité des outils
        if target_lang in ['en', 'fr'] and self.google_available:
            confidence *= 1.0  # Confiance élevée
        elif target_lang in ['ff', 'ewo', 'dua']:
            confidence *= 0.8  # Confiance modérée (dictionnaire)
        else:
            confidence *= 0.6  # Confiance faible
        
        # Ajuster selon la langue source
        if source_lang in ['fr', 'en']:
            confidence *= 1.0
        else:
            confidence *= 0.9
        
        return min(confidence, 1.0)
    
    def _determine_translation_method(self, target_lang: str) -> str:
        """Détermine la méthode de traduction utilisée"""
        if target_lang in ['en', 'fr'] and self.google_available:
            return 'google_translate'
        elif target_lang in ['ff', 'ewo', 'dua']:
            return 'medical_dictionary'
        else:
            return 'fallback'
    
    def _split_into_sentences(self, content: str) -> List[str]:
        """Divise le contenu en phrases"""
        sentences = re.split(r'[.!?]+\s+', content)
        return [s.strip() for s in sentences if len(s.strip()) > 5]
    
    def _create_error_result(self, doc_id: str, source_lang: str, target_lang: str, error_msg: str) -> TranslationResult:
        """Crée un résultat d'erreur"""
        return TranslationResult(
            document_id=doc_id,
            source_language=source_lang,
            target_language=target_lang,
            translated_title=f"[Erreur de traduction: {error_msg}]",
            translated_content=f"[Erreur de traduction: {error_msg}]",
            translated_summary="",
            translated_keywords=[],
            translated_sections={},
            medical_terms_glossary={},
            translation_quality_score=0.0,
            confidence_score=0.0,
            cultural_adaptations=[],
            local_context_notes=[],
            translation_date=datetime.now(),
            translator_version=self.translator_version,
            translation_method='error',
            review_status='failed'
        )
    
    def translate_batch(self, documents: List[Dict[str, Any]], target_languages: List[str]) -> Dict[str, List[TranslationResult]]:
        """Traduit un lot de documents vers plusieurs langues"""
        logger.info(f"🌍 Traduction de {len(documents)} documents vers {len(target_languages)} langues...")
        
        results = {}
        
        for target_lang in target_languages:
            logger.info(f"📝 Traduction vers {self.supported_languages.get(target_lang, target_lang)}...")
            
            lang_results = []
            for i, doc in enumerate(documents):
                logger.info(f"🔄 Document {i+1}/{len(documents)}: {doc.get('title', 'Sans titre')[:50]}...")
                
                result = self.translate_document(doc, target_lang)
                lang_results.append(result)
            
            results[target_lang] = lang_results
        
        logger.info(f"✅ Traduction terminée pour toutes les langues")
        return results
    
    def save_translations(self, results: Dict[str, List[TranslationResult]], output_path: Path) -> bool:
        """Sauvegarde les traductions"""
        try:
            output_path.mkdir(parents=True, exist_ok=True)
            
            for target_lang, lang_results in results.items():
                # Créer un dossier par langue
                lang_path = output_path / target_lang
                lang_path.mkdir(exist_ok=True)
                
                # Sauvegarder chaque traduction
                for result in lang_results:
                    filename = f"translation_{result.document_id}_{target_lang}.json"
                    filepath = lang_path / filename
                    
                    # Convertir en dictionnaire
                    result_dict = asdict(result)
                    result_dict['translation_date'] = result.translation_date.isoformat()
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(result_dict, f, ensure_ascii=False, indent=2)
                
                # Créer un glossaire consolidé pour la langue
                self._create_consolidated_glossary(lang_results, lang_path)
            
            # Sauvegarder les statistiques
            stats_path = output_path / "translation_statistics.json"
            with open(stats_path, 'w', encoding='utf-8') as f:
                json.dump(self.translation_stats, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 Traductions sauvegardées dans {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde: {e}")
            return False
    
    def _create_consolidated_glossary(self, results: List[TranslationResult], output_path: Path):
        """Crée un glossaire consolidé pour une langue"""
        consolidated_glossary = {}
        
        for result in results:
            consolidated_glossary.update(result.medical_terms_glossary)
        
        # Ajouter les termes du glossaire principal
        target_lang = results[0].target_language if results else 'unknown'
        for term, medical_term in self.medical_glossary.items():
            if target_lang in medical_term.translations:
                consolidated_glossary[term] = medical_term.translations[target_lang]
        
        # Sauvegarder le glossaire
        glossary_path = output_path / f"medical_glossary_{target_lang}.json"
        with open(glossary_path, 'w', encoding='utf-8') as f:
            json.dump(consolidated_glossary, f, ensure_ascii=False, indent=2)
    
    def create_simplified_sheets(self, documents: List[Dict[str, Any]], target_language: str) -> List[Dict[str, Any]]:
        """Crée des fiches explicatives simplifiées"""
        logger.info(f"📋 Création de fiches simplifiées en {self.supported_languages.get(target_language, target_language)}...")
        
        simplified_sheets = []
        
        for doc in documents:
            # Extraire les informations essentielles
            title = doc.get('title', '')
            content = doc.get('cleaned_content', '')
            
            # Créer une version simplifiée
            simplified_content = self._simplify_medical_content(content)
            
            # Traduire la fiche simplifiée
            translation_result = self.translate_document({
                'title': title,
                'cleaned_content': simplified_content,
                'language': doc.get('language', 'fr')
            }, target_language)
            
            # Créer la fiche
            sheet = {
                'title': translation_result.translated_title,
                'simplified_content': translation_result.translated_content,
                'key_points': self._extract_key_points(simplified_content, target_language),
                'glossary': translation_result.medical_terms_glossary,
                'cultural_notes': translation_result.local_context_notes,
                'language': target_language,
                'complexity_level': 'simple',
                'target_audience': 'general_public'
            }
            
            simplified_sheets.append(sheet)
        
        return simplified_sheets
    
    def _simplify_medical_content(self, content: str) -> str:
        """Simplifie le contenu médical pour le grand public"""
        # Extraire les points essentiels
        sentences = self._split_into_sentences(content)
        
        # Sélectionner les phrases les plus importantes et simples
        simplified_sentences = []
        
        for sentence in sentences:
            # Critères de simplicité
            if (len(sentence.split()) <= 15 and  # Phrases courtes
                not re.search(r'\b(?:physiopathologie|étiologie|nosologie)\b', sentence, re.IGNORECASE) and  # Éviter termes complexes
                any(keyword in sentence.lower() for keyword in ['symptôme', 'traitement', 'prévention', 'cause'])):
                
                simplified_sentences.append(sentence)
        
        return '. '.join(simplified_sentences[:5])  # Limiter à 5 phrases
    
    def _extract_key_points(self, content: str, target_language: str) -> List[str]:
        """Extrait les points clés du contenu"""
        key_points = []
        
        # Patterns pour identifier les points clés
        if target_language in ['fr', 'en']:
            key_patterns = [
                r'(?:symptômes?|symptoms?)\s*:?\s*([^.]+)',
                r'(?:traitement|treatment)\s*:?\s*([^.]+)',
                r'(?:prévention|prevention)\s*:?\s*([^.]+)'
            ]
        else:
            # Pour les langues locales, utiliser des patterns plus simples
            key_patterns = [r'([^.]{20,100}[.])']
        
        for pattern in key_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            key_points.extend(matches[:3])  # Limiter à 3 points par catégorie
        
        return key_points[:10]  # Maximum 10 points clés
    
    def get_translation_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques de traduction"""
        stats = self.translation_stats.copy()
        
        if stats['total_translated'] > 0:
            stats['success_rate'] = stats['successful_translations'] / stats['total_translated'] * 100
            stats['average_quality'] = sum(stats['quality_scores']) / len(stats['quality_scores']) if stats['quality_scores'] else 0
        else:
            stats['success_rate'] = 0
            stats['average_quality'] = 0
        
        return stats

def main():
    """Fonction principale pour tester le traducteur"""
    # Configuration de test
    config = {}
    
    translator = MedicalTranslator(config)
    
    # Document de test
    test_document = {
        'title': 'Hypertension artérielle',
        'cleaned_content': '''
        L'hypertension artérielle est une maladie chronique.
        Les symptômes incluent maux de tête, fatigue et essoufflement.
        Le traitement comprend des médicaments et des changements de mode de vie.
        La prévention passe par une alimentation saine et l'exercice physique.
        ''',
        'language': 'fr',
        'file_hash': 'test123'
    }
    
    logger.info("🧪 Test du traducteur médical...")
    
    # Test de traduction vers le fulfulde
    result = translator.translate_document(test_document, 'ff')
    
    logger.info(f"✅ Traduction terminée")
    logger.info(f"🎯 Qualité: {result.translation_quality_score:.2f}")
    logger.info(f"🔒 Confiance: {result.confidence_score:.2f}")
    logger.info(f"📝 Titre traduit: {result.translated_title}")
    logger.info(f"📖 Glossaire: {len(result.medical_terms_glossary)} termes")
    logger.info(f"🌍 Adaptations culturelles: {len(result.cultural_adaptations)}")
    
    # Test de création de fiches simplifiées
    simplified_sheets = translator.create_simplified_sheets([test_document], 'ff')
    logger.info(f"📋 Fiches simplifiées créées: {len(simplified_sheets)}")
    
    # Sauvegarder le test
    output_path = Path("../data/translations/test")
    translator.save_translations({'ff': [result]}, output_path)
    
    # Afficher les statistiques
    stats = translator.get_translation_statistics()
    logger.info(f"📈 Statistiques: {stats}")

if __name__ == "__main__":
    main()