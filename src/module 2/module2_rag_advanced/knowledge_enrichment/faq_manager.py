#!/usr/bin/env python3
"""
Gestionnaire de FAQ Patients

Objectif 7: Ajouter FAQ courantes patients

Ce module gère les questions fréquemment posées par les patients
et leurs familles, avec des réponses adaptées au contexte camerounais.

Auteur: Équipe Hackathon Hôpital Général de Douala
Module: 2 - RAG Avancé & Multilingue
Version: 2.0.0
"""

import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re
from collections import defaultdict

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FAQCategory(Enum):
    """Catégories de FAQ"""
    GENERAL_INFO = "informations_generales"
    SYMPTOMS = "symptomes"
    TREATMENTS = "traitements"
    PREVENTION = "prevention"
    EMERGENCY = "urgences"
    APPOINTMENTS = "rendez_vous"
    COSTS = "couts"
    PROCEDURES = "procedures"
    MEDICATIONS = "medicaments"
    LIFESTYLE = "mode_vie"
    PREGNANCY = "grossesse"
    PEDIATRICS = "pediatrie"
    CHRONIC_DISEASES = "maladies_chroniques"
    MENTAL_HEALTH = "sante_mentale"
    NUTRITION = "nutrition"

class TargetAudience(Enum):
    """Public cible des FAQ"""
    PATIENTS = "patients"
    FAMILIES = "familles"
    CAREGIVERS = "aidants"
    GENERAL_PUBLIC = "grand_public"
    PREGNANT_WOMEN = "femmes_enceintes"
    PARENTS = "parents"
    ELDERLY = "personnes_agees"
    YOUTH = "jeunes"

class Language(Enum):
    """Langues supportées"""
    FRENCH = "fr"
    ENGLISH = "en"
    FULFULDE = "ff"
    EWONDO = "ewo"
    DUALA = "dua"

class UrgencyLevel(Enum):
    """Niveau d'urgence de la question"""
    EMERGENCY = "urgence"  # Nécessite consultation immédiate
    URGENT = "urgent"  # Consultation dans 24h
    MODERATE = "modere"  # Consultation dans la semaine
    LOW = "faible"  # Information générale

@dataclass
class FAQAnswer:
    """Réponse à une FAQ"""
    language: Language
    content: str
    simplified_version: Optional[str] = None
    audio_available: bool = False
    last_updated: datetime = field(default_factory=datetime.now)
    reviewed_by: Optional[str] = None
    sources: List[str] = field(default_factory=list)

