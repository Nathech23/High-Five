#!/usr/bin/env python3
"""
Lieur de Concepts Médicaux

Objectif 9: Créer liens entre concepts médicaux

Ce module crée automatiquement des liens sémantiques entre
les concepts médicaux pour améliorer la navigation et la découverte.

Auteur: Équipe Hackathon Hôpital Général de Douala
Module: 2 - RAG Avancé & Multilingue
Version: 2.0.0
"""

import asyncio
import logging
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import math

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LinkType(Enum):
    """Types de liens entre concepts"""
    IS_A = "est_un"  # Relation hiérarchique (diabète est une maladie)
    PART_OF = "partie_de"  # Relation partie-tout (cœur partie de système cardiovasculaire)
    CAUSES = "cause"  # Relation causale (virus cause infection)
    TREATS = "traite"  # Relation thérapeutique (médicament traite maladie)
    SYMPTOM_OF = "symptome_de"  # Relation symptomatique (fièvre symptôme de infection)
    DIAGNOSED_BY = "diagnostique_par"  # Relation diagnostique (maladie diagnostiquée par test)
    PREVENTS = "previent"  # Relation préventive (vaccin prévient maladie)
    ASSOCIATED_WITH = "associe_a"  # Association générale
    CONTRAINDICATED_WITH = "contre_indique_avec"  # Contre-indication
    INTERACTS_WITH = "interagit_avec"  # Interaction médicamenteuse
    SIMILAR_TO = "similaire_a"  # Similarité
    PRECEDES = "precede"  # Relation temporelle
    FOLLOWS = "suit"  # Relation temporelle inverse

class ConceptType(Enum):
    """Types de concepts médicaux"""
    DISEASE = "maladie"
    SYMPTOM = "symptome"
    MEDICATION = "medicament"
    PROCEDURE = "procedure"
    ANATOMY = "anatomie"
    TEST = "test"
    SPECIALTY = "specialite"
    PATHOGEN = "pathogene"
    TREATMENT = "traitement"
    PREVENTION = "prevention"
    RISK_FACTOR = "facteur_risque"
    COMPLICATION = "complication"

@dataclass
class MedicalConcept:
    """Concept médical"""
    id: str
    name: str
    concept_type: ConceptType
    description: str = ""
    synonyms: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    specialty: Optional[str] = None
    frequency: float = 0.0  # Fréquence d'apparition
    importance: float = 0.0  # Score d'importance
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Génère un ID unique pour le concept"""
        import hashlib
        content = f"{self.name}_{self.concept_type.value}"
        concept_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"concept_{self.concept_type.value}_{concept_hash}"

@dataclass
class ConceptLink:
    """Lien entre deux concepts médicaux"""
    id: str
    source_concept_id: str
    target_concept_id: str
    link_type: LinkType
    strength: float = 0.0  # Force du lien (0-1)
    confidence: float = 0.0  # Confiance dans le lien (0-1)
    evidence: List[str] = field(default_factory=list)  # Sources/preuves
    context: Optional[str] = None
    bidirectional: bool = False
    created_date: datetime = field(default_factory=datetime.now)
    validated: bool = False
    validator: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Génère un ID unique pour le lien"""
        import hashlib
        content = f"{self.source_concept_id}_{self.target_concept_id}_{self.link_type.value}"
        link_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"link_{link_hash}"

@dataclass
class ConceptGraph:
    """Graphe de concepts médicaux"""
    concepts: Dict[str, MedicalConcept] = field(default_factory=dict)
    links: Dict[str, ConceptLink] = field(default_factory=dict)
    concept_links: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    link_types_index: Dict[LinkType, Set[str]] = field(default_factory=lambda: defaultdict(set))
    concept_types_index: Dict[ConceptType, Set[str]] = field(default_factory=lambda: defaultdict(set))

@dataclass
class LinkingStats:
    """Statistiques de liaison de concepts"""
    total_concepts: int = 0
    total_links: int = 0
    links_by_type: Dict[str, int] = field(default_factory=dict)
    concepts_by_type: Dict[str, int] = field(default_factory=dict)
    avg_links_per_concept: float = 0.0
    avg_link_strength: float = 0.0
    processing_time: float = 0.0