@dataclass
class FAQ:
    """Question fréquemment posée"""
    id: str
    question: str
    category: FAQCategory
    target_audience: TargetAudience
    urgency_level: UrgencyLevel
    answers: Dict[Language, FAQAnswer] = field(default_factory=dict)
    related_questions: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    view_count: int = 0
    helpful_votes: int = 0
    unhelpful_votes: int = 0
    created_date: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    specialty: Optional[str] = None
    age_group: Optional[str] = None
    gender_specific: Optional[str] = None
    seasonal: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Génère un ID unique pour la FAQ"""
        import hashlib
        content = f"{self.question}_{self.category.value}"
        faq_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"faq_{self.category.value}_{faq_hash}"

@dataclass
class FAQStats:
    """Statistiques des FAQ"""
    total_faqs: int = 0
    faqs_by_category: Dict[str, int] = field(default_factory=dict)
    faqs_by_audience: Dict[str, int] = field(default_factory=dict)
    faqs_by_urgency: Dict[str, int] = field(default_factory=dict)
    faqs_by_language: Dict[str, int] = field(default_factory=dict)
    total_views: int = 0
    avg_helpfulness: float = 0.0
    processing_time: float = 0.0

class FAQManager:
    """
    Gestionnaire de FAQ pour patients
    
    Objectif couvert:
    - 7. Ajouter FAQ courantes patients
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.faqs: Dict[str, FAQ] = {}
        self.category_index: Dict[FAQCategory, Set[str]] = defaultdict(set)
        self.keyword_index: Dict[str, Set[str]] = defaultdict(set)
        self.stats = FAQStats()
        
        # Configuration
        self.auto_translate = self.config.get("auto_translate", False)
        self.enable_analytics = self.config.get("enable_analytics", True)
        
        # Initialiser les FAQ de base
        self._init_base_faqs()
        
        logger.info("Gestionnaire de FAQ patients initialisé")
    
    def _init_base_faqs(self):
        """Initialise les FAQ de base pour l'HGD"""
        base_faqs = self._get_base_faqs()
        
        for faq_data in base_faqs:
            faq = FAQ(**faq_data)
            self.add_faq(faq)
        
        logger.info(f"FAQ de base initialisées: {len(base_faqs)} questions")
    
    def _get_base_faqs(self) -> List[Dict[str, Any]]:
        """Retourne les FAQ de base pour l'HGD"""
        return [
            {
                "question": "Comment prendre rendez-vous à l'Hôpital Général de Douala ?",
                "category": FAQCategory.APPOINTMENTS,
                "target_audience": TargetAudience.GENERAL_PUBLIC,
                "urgency_level": UrgencyLevel.LOW,
                "answers": {
                    Language.FRENCH: FAQAnswer(
                        language=Language.FRENCH,
                        content="""Pour prendre rendez-vous à l'HGD :
1. Appelez le standard : +237 233 42 21 34
2. Présentez-vous directement au service des rendez-vous (bâtiment principal, rez-de-chaussée)
3. Horaires : Lundi-Vendredi 7h-15h, Samedi 7h-12h
4. Apportez votre carte d'identité et carnet de santé
5. Pour les urgences, présentez-vous directement au service d'urgences 24h/24""",
                        simplified_version="Appelez le +237 233 42 21 34 ou venez directement au service des rendez-vous.",
                        sources=["Service des rendez-vous HGD"]
                    ),
                    Language.FULFULDE: FAQAnswer(
                        language=Language.FULFULDE,
                        content="Ngam heɓde rendez-vous to HGD, noddu +237 233 42 21 34 walla ari to service rendez-vous.",
                        sources=["Service des rendez-vous HGD"]
                    )
                },
                "keywords": ["rendez-vous", "consultation", "téléphone", "horaires"],
                "specialty": "administration"
            },
            
            {
                "question": "Que faire en cas de fièvre chez un enfant ?",
                "category": FAQCategory.PEDIATRICS,
                "target_audience": TargetAudience.PARENTS,
                "urgency_level": UrgencyLevel.URGENT,
                "answers": {
                    Language.FRENCH: FAQAnswer(
                        language=Language.FRENCH,
                        content="""En cas de fièvre chez l'enfant :

🌡️ MESURER LA TEMPÉRATURE :
- Température rectale > 38°C = fièvre
- Utilisez un thermomètre digital

💊 TRAITEMENT IMMÉDIAT :
- Paracétamol : 15mg/kg toutes les 6h
- Découvrir l'enfant, bain tiède
- Faire boire beaucoup d'eau

🚨 CONSULTER EN URGENCE SI :
- Fièvre > 40°C
- Enfant < 3 mois avec fièvre
- Convulsions
- Difficultés respiratoires
- Vomissements répétés
- Éruption cutanée

📞 Urgences pédiatriques HGD : +237 233 42 21 35""",
                        simplified_version="Donnez du paracétamol, découvrez l'enfant, faites boire. Consultez si fièvre > 40°C ou signes graves.",
                        sources=["Service de pédiatrie HGD", "OMS"]
                    )
                },
                "keywords": ["fièvre", "enfant", "paracétamol", "urgence", "pédiatrie"],
                "specialty": "pediatrie",
                "age_group": "enfants",
                "seasonal": True
            },
            
            {
                "question": "Comment reconnaître les signes du paludisme ?",
                "category": FAQCategory.SYMPTOMS,
                "target_audience": TargetAudience.GENERAL_PUBLIC,
                "urgency_level": UrgencyLevel.URGENT,
                "answers": {
                    Language.FRENCH: FAQAnswer(
                        language=Language.FRENCH,
                        content="""Signes du paludisme à surveiller :

🌡️ SIGNES PRINCIPAUX :
- Fièvre (souvent le soir)
- Frissons intenses
- Maux de tête violents
- Courbatures
- Fatigue extrême

⚠️ SIGNES DE GRAVITÉ :
- Vomissements répétés
- Convulsions
- Troubles de conscience
- Difficultés respiratoires
- Jaunisse (yeux jaunes)
- Urines foncées

🩺 DIAGNOSTIC :
- Test de diagnostic rapide (TDR)
- Goutte épaisse
- Disponibles à l'HGD 24h/24

💡 IMPORTANT :
Tout accès de fièvre au Cameroun = paludisme jusqu'à preuve du contraire
Consultez rapidement, le paludisme peut être mortel sans traitement""",
                        simplified_version="Fièvre + frissons + maux de tête = pensez au paludisme. Consultez rapidement pour un test.",
                        sources=["Service d'infectiologie HGD", "PNLP Cameroun"]
                    ),
                    Language.FULFULDE: FAQAnswer(
                        language=Language.FULFULDE,
                        content="Sette: ladde, ɓernde, naange hoore. Yah dokita yaawde ngam test.",
                        sources=["Service d'infectiologie HGD"]
                    )
                },
                "keywords": ["paludisme", "fièvre", "frissons", "TDR", "test"],
                "specialty": "infectiologie",
                "seasonal": True
            },
            
            {
                "question": "Quels sont les tarifs des consultations à l'HGD ?",
                "category": FAQCategory.COSTS,
                "target_audience": TargetAudience.GENERAL_PUBLIC,
                "urgency_level": UrgencyLevel.LOW,
                "answers": {
                    Language.FRENCH: FAQAnswer(
                        language=Language.FRENCH,
                        content="""Tarifs consultations HGD (2024) :

🏥 CONSULTATIONS EXTERNES :
- Médecine générale : 2 000 FCFA
- Spécialistes : 5 000 FCFA
- Pédiatrie : 3 000 FCFA
- Gynécologie : 4 000 FCFA

🚨 URGENCES :
- Consultation urgences : 3 000 FCFA
- Majoration nocturne (20h-6h) : +1 000 FCFA
- Week-end et jours fériés : +1 000 FCFA

🔬 EXAMENS COMPLÉMENTAIRES :
- Radiographie : 3 000-8 000 FCFA
- Échographie : 8 000-15 000 FCFA
- Scanner : 35 000-50 000 FCFA
- IRM : 80 000-120 000 FCFA

💳 MODES DE PAIEMENT :
- Espèces
- Mobile Money (Orange, MTN)
- Assurance maladie (selon convention)

📋 EXONÉRATIONS :
- Enfants < 5 ans : gratuit pour certains soins
- Femmes enceintes : consultations prénatales gratuites""",
                        sources=["Service financier HGD"]
                    )
                },
                "keywords": ["tarifs", "prix", "consultation", "coût", "paiement"],
                "specialty": "administration"
            },
            
            {
                "question": "Comment se préparer pour une échographie de grossesse ?",
                "category": FAQCategory.PREGNANCY,
                "target_audience": TargetAudience.PREGNANT_WOMEN,
                "urgency_level": UrgencyLevel.LOW,
                "answers": {
                    Language.FRENCH: FAQAnswer(
                        language=Language.FRENCH,
                        content="""Préparation échographie de grossesse :

💧 AVANT L'EXAMEN :
- Boire 1 litre d'eau 1h avant
- Ne pas uriner avant l'examen
- Vessie pleine = meilleure visualisation

👗 TENUE VESTIMENTAIRE :
- Porter des vêtements faciles à enlever
- Éviter les robes une pièce
- Prévoir une serviette

📋 DOCUMENTS À APPORTER :
- Carnet de grossesse
- Ordonnance du médecin
- Carte d'identité
- Résultats d'examens précédents

⏰ HORAIRES SERVICE IMAGERIE HGD :
- Lundi-Vendredi : 7h-17h
- Samedi : 7h-12h
- Urgences : 24h/24

💡 BON À SAVOIR :
- Examen indolore
- Durée : 15-30 minutes
- Accompagnant autorisé
- Photos échographie disponibles""",
                        simplified_version="Buvez 1L d'eau 1h avant, ne pas uriner. Apportez carnet de grossesse et ordonnance.",
                        sources=["Service d'imagerie HGD", "Service de gynécologie"]
                    )
                },
                "keywords": ["échographie", "grossesse", "préparation", "vessie", "imagerie"],
                "specialty": "gynecologie",
                "gender_specific": "femmes"
            },
            
            {
                "question": "Que faire en cas d'urgence cardiaque ?",
                "category": FAQCategory.EMERGENCY,
                "target_audience": TargetAudience.GENERAL_PUBLIC,
                "urgency_level": UrgencyLevel.EMERGENCY,
                "answers": {
                    Language.FRENCH: FAQAnswer(
                        language=Language.FRENCH,
                        content="""🚨 URGENCE CARDIAQUE - AGIR VITE :

⚠️ SIGNES D'ALERTE :
- Douleur thoracique intense
- Essoufflement soudain
- Sueurs froides
- Nausées, vomissements
- Douleur bras gauche, mâchoire
- Malaise, perte de connaissance

🆘 ACTIONS IMMÉDIATES :
1. Appelez le 15 ou +237 233 42 21 35 (urgences HGD)
2. Allongez la personne, tête surélevée
3. Desserrez les vêtements
4. Si consciente : 1 comprimé d'aspirine à croquer
5. Si inconsciente : position latérale de sécurité
6. Préparez-vous à faire un massage cardiaque

🏥 TRANSPORT :
- Ambulance recommandée
- Évitez de conduire vous-même
- Service d'urgences HGD 24h/24

⏱️ TEMPS = VIE :
Chaque minute compte dans l'infarctus
N'attendez pas que ça passe !""",
                        simplified_version="Douleur thoracique = urgence ! Appelez le 15, donnez de l'aspirine, transportez rapidement.",
                        sources=["Service de cardiologie HGD", "SAMU"]
                    )
                },
                "keywords": ["urgence", "cardiaque", "infarctus", "douleur thoracique", "15"],
                "specialty": "cardiologie"
            },
            
            {
                "question": "Comment bien prendre ses médicaments contre l'hypertension ?",
                "category": FAQCategory.MEDICATIONS,
                "target_audience": TargetAudience.PATIENTS,
                "urgency_level": UrgencyLevel.MODERATE,
                "answers": {
                    Language.FRENCH: FAQAnswer(
                        language=Language.FRENCH,
                        content="""Prise des médicaments antihypertenseurs :

⏰ RÉGULARITÉ :
- Même heure chaque jour
- Ne jamais arrêter brutalement
- Traitement à vie dans la plupart des cas

💊 CONSEILS DE PRISE :
- Le matin de préférence
- Avec un verre d'eau
- Avant ou après repas selon prescription
- Utiliser un pilulier si oublis fréquents

📊 SURVEILLANCE :
- Mesurer tension 2-3 fois/semaine
- Tenir un carnet de suivi
- Objectif : < 140/90 mmHg
- Consultation de contrôle tous les 3 mois

⚠️ EFFETS SECONDAIRES POSSIBLES :
- Fatigue, vertiges
- Toux sèche (IEC)
- Œdèmes chevilles
- Signaler au médecin si gênants

🚫 ÉVITER :
- Automédication
- Anti-inflammatoires sans avis médical
- Excès de sel
- Arrêt brutal du traitement

📞 Contact service cardiologie HGD : +237 233 42 21 36""",
                        simplified_version="Prenez vos médicaments tous les jours à la même heure. Ne jamais arrêter. Surveillez votre tension.",
                        sources=["Service de cardiologie HGD"]
                    )
                },
                "keywords": ["hypertension", "médicaments", "tension", "traitement", "observance"],
                "specialty": "cardiologie"
            },
            
            {
                "question": "Quels aliments éviter en cas de diabète ?",
                "category": FAQCategory.NUTRITION,
                "target_audience": TargetAudience.PATIENTS,
                "urgency_level": UrgencyLevel.LOW,
                "answers": {
                    Language.FRENCH: FAQAnswer(
                        language=Language.FRENCH,
                        content="""Alimentation et diabète - Conseils HGD :

🚫 ALIMENTS À ÉVITER :
- Sucre blanc, miel, confiture
- Sodas, jus de fruits sucrés
- Pâtisseries, gâteaux, bonbons
- Pain blanc, riz blanc
- Fruits très sucrés (mangue mûre, banane très mûre)

✅ ALIMENTS RECOMMANDÉS :
- Légumes verts (épinards, gombo, ndolé)
- Poissons (machoiron, capitaine)
- Viandes maigres (poulet sans peau)
- Céréales complètes (riz complet, mil)
- Fruits peu sucrés (orange, pamplemousse)

🍽️ CONSEILS PRATIQUES :
- 3 repas réguliers + 2 collations
- Portions modérées
- Cuisson sans huile excessive
- Boire beaucoup d'eau

🥗 PLATS CAMEROUNAIS ADAPTÉS :
- Ndolé aux arachides (sans huile excessive)
- Poisson braisé aux légumes
- Salade de concombre-tomate
- Bouillie de mil non sucrée

📊 SURVEILLANCE :
- Glycémie avant repas : 0.8-1.2 g/L
- Consultation diététicienne HGD disponible""",
                        simplified_version="Évitez sucre, sodas, pâtisseries. Privilégiez légumes, poissons, céréales complètes.",
                        sources=["Service d'endocrinologie HGD", "Diététicienne HGD"]
                    )
                },
                "keywords": ["diabète", "alimentation", "sucre", "régime", "glycémie"],
                "specialty": "endocrinologie"
            },
            
            {
                "question": "Comment protéger sa famille du COVID-19 ?",
                "category": FAQCategory.PREVENTION,
                "target_audience": TargetAudience.FAMILIES,
                "urgency_level": UrgencyLevel.MODERATE,
                "answers": {
                    Language.FRENCH: FAQAnswer(
                        language=Language.FRENCH,
                        content="""Protection familiale COVID-19 :

😷 GESTES BARRIÈRES :
- Port du masque en public
- Lavage des mains 20 secondes
- Gel hydroalcoolique si pas d'eau
- Distance 1 mètre minimum
- Éviter les rassemblements

🏠 À LA MAISON :
- Aérer les pièces 10min/jour
- Nettoyer surfaces fréquemment touchées
- Ne pas partager verres, couverts
- Isoler les personnes malades

💉 VACCINATION :
- Disponible gratuitement au Cameroun
- Toute personne > 12 ans
- Centre de vaccination HGD ouvert
- Rappel recommandé

🚨 CONSULTER SI :
- Fièvre + toux + difficultés respiratoires
- Perte goût/odorat
- Fatigue extrême
- Contact avec cas positif

📞 Ligne verte COVID : 1510
📞 Urgences HGD : +237 233 42 21 35

🧪 TESTS DISPONIBLES HGD :
- Test antigénique rapide
- RT-PCR
- Ouvert 7j/7""",
                        simplified_version="Masque, lavage mains, distance, vaccination. Consultez si fièvre + toux + essoufflement.",
                        sources=["MINSANTE Cameroun", "Service d'infectiologie HGD"]
                    )
                },
                "keywords": ["COVID-19", "protection", "masque", "vaccination", "gestes barrières"],
                "specialty": "infectiologie"
            },
            
            {
                "question": "Quand consulter pour des troubles de la mémoire ?",
                "category": FAQCategory.MENTAL_HEALTH,
                "target_audience": TargetAudience.ELDERLY,
                "urgency_level": UrgencyLevel.MODERATE,
                "answers": {
                    Language.FRENCH: FAQAnswer(
                        language=Language.FRENCH,
                        content="""Troubles de la mémoire - Quand s'inquiéter ?

🧠 SIGNES D'ALERTE :
- Oublis récents fréquents
- Difficultés à trouver ses mots
- Se perdre dans des lieux familiers
- Difficultés à gérer l'argent
- Changements de personnalité
- Négligence de l'hygiène

✅ VIEILLISSEMENT NORMAL :
- Oublis occasionnels de noms
- Chercher ses clés parfois
- Fatigue après effort mental
- Ralentissement léger

🩺 CONSULTATION RECOMMANDÉE SI :
- Troubles gênent la vie quotidienne
- Famille inquiète
- Chutes répétées
- Perte d'autonomie

🏥 PRISE EN CHARGE HGD :
- Consultation neurologie
- Tests cognitifs
- Bilan sanguin complet
- Scanner cérébral si nécessaire

💡 PRÉVENTION :
- Activité physique régulière
- Lecture, jeux de société
- Vie sociale active
- Alimentation équilibrée
- Contrôle tension, diabète

📞 RDV neurologie HGD : +237 233 42 21 37""",
                        simplified_version="Consultez si oublis gênent la vie quotidienne, changements de personnalité, perte d'autonomie.",
                        sources=["Service de neurologie HGD"]
                    )
                },
                "keywords": ["mémoire", "oublis", "Alzheimer", "neurologie", "personnes âgées"],
                "specialty": "neurologie",
                "age_group": "personnes_agees"
            }
        ]
    
    def add_faq(self, faq: FAQ) -> bool:
        """
        Ajoute une FAQ
        
        Args:
            faq: FAQ à ajouter
        
        Returns:
            bool: True si ajoutée avec succès
        """
        try:
            if faq.id in self.faqs:
                logger.warning(f"FAQ déjà existante: {faq.id}")
                return False
            
            # Ajouter la FAQ
            self.faqs[faq.id] = faq
            
            # Mettre à jour les index
            self.category_index[faq.category].add(faq.id)
            
            for keyword in faq.keywords:
                self.keyword_index[keyword.lower()].add(faq.id)
            
            logger.debug(f"FAQ ajoutée: {faq.question[:50]}...")
            return True
        
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout de la FAQ: {e}")
            return False
    
    def search_faqs(self, query: str, category: Optional[FAQCategory] = None,
                   audience: Optional[TargetAudience] = None,
                   language: Optional[Language] = None) -> List[FAQ]:
        """
        Recherche des FAQ
        
        Args:
            query: Terme de recherche
            category: Catégorie (optionnel)
            audience: Audience cible (optionnel)
            language: Langue (optionnel)
        
        Returns:
            List[FAQ]: FAQ trouvées
        """
        results = []
        query_lower = query.lower()
        
        for faq in self.faqs.values():
            # Filtrer par catégorie
            if category and faq.category != category:
                continue
            
            # Filtrer par audience
            if audience and faq.target_audience != audience:
                continue
            
            # Filtrer par langue (vérifier si réponse disponible)
            if language and language not in faq.answers:
                continue
            
            # Recherche textuelle
            if (query_lower in faq.question.lower() or
                any(query_lower in keyword.lower() for keyword in faq.keywords) or
                any(query_lower in answer.content.lower() for answer in faq.answers.values())):
                results.append(faq)
        
        # Trier par pertinence (nombre de vues, votes utiles)
        results.sort(key=lambda f: (f.helpful_votes, f.view_count), reverse=True)
        
        return results
    
    def get_faq(self, faq_id: str) -> Optional[FAQ]:
        """Retourne une FAQ par son ID"""
        faq = self.faqs.get(faq_id)
        if faq and self.enable_analytics:
            faq.view_count += 1
        return faq
    
    def get_faqs_by_category(self, category: FAQCategory) -> List[FAQ]:
        """Retourne toutes les FAQ d'une catégorie"""
        faq_ids = self.category_index.get(category, set())
        return [self.faqs[faq_id] for faq_id in faq_ids if faq_id in self.faqs]
    
    def get_faqs_by_urgency(self, urgency: UrgencyLevel) -> List[FAQ]:
        """Retourne toutes les FAQ d'un niveau d'urgence"""
        return [faq for faq in self.faqs.values() if faq.urgency_level == urgency]
    
    def get_popular_faqs(self, limit: int = 10) -> List[FAQ]:
        """Retourne les FAQ les plus populaires"""
        sorted_faqs = sorted(self.faqs.values(), 
                           key=lambda f: (f.helpful_votes, f.view_count), 
                           reverse=True)
        return sorted_faqs[:limit]
    
    def get_related_faqs(self, faq_id: str, limit: int = 5) -> List[FAQ]:
        """Retourne les FAQ liées"""
        faq = self.faqs.get(faq_id)
        if not faq:
            return []
        
        related = []
        
        # FAQ explicitement liées
        for related_id in faq.related_questions:
            if related_id in self.faqs:
                related.append(self.faqs[related_id])
        
        # FAQ de la même catégorie
        if len(related) < limit:
            category_faqs = self.get_faqs_by_category(faq.category)
            for cat_faq in category_faqs:
                if cat_faq.id != faq_id and cat_faq not in related:
                    related.append(cat_faq)
                    if len(related) >= limit:
                        break
        
        return related[:limit]
    
    def vote_helpful(self, faq_id: str, helpful: bool = True) -> bool:
        """
        Vote pour l'utilité d'une FAQ
        
        Args:
            faq_id: ID de la FAQ
            helpful: True si utile, False sinon
        
        Returns:
            bool: True si vote enregistré
        """
        faq = self.faqs.get(faq_id)
        if not faq:
            return False
        
        if helpful:
            faq.helpful_votes += 1
        else:
            faq.unhelpful_votes += 1
        
        return True
    
    def add_answer(self, faq_id: str, answer: FAQAnswer) -> bool:
        """
        Ajoute une réponse à une FAQ existante
        
        Args:
            faq_id: ID de la FAQ
            answer: Réponse à ajouter
        
        Returns:
            bool: True si ajoutée avec succès
        """
        faq = self.faqs.get(faq_id)
        if not faq:
            return False
        
        faq.answers[answer.language] = answer
        faq.last_updated = datetime.now()
        
        return True
    
    def generate_stats(self) -> FAQStats:
        """
        Génère les statistiques des FAQ
        
        Returns:
            FAQStats: Statistiques complètes
        """
        import time
        start_time = time.time()
        
        stats = FAQStats()
        stats.total_faqs = len(self.faqs)
        
        # Statistiques par catégorie
        for category, faq_ids in self.category_index.items():
            stats.faqs_by_category[category.value] = len(faq_ids)
        
        # Statistiques par audience
        audience_count = defaultdict(int)
        for faq in self.faqs.values():
            audience_count[faq.target_audience.value] += 1
        stats.faqs_by_audience = dict(audience_count)
        
        # Statistiques par urgence
        urgency_count = defaultdict(int)
        for faq in self.faqs.values():
            urgency_count[faq.urgency_level.value] += 1
        stats.faqs_by_urgency = dict(urgency_count)
        
        # Statistiques par langue
        language_count = defaultdict(int)
        for faq in self.faqs.values():
            for language in faq.answers.keys():
                language_count[language.value] += 1
        stats.faqs_by_language = dict(language_count)
        
        # Statistiques d'utilisation
        stats.total_views = sum(faq.view_count for faq in self.faqs.values())
        
        # Score d'utilité moyen
        total_votes = sum(faq.helpful_votes + faq.unhelpful_votes for faq in self.faqs.values())
        helpful_votes = sum(faq.helpful_votes for faq in self.faqs.values())
        if total_votes > 0:
            stats.avg_helpfulness = helpful_votes / total_votes
        
        stats.processing_time = time.time() - start_time
        
        self.stats = stats
        return stats
    
    def export_faqs(self, output_path: str, language: Optional[Language] = None):
        """
        Exporte les FAQ dans un fichier JSON
        
        Args:
            output_path: Chemin de sortie
            language: Langue spécifique (optionnel)
        """
        export_data = {
            "metadata": {
                "total_faqs": len(self.faqs),
                "export_language": language.value if language else "all",
                "export_date": datetime.now().isoformat(),
                "source": "Hôpital Général de Douala"
            },
            "faqs": []
        }
        
        for faq in self.faqs.values():
            faq_data = {
                "id": faq.id,
                "question": faq.question,
                "category": faq.category.value,
                "target_audience": faq.target_audience.value,
                "urgency_level": faq.urgency_level.value,
                "keywords": faq.keywords,
                "view_count": faq.view_count,
                "helpful_votes": faq.helpful_votes,
                "unhelpful_votes": faq.unhelpful_votes,
                "specialty": faq.specialty,
                "age_group": faq.age_group,
                "gender_specific": faq.gender_specific
            }
            
            # Ajouter les réponses
            if language:
                answer = faq.answers.get(language)
                if answer:
                    faq_data["answer"] = {
                        "content": answer.content,
                        "simplified_version": answer.simplified_version,
                        "sources": answer.sources
                    }
            else:
                faq_data["answers"] = {
                    lang.value: {
                        "content": ans.content,
                        "simplified_version": ans.simplified_version,
                        "sources": ans.sources
                    }
                    for lang, ans in faq.answers.items()
                }
            
            export_data["faqs"].append(faq_data)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"FAQ exportées: {output_path}")

# Test de démonstration
async def main():
    """Fonction de test principale"""
    print("❓ Test du Gestionnaire de FAQ Patients")
    
    # Créer le gestionnaire
    faq_manager = FAQManager({
        "enable_analytics": True,
        "auto_translate": False
    })
    
    # Afficher les FAQ disponibles
    print(f"\n📋 FAQ disponibles: {len(faq_manager.faqs)}")
    
    # Rechercher des FAQ
    print("\n🔍 Recherche 'fièvre':")
    fever_faqs = faq_manager.search_faqs("fièvre")
    for faq in fever_faqs:
        print(f"  - {faq.question}")
        print(f"    Catégorie: {faq.category.value}, Urgence: {faq.urgency_level.value}")
    
    # FAQ par catégorie
    print("\n🚨 FAQ d'urgence:")
    emergency_faqs = faq_manager.get_faqs_by_category(FAQCategory.EMERGENCY)
    for faq in emergency_faqs:
        print(f"  - {faq.question}")
    
    # FAQ populaires
    print("\n⭐ FAQ populaires:")
    popular_faqs = faq_manager.get_popular_faqs(3)
    for faq in popular_faqs:
        print(f"  - {faq.question}")
        print(f"    Vues: {faq.view_count}, Votes utiles: {faq.helpful_votes}")
    
    # Générer les statistiques
    stats = faq_manager.generate_stats()
    print(f"\n📊 Statistiques:")
    print(f"  Total FAQ: {stats.total_faqs}")
    print(f"  Vues totales: {stats.total_views}")
    print(f"  Utilité moyenne: {stats.avg_helpfulness:.2f}")
    
    print(f"\n📋 Répartition par catégorie:")
    for category, count in stats.faqs_by_category.items():
        print(f"  {category}: {count} FAQ")
    
    # Exporter les FAQ
    faq_manager.export_faqs("patient_faqs_hgd.json")
    print("\n✅ FAQ exportées: patient_faqs_hgd.json")

if __name__ == "__main__":
    asyncio.run(main())