class ConceptLinker:
    """
    Lieur automatique de concepts médicaux
    
    Objectif couvert:
    - 9. Créer liens entre concepts médicaux
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.graph = ConceptGraph()
        self.stats = LinkingStats()
        
        # Configuration
        self.min_link_strength = self.config.get("min_link_strength", 0.3)
        self.min_confidence = self.config.get("min_confidence", 0.5)
        self.auto_validate_threshold = self.config.get("auto_validate_threshold", 0.8)
        
        # Patterns de détection de liens
        self._init_link_patterns()
        
        # Initialiser les concepts de base
        self._init_base_concepts()
        
        logger.info("Lieur de concepts médicaux initialisé")
    
    def _init_link_patterns(self):
        """Initialise les patterns de détection de liens"""
        self.link_patterns = {
            LinkType.CAUSES: {
                "patterns": [
                    r'(\w+)\s+(?:cause|provoque|entraîne|déclenche)\s+(\w+)',
                    r'(\w+)\s+(?:est causé par|est provoqué par|est dû à)\s+(\w+)',
                    r'(\w+)\s+(?:→|->)\s+(\w+)'
                ],
                "keywords": ["cause", "provoque", "entraîne", "déclenche", "dû à"]
            },
            
            LinkType.TREATS: {
                "patterns": [
                    r'(\w+)\s+(?:traite|soigne|guérit)\s+(\w+)',
                    r'(\w+)\s+(?:pour|contre)\s+(?:le|la|les)?\s*(\w+)',
                    r'traitement\s+(?:de|du|des)?\s*(\w+)\s+(?:par|avec)?\s*(\w+)'
                ],
                "keywords": ["traite", "soigne", "guérit", "traitement", "thérapie"]
            },
            
            LinkType.SYMPTOM_OF: {
                "patterns": [
                    r'(\w+)\s+(?:est un symptôme de|symptôme de|signe de)\s+(\w+)',
                    r'(\w+)\s+(?:présente|manifeste)\s+(\w+)',
                    r'(\w+)\s+(?:avec|accompagné de)\s+(\w+)'
                ],
                "keywords": ["symptôme", "signe", "manifeste", "présente"]
            },
            
            LinkType.DIAGNOSED_BY: {
                "patterns": [
                    r'(\w+)\s+(?:diagnostiqué par|détecté par)\s+(\w+)',
                    r'(\w+)\s+(?:test|examen|analyse)\s+(?:pour|de)?\s*(\w+)',
                    r'diagnostic\s+(?:de|du)?\s*(\w+)\s+(?:par|avec)?\s*(\w+)'
                ],
                "keywords": ["diagnostic", "test", "examen", "analyse", "détection"]
            },
            
            LinkType.PREVENTS: {
                "patterns": [
                    r'(\w+)\s+(?:prévient|évite|protège contre)\s+(\w+)',
                    r'prévention\s+(?:de|du)?\s*(\w+)\s+(?:par|avec)?\s*(\w+)',
                    r'(\w+)\s+(?:pour prévenir|pour éviter)\s+(\w+)'
                ],
                "keywords": ["prévient", "évite", "protège", "prévention", "prophylaxie"]
            },
            
            LinkType.IS_A: {
                "patterns": [
                    r'(\w+)\s+(?:est une?|est un type de)\s+(\w+)',
                    r'(\w+)\s+(?:appartient à|fait partie des)\s+(\w+)',
                    r'(\w+)\s*:\s*type\s+de\s+(\w+)'
                ],
                "keywords": ["est un", "est une", "type de", "appartient à"]
            },
            
            LinkType.PART_OF: {
                "patterns": [
                    r'(\w+)\s+(?:partie de|composant de|élément de)\s+(\w+)',
                    r'(\w+)\s+(?:dans|au niveau de)\s+(\w+)',
                    r'(\w+)\s+(?:du|de la|des)\s+(\w+)'
                ],
                "keywords": ["partie de", "composant", "élément", "dans", "au niveau"]
            }
        }
    
    def _init_base_concepts(self):
        """Initialise les concepts médicaux de base"""
        base_concepts = self._get_base_medical_concepts()
        
        for concept_data in base_concepts:
            concept = MedicalConcept(**concept_data)
            self.add_concept(concept)
        
        # Créer les liens de base
        self._create_base_links()
        
        logger.info(f"Concepts de base initialisés: {len(base_concepts)} concepts")
    
    def _get_base_medical_concepts(self) -> List[Dict[str, Any]]:
        """Retourne les concepts médicaux de base"""
        return [
            # Maladies
            {
                "name": "paludisme",
                "concept_type": ConceptType.DISEASE,
                "description": "Maladie parasitaire transmise par les moustiques Anopheles",
                "synonyms": ["malaria"],
                "keywords": ["plasmodium", "moustique", "fièvre", "parasitaire"],
                "specialty": "infectiologie",
                "frequency": 0.9,
                "importance": 0.95
            },
            {
                "name": "diabète",
                "concept_type": ConceptType.DISEASE,
                "description": "Maladie métabolique caractérisée par une hyperglycémie",
                "synonyms": ["diabète sucré"],
                "keywords": ["glycémie", "insuline", "sucre", "métabolique"],
                "specialty": "endocrinologie",
                "frequency": 0.8,
                "importance": 0.9
            },
            {
                "name": "hypertension",
                "concept_type": ConceptType.DISEASE,
                "description": "Élévation anormale de la pression artérielle",
                "synonyms": ["tension élevée", "HTA"],
                "keywords": ["tension", "pression", "artérielle", "cardiovasculaire"],
                "specialty": "cardiologie",
                "frequency": 0.85,
                "importance": 0.88
            },
            
            # Symptômes
            {
                "name": "fièvre",
                "concept_type": ConceptType.SYMPTOM,
                "description": "Élévation de la température corporelle",
                "synonyms": ["hyperthermie"],
                "keywords": ["température", "chaud", "thermomètre"],
                "frequency": 0.95,
                "importance": 0.9
            },
            {
                "name": "douleur",
                "concept_type": ConceptType.SYMPTOM,
                "description": "Sensation désagréable causée par une lésion",
                "synonyms": ["mal", "souffrance"],
                "keywords": ["mal", "souffrance", "inconfort"],
                "frequency": 0.98,
                "importance": 0.85
            },
            {
                "name": "toux",
                "concept_type": ConceptType.SYMPTOM,
                "description": "Expulsion forcée d'air des poumons",
                "synonyms": [],
                "keywords": ["expectoration", "crachat", "respiratoire"],
                "frequency": 0.8,
                "importance": 0.7
            },
            
            # Médicaments
            {
                "name": "paracétamol",
                "concept_type": ConceptType.MEDICATION,
                "description": "Antalgique et antipyrétique",
                "synonyms": ["acétaminophène"],
                "keywords": ["antalgique", "antipyrétique", "douleur", "fièvre"],
                "frequency": 0.9,
                "importance": 0.8
            },
            {
                "name": "artéméther-luméfantrine",
                "concept_type": ConceptType.MEDICATION,
                "description": "Antipaludique de première ligne",
                "synonyms": ["coartem", "AL"],
                "keywords": ["antipaludique", "artémisinine", "paludisme"],
                "specialty": "infectiologie",
                "frequency": 0.7,
                "importance": 0.9
            },
            {
                "name": "metformine",
                "concept_type": ConceptType.MEDICATION,
                "description": "Antidiabétique oral de première ligne",
                "synonyms": [],
                "keywords": ["antidiabétique", "biguanide", "glycémie"],
                "specialty": "endocrinologie",
                "frequency": 0.6,
                "importance": 0.85
            },
            
            # Tests/Examens
            {
                "name": "TDR paludisme",
                "concept_type": ConceptType.TEST,
                "description": "Test de diagnostic rapide du paludisme",
                "synonyms": ["test rapide paludisme"],
                "keywords": ["diagnostic", "rapide", "plasmodium", "antigène"],
                "specialty": "laboratoire",
                "frequency": 0.8,
                "importance": 0.9
            },
            {
                "name": "glycémie",
                "concept_type": ConceptType.TEST,
                "description": "Mesure du taux de glucose dans le sang",
                "synonyms": ["glucose sanguin"],
                "keywords": ["glucose", "sucre", "sang", "diabète"],
                "specialty": "laboratoire",
                "frequency": 0.75,
                "importance": 0.8
            },
            
            # Anatomie
            {
                "name": "cœur",
                "concept_type": ConceptType.ANATOMY,
                "description": "Organe musculaire qui pompe le sang",
                "synonyms": ["muscle cardiaque"],
                "keywords": ["cardiaque", "pompe", "circulation", "sang"],
                "specialty": "cardiologie",
                "frequency": 0.7,
                "importance": 0.95
            },
            {
                "name": "foie",
                "concept_type": ConceptType.ANATOMY,
                "description": "Organe de détoxification et de métabolisme",
                "synonyms": ["hépatique"],
                "keywords": ["hépatique", "métabolisme", "détoxification"],
                "specialty": "gastroenterologie",
                "frequency": 0.6,
                "importance": 0.85
            },
            
            # Pathogènes
            {
                "name": "plasmodium",
                "concept_type": ConceptType.PATHOGEN,
                "description": "Parasite responsable du paludisme",
                "synonyms": ["hématozoaire"],
                "keywords": ["parasite", "protozoaire", "paludisme"],
                "specialty": "parasitologie",
                "frequency": 0.5,
                "importance": 0.9
            },
            {
                "name": "anopheles",
                "concept_type": ConceptType.PATHOGEN,
                "description": "Moustique vecteur du paludisme",
                "synonyms": ["moustique anophèle"],
                "keywords": ["moustique", "vecteur", "transmission"],
                "specialty": "entomologie",
                "frequency": 0.4,
                "importance": 0.8
            }
        ]
    
    def _create_base_links(self):
        """Crée les liens de base entre concepts"""
        base_links = [
            # Liens causaux
            ("plasmodium", "paludisme", LinkType.CAUSES, 0.95, 0.98),
            ("anopheles", "paludisme", LinkType.CAUSES, 0.8, 0.9),  # transmission
            
            # Liens symptomatiques
            ("fièvre", "paludisme", LinkType.SYMPTOM_OF, 0.9, 0.95),
            ("fièvre", "diabète", LinkType.SYMPTOM_OF, 0.3, 0.6),  # moins fréquent
            
            # Liens thérapeutiques
            ("artéméther-luméfantrine", "paludisme", LinkType.TREATS, 0.95, 0.98),
            ("metformine", "diabète", LinkType.TREATS, 0.9, 0.95),
            ("paracétamol", "fièvre", LinkType.TREATS, 0.85, 0.9),
            ("paracétamol", "douleur", LinkType.TREATS, 0.9, 0.95),
            
            # Liens diagnostiques
            ("TDR paludisme", "paludisme", LinkType.DIAGNOSED_BY, 0.9, 0.95),
            ("glycémie", "diabète", LinkType.DIAGNOSED_BY, 0.95, 0.98),
            
            # Liens anatomiques
            ("cœur", "hypertension", LinkType.ASSOCIATED_WITH, 0.8, 0.85),
            ("foie", "paludisme", LinkType.ASSOCIATED_WITH, 0.6, 0.7),  # complications
        ]
        
        for source_name, target_name, link_type, strength, confidence in base_links:
            source_concept = self._find_concept_by_name(source_name)
            target_concept = self._find_concept_by_name(target_name)
            
            if source_concept and target_concept:
                link = ConceptLink(
                    source_concept_id=source_concept.id,
                    target_concept_id=target_concept.id,
                    link_type=link_type,
                    strength=strength,
                    confidence=confidence,
                    evidence=["Base de connaissances médicales"],
                    validated=True,
                    validator="system"
                )
                self.add_link(link)
    
    def _find_concept_by_name(self, name: str) -> Optional[MedicalConcept]:
        """Trouve un concept par son nom"""
        for concept in self.graph.concepts.values():
            if concept.name.lower() == name.lower() or name.lower() in [s.lower() for s in concept.synonyms]:
                return concept
        return None
    
    def add_concept(self, concept: MedicalConcept) -> bool:
        """
        Ajoute un concept au graphe
        
        Args:
            concept: Concept à ajouter
        
        Returns:
            bool: True si ajouté avec succès
        """
        try:
            if concept.id in self.graph.concepts:
                logger.warning(f"Concept déjà existant: {concept.id}")
                return False
            
            # Ajouter le concept
            self.graph.concepts[concept.id] = concept
            
            # Mettre à jour l'index par type
            self.graph.concept_types_index[concept.concept_type].add(concept.id)
            
            logger.debug(f"Concept ajouté: {concept.name} ({concept.concept_type.value})")
            return True
        
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du concept: {e}")
            return False
    
    def add_link(self, link: ConceptLink) -> bool:
        """
        Ajoute un lien au graphe
        
        Args:
            link: Lien à ajouter
        
        Returns:
            bool: True si ajouté avec succès
        """
        try:
            # Vérifier que les concepts existent
            if (link.source_concept_id not in self.graph.concepts or
                link.target_concept_id not in self.graph.concepts):
                logger.error(f"Concepts manquants pour le lien {link.id}")
                return False
            
            # Vérifier les seuils
            if (link.strength < self.min_link_strength or
                link.confidence < self.min_confidence):
                logger.warning(f"Lien rejeté - seuils non atteints: {link.id}")
                return False
            
            # Ajouter le lien
            self.graph.links[link.id] = link
            
            # Mettre à jour les index
            self.graph.concept_links[link.source_concept_id].add(link.id)
            if link.bidirectional:
                self.graph.concept_links[link.target_concept_id].add(link.id)
            
            self.graph.link_types_index[link.link_type].add(link.id)
            
            # Auto-validation si confiance élevée
            if link.confidence >= self.auto_validate_threshold and not link.validated:
                link.validated = True
                link.validator = "auto_system"
            
            logger.debug(f"Lien ajouté: {link.link_type.value} ({link.strength:.2f})")
            return True
        
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du lien: {e}")
            return False
    
    async def discover_links_from_text(self, text: str, context: Optional[str] = None) -> List[ConceptLink]:
        """
        Découvre automatiquement des liens à partir d'un texte
        
        Args:
            text: Texte à analyser
            context: Contexte optionnel
        
        Returns:
            List[ConceptLink]: Liens découverts
        """
        discovered_links = []
        
        try:
            # Identifier les concepts mentionnés dans le texte
            mentioned_concepts = self._identify_concepts_in_text(text)
            
            if len(mentioned_concepts) < 2:
                return discovered_links
            
            # Rechercher des patterns de liens
            for link_type, pattern_data in self.link_patterns.items():
                for pattern in pattern_data["patterns"]:
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    
                    for match in matches:
                        if len(match.groups()) >= 2:
                            source_term = match.group(1).strip()
                            target_term = match.group(2).strip()
                            
                            source_concept = self._find_concept_by_name(source_term)
                            target_concept = self._find_concept_by_name(target_term)
                            
                            if source_concept and target_concept:
                                # Calculer la force et confiance du lien
                                strength = self._calculate_link_strength(
                                    source_concept, target_concept, link_type, text
                                )
                                confidence = self._calculate_link_confidence(
                                    source_concept, target_concept, link_type, pattern
                                )
                                
                                if strength >= self.min_link_strength and confidence >= self.min_confidence:
                                    link = ConceptLink(
                                        source_concept_id=source_concept.id,
                                        target_concept_id=target_concept.id,
                                        link_type=link_type,
                                        strength=strength,
                                        confidence=confidence,
                                        evidence=[f"Pattern: {pattern}", f"Text: {match.group(0)}"],
                                        context=context
                                    )
                                    discovered_links.append(link)
            
            # Découvrir des liens par co-occurrence
            cooccurrence_links = await self._discover_cooccurrence_links(mentioned_concepts, text)
            discovered_links.extend(cooccurrence_links)
            
            logger.info(f"Liens découverts: {len(discovered_links)}")
            return discovered_links
        
        except Exception as e:
            logger.error(f"Erreur lors de la découverte de liens: {e}")
            return []
    
    def _identify_concepts_in_text(self, text: str) -> List[MedicalConcept]:
        """Identifie les concepts médicaux mentionnés dans un texte"""
        mentioned_concepts = []
        text_lower = text.lower()
        
        for concept in self.graph.concepts.values():
            # Vérifier le nom principal
            if concept.name.lower() in text_lower:
                mentioned_concepts.append(concept)
                continue
            
            # Vérifier les synonymes
            if any(synonym.lower() in text_lower for synonym in concept.synonyms):
                mentioned_concepts.append(concept)
                continue
            
            # Vérifier les mots-clés
            if any(keyword.lower() in text_lower for keyword in concept.keywords):
                mentioned_concepts.append(concept)
        
        return mentioned_concepts
    
    def _calculate_link_strength(self, source: MedicalConcept, target: MedicalConcept, 
                               link_type: LinkType, text: str) -> float:
        """Calcule la force d'un lien"""
        strength = 0.0
        
        # Force basée sur la fréquence des concepts
        freq_factor = (source.frequency + target.frequency) / 2
        strength += freq_factor * 0.3
        
        # Force basée sur l'importance des concepts
        importance_factor = (source.importance + target.importance) / 2
        strength += importance_factor * 0.3
        
        # Force basée sur la proximité dans le texte
        proximity_factor = self._calculate_text_proximity(source.name, target.name, text)
        strength += proximity_factor * 0.2
        
        # Force basée sur le type de lien
        type_weights = {
            LinkType.CAUSES: 0.9,
            LinkType.TREATS: 0.9,
            LinkType.SYMPTOM_OF: 0.8,
            LinkType.DIAGNOSED_BY: 0.8,
            LinkType.PREVENTS: 0.7,
            LinkType.IS_A: 0.8,
            LinkType.PART_OF: 0.7,
            LinkType.ASSOCIATED_WITH: 0.5
        }
        type_factor = type_weights.get(link_type, 0.5)
        strength += type_factor * 0.2
        
        return min(strength, 1.0)
    
    def _calculate_link_confidence(self, source: MedicalConcept, target: MedicalConcept,
                                 link_type: LinkType, pattern: str) -> float:
        """Calcule la confiance d'un lien"""
        confidence = 0.0
        
        # Confiance basée sur la spécificité du pattern
        pattern_specificity = len(pattern.split()) / 10  # Approximation
        confidence += min(pattern_specificity, 0.3)
        
        # Confiance basée sur la cohérence des types de concepts
        type_coherence = self._calculate_type_coherence(source.concept_type, target.concept_type, link_type)
        confidence += type_coherence * 0.4
        
        # Confiance basée sur la spécialité
        if source.specialty and target.specialty:
            if source.specialty == target.specialty:
                confidence += 0.2
            else:
                confidence += 0.1
        else:
            confidence += 0.15
        
        # Confiance de base pour le type de lien
        base_confidence = {
            LinkType.CAUSES: 0.8,
            LinkType.TREATS: 0.8,
            LinkType.SYMPTOM_OF: 0.7,
            LinkType.DIAGNOSED_BY: 0.7,
            LinkType.PREVENTS: 0.6,
            LinkType.IS_A: 0.9,
            LinkType.PART_OF: 0.8,
            LinkType.ASSOCIATED_WITH: 0.4
        }
        confidence += base_confidence.get(link_type, 0.5) * 0.1
        
        return min(confidence, 1.0)
    
    def _calculate_text_proximity(self, term1: str, term2: str, text: str) -> float:
        """Calcule la proximité de deux termes dans un texte"""
        text_lower = text.lower()
        pos1 = text_lower.find(term1.lower())
        pos2 = text_lower.find(term2.lower())
        
        if pos1 == -1 or pos2 == -1:
            return 0.0
        
        distance = abs(pos1 - pos2)
        max_distance = len(text)
        
        # Proximité inversement proportionnelle à la distance
        proximity = 1.0 - (distance / max_distance)
        
        return proximity
    
    def _calculate_type_coherence(self, source_type: ConceptType, target_type: ConceptType, 
                                link_type: LinkType) -> float:
        """Calcule la cohérence entre types de concepts et type de lien"""
        # Règles de cohérence prédéfinies
        coherence_rules = {
            LinkType.CAUSES: {
                (ConceptType.PATHOGEN, ConceptType.DISEASE): 0.9,
                (ConceptType.RISK_FACTOR, ConceptType.DISEASE): 0.8,
                (ConceptType.DISEASE, ConceptType.COMPLICATION): 0.8
            },
            LinkType.TREATS: {
                (ConceptType.MEDICATION, ConceptType.DISEASE): 0.9,
                (ConceptType.MEDICATION, ConceptType.SYMPTOM): 0.8,
                (ConceptType.PROCEDURE, ConceptType.DISEASE): 0.8
            },
            LinkType.SYMPTOM_OF: {
                (ConceptType.SYMPTOM, ConceptType.DISEASE): 0.9
            },
            LinkType.DIAGNOSED_BY: {
                (ConceptType.TEST, ConceptType.DISEASE): 0.9,
                (ConceptType.PROCEDURE, ConceptType.DISEASE): 0.7
            },
            LinkType.PREVENTS: {
                (ConceptType.MEDICATION, ConceptType.DISEASE): 0.8,
                (ConceptType.PREVENTION, ConceptType.DISEASE): 0.9
            }
        }
        
        rules_for_type = coherence_rules.get(link_type, {})
        return rules_for_type.get((source_type, target_type), 0.5)
    
    async def _discover_cooccurrence_links(self, concepts: List[MedicalConcept], 
                                         text: str) -> List[ConceptLink]:
        """Découvre des liens par co-occurrence"""
        cooccurrence_links = []
        
        # Analyser toutes les paires de concepts
        for i, concept1 in enumerate(concepts):
            for concept2 in concepts[i+1:]:
                # Calculer la force de co-occurrence
                cooccurrence_strength = self._calculate_cooccurrence_strength(concept1, concept2, text)
                
                if cooccurrence_strength >= self.min_link_strength:
                    # Déterminer le type de lien le plus probable
                    probable_link_type = self._infer_link_type(concept1, concept2)
                    
                    confidence = cooccurrence_strength * 0.7  # Confiance réduite pour co-occurrence
                    
                    if confidence >= self.min_confidence:
                        link = ConceptLink(
                            source_concept_id=concept1.id,
                            target_concept_id=concept2.id,
                            link_type=probable_link_type,
                            strength=cooccurrence_strength,
                            confidence=confidence,
                            evidence=[f"Co-occurrence dans le texte"],
                            bidirectional=True
                        )
                        cooccurrence_links.append(link)
        
        return cooccurrence_links
    
    def _calculate_cooccurrence_strength(self, concept1: MedicalConcept, 
                                       concept2: MedicalConcept, text: str) -> float:
        """Calcule la force de co-occurrence"""
        # Proximité dans le texte
        proximity = self._calculate_text_proximity(concept1.name, concept2.name, text)
        
        # Fréquence des concepts
        freq_factor = (concept1.frequency + concept2.frequency) / 2
        
        # Importance des concepts
        importance_factor = (concept1.importance + concept2.importance) / 2
        
        # Cohérence des spécialités
        specialty_factor = 0.5
        if concept1.specialty and concept2.specialty:
            if concept1.specialty == concept2.specialty:
                specialty_factor = 0.8
            else:
                specialty_factor = 0.3
        
        strength = (proximity * 0.4 + freq_factor * 0.2 + 
                   importance_factor * 0.2 + specialty_factor * 0.2)
        
        return min(strength, 1.0)
    
    def _infer_link_type(self, concept1: MedicalConcept, concept2: MedicalConcept) -> LinkType:
        """Infère le type de lien le plus probable entre deux concepts"""
        # Règles d'inférence basées sur les types de concepts
        type_rules = {
            (ConceptType.MEDICATION, ConceptType.DISEASE): LinkType.TREATS,
            (ConceptType.MEDICATION, ConceptType.SYMPTOM): LinkType.TREATS,
            (ConceptType.SYMPTOM, ConceptType.DISEASE): LinkType.SYMPTOM_OF,
            (ConceptType.TEST, ConceptType.DISEASE): LinkType.DIAGNOSED_BY,
            (ConceptType.PATHOGEN, ConceptType.DISEASE): LinkType.CAUSES,
            (ConceptType.PREVENTION, ConceptType.DISEASE): LinkType.PREVENTS
        }
        
        # Vérifier les règles directes
        direct_rule = type_rules.get((concept1.concept_type, concept2.concept_type))
        if direct_rule:
            return direct_rule
        
        # Vérifier les règles inverses
        inverse_rule = type_rules.get((concept2.concept_type, concept1.concept_type))
        if inverse_rule:
            return inverse_rule
        
        # Par défaut, association générale
        return LinkType.ASSOCIATED_WITH
    
    def get_concept_links(self, concept_id: str, link_type: Optional[LinkType] = None) -> List[ConceptLink]:
        """Retourne tous les liens d'un concept"""
        link_ids = self.graph.concept_links.get(concept_id, set())
        links = [self.graph.links[link_id] for link_id in link_ids if link_id in self.graph.links]
        
        if link_type:
            links = [link for link in links if link.link_type == link_type]
        
        return links
    
    def get_related_concepts(self, concept_id: str, max_depth: int = 2) -> List[Tuple[MedicalConcept, float]]:
        """Retourne les concepts liés avec leur score de relation"""
        related = []
        visited = set()
        
        def _explore_relations(current_id: str, depth: int, accumulated_strength: float):
            if depth > max_depth or current_id in visited:
                return
            
            visited.add(current_id)
            links = self.get_concept_links(current_id)
            
            for link in links:
                target_id = link.target_concept_id if link.source_concept_id == current_id else link.source_concept_id
                
                if target_id != concept_id and target_id in self.graph.concepts:
                    relation_strength = accumulated_strength * link.strength
                    target_concept = self.graph.concepts[target_id]
                    
                    # Ajouter ou mettre à jour le score
                    existing = next((r for r in related if r[0].id == target_id), None)
                    if existing:
                        if relation_strength > existing[1]:
                            related.remove(existing)
                            related.append((target_concept, relation_strength))
                    else:
                        related.append((target_concept, relation_strength))
                    
                    # Explorer plus profondément
                    if depth < max_depth:
                        _explore_relations(target_id, depth + 1, relation_strength)
        
        _explore_relations(concept_id, 0, 1.0)
        
        # Trier par force de relation
        related.sort(key=lambda x: x[1], reverse=True)
        
        return related
    
    def generate_stats(self) -> LinkingStats:
        """Génère les statistiques de liaison"""
        import time
        start_time = time.time()
        
        stats = LinkingStats()
        stats.total_concepts = len(self.graph.concepts)
        stats.total_links = len(self.graph.links)
        
        # Statistiques par type de lien
        for link_type, link_ids in self.graph.link_types_index.items():
            stats.links_by_type[link_type.value] = len(link_ids)
        
        # Statistiques par type de concept
        for concept_type, concept_ids in self.graph.concept_types_index.items():
            stats.concepts_by_type[concept_type.value] = len(concept_ids)
        
        # Moyenne de liens par concept
        if stats.total_concepts > 0:
            total_concept_links = sum(len(link_ids) for link_ids in self.graph.concept_links.values())
            stats.avg_links_per_concept = total_concept_links / stats.total_concepts
        
        # Force moyenne des liens
        if stats.total_links > 0:
            total_strength = sum(link.strength for link in self.graph.links.values())
            stats.avg_link_strength = total_strength / stats.total_links
        
        stats.processing_time = time.time() - start_time
        
        self.stats = stats
        return stats
    
    def export_graph(self, output_path: str):
        """Exporte le graphe de concepts"""
        graph_data = {
            "metadata": {
                "total_concepts": len(self.graph.concepts),
                "total_links": len(self.graph.links),
                "export_date": datetime.now().isoformat(),
                "version": "2.0.0"
            },
            "concepts": {
                concept_id: {
                    "name": concept.name,
                    "type": concept.concept_type.value,
                    "description": concept.description,
                    "synonyms": concept.synonyms,
                    "keywords": concept.keywords,
                    "specialty": concept.specialty,
                    "frequency": concept.frequency,
                    "importance": concept.importance
                }
                for concept_id, concept in self.graph.concepts.items()
            },
            "links": {
                link_id: {
                    "source": link.source_concept_id,
                    "target": link.target_concept_id,
                    "type": link.link_type.value,
                    "strength": link.strength,
                    "confidence": link.confidence,
                    "evidence": link.evidence,
                    "validated": link.validated,
                    "bidirectional": link.bidirectional
                }
                for link_id, link in self.graph.links.items()
            },
            "statistics": {
                "links_by_type": self.stats.links_by_type,
                "concepts_by_type": self.stats.concepts_by_type,
                "avg_links_per_concept": self.stats.avg_links_per_concept,
                "avg_link_strength": self.stats.avg_link_strength
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Graphe de concepts exporté: {output_path}")

# Test de démonstration
async def main():
    """Fonction de test principale"""
    print("🔗 Test du Lieur de Concepts Médicaux")
    
    # Créer le lieur
    linker = ConceptLinker({
        "min_link_strength": 0.3,
        "min_confidence": 0.5,
        "auto_validate_threshold": 0.8
    })
    
    # Afficher les concepts disponibles
    print(f"\n📚 Concepts disponibles: {len(linker.graph.concepts)}")
    for concept in list(linker.graph.concepts.values())[:5]:  # Afficher les 5 premiers
        print(f"  - {concept.name} ({concept.concept_type.value})")
    
    # Afficher les liens existants
    print(f"\n🔗 Liens existants: {len(linker.graph.links)}")
    for link in list(linker.graph.links.values())[:5]:  # Afficher les 5 premiers
        source = linker.graph.concepts[link.source_concept_id]
        target = linker.graph.concepts[link.target_concept_id]
        print(f"  - {source.name} {link.link_type.value} {target.name} (Force: {link.strength:.2f})")
    
    # Test de découverte de liens à partir de texte
    test_text = """
    Le paludisme est causé par le plasmodium et transmis par les moustiques anopheles.
    Les symptômes incluent la fièvre, les frissons et les maux de tête.
    Le traitement de première ligne est l'artéméther-luméfantrine.
    Le diagnostic se fait par TDR paludisme ou goutte épaisse.
    """
    
    print("\n🔍 Découverte de liens à partir de texte:")
    discovered_links = await linker.discover_links_from_text(test_text, "Test médical")
    
    for link in discovered_links:
        if link.source_concept_id in linker.graph.concepts and link.target_concept_id in linker.graph.concepts:
            source = linker.graph.concepts[link.source_concept_id]
            target = linker.graph.concepts[link.target_concept_id]
            print(f"  - {source.name} {link.link_type.value} {target.name}")
            print(f"    Force: {link.strength:.2f}, Confiance: {link.confidence:.2f}")
    
    # Test de concepts liés
    paludisme_concept = linker._find_concept_by_name("paludisme")
    if paludisme_concept:
        print(f"\n🌐 Concepts liés au paludisme:")
        related = linker.get_related_concepts(paludisme_concept.id, max_depth=2)
        for concept, strength in related[:5]:  # Top 5
            print(f"  - {concept.name} ({concept.concept_type.value}) - Score: {strength:.2f}")
    
    # Générer les statistiques
    stats = linker.generate_stats()
    print(f"\n📊 Statistiques:")
    print(f"  Concepts totaux: {stats.total_concepts}")
    print(f"  Liens totaux: {stats.total_links}")
    print(f"  Liens moyens par concept: {stats.avg_links_per_concept:.1f}")
    print(f"  Force moyenne des liens: {stats.avg_link_strength:.2f}")
    
    print(f"\n📋 Répartition des liens par type:")
    for link_type, count in stats.links_by_type.items():
        print(f"  {link_type}: {count} liens")
    
    # Exporter le graphe
    linker.export_graph("medical_concept_graph.json")
    print("\n✅ Graphe exporté: medical_concept_graph.json")

if __name__ == "__main__":
    asyncio.run(main())