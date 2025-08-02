#!/usr/bin/env python3
"""
Intégrateur de Protocoles DGH

Objectif 6: Intégrer protocoles de soins DGH

Ce module intègre les protocoles de soins spécifiques à l'Hôpital
Général de Douala dans la base de connaissances médicales.

Auteur: Équipe Hackathon Hôpital Général de Douala
Module: 2 - RAG Avancé & Multilingue
Version: 2.0.0
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re
from collections import defaultdict

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProtocolType(Enum):
    """Types de protocoles médicaux"""
    EMERGENCY = "urgence"
    DIAGNOSTIC = "diagnostic"
    THERAPEUTIC = "therapeutique"
    PREVENTIVE = "preventif"
    SURGICAL = "chirurgical"
    NURSING = "soins_infirmiers"
    PHARMACY = "pharmacie"
    LABORATORY = "laboratoire"
    RADIOLOGY = "radiologie"
    INFECTION_CONTROL = "controle_infection"

class ProtocolStatus(Enum):
    """Statut des protocoles"""
    DRAFT = "brouillon"
    UNDER_REVIEW = "en_revision"
    APPROVED = "approuve"
    ACTIVE = "actif"
    SUSPENDED = "suspendu"
    ARCHIVED = "archive"

class UrgencyLevel(Enum):
    """Niveaux d'urgence"""
    IMMEDIATE = "immediat"  # < 15 minutes
    URGENT = "urgent"  # < 1 heure
    SEMI_URGENT = "semi_urgent"  # < 4 heures
    NON_URGENT = "non_urgent"  # < 24 heures
    ROUTINE = "routine"  # > 24 heures

@dataclass
class ProtocolStep:
    """Étape d'un protocole"""
    step_number: int
    title: str
    description: str
    duration_minutes: Optional[int] = None
    required_personnel: List[str] = field(default_factory=list)
    required_equipment: List[str] = field(default_factory=list)
    medications: List[str] = field(default_factory=list)
    contraindications: List[str] = field(default_factory=list)
    complications: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    next_steps: List[int] = field(default_factory=list)
    alternative_steps: List[int] = field(default_factory=list)

@dataclass
class DGHProtocol:
    """Protocole de soins DGH"""
    id: str
    title: str
    protocol_type: ProtocolType
    specialty: str
    description: str
    steps: List[ProtocolStep] = field(default_factory=list)
    indications: List[str] = field(default_factory=list)
    contraindications: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    urgency_level: UrgencyLevel = UrgencyLevel.ROUTINE
    status: ProtocolStatus = ProtocolStatus.DRAFT
    version: str = "1.0"
    created_date: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    approved_by: Optional[str] = None
    approval_date: Optional[datetime] = None
    review_date: Optional[datetime] = None
    authors: List[str] = field(default_factory=list)
    reviewers: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    estimated_duration: Optional[int] = None  # en minutes
    success_rate: Optional[float] = None
    complications_rate: Optional[float] = None
    cost_estimate: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
        
        # Calculer la durée estimée si non fournie
        if not self.estimated_duration and self.steps:
            self.estimated_duration = sum(
                step.duration_minutes or 0 for step in self.steps
            )
    
    def _generate_id(self) -> str:
        """Génère un ID unique pour le protocole"""
        import hashlib
        content = f"{self.title}_{self.specialty}_{self.protocol_type.value}"
        protocol_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"dgh_{self.protocol_type.value}_{protocol_hash}"

@dataclass
class ProtocolValidation:
    """Validation d'un protocole"""
    protocol_id: str
    is_valid: bool
    validation_score: float
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    validated_by: str = "system"
    validation_date: datetime = field(default_factory=datetime.now)
    compliance_score: float = 0.0
    safety_score: float = 0.0
    completeness_score: float = 0.0

@dataclass
class IntegrationStats:
    """Statistiques d'intégration des protocoles"""
    total_protocols: int = 0
    integrated_protocols: int = 0
    rejected_protocols: int = 0
    protocols_by_type: Dict[str, int] = field(default_factory=dict)
    protocols_by_specialty: Dict[str, int] = field(default_factory=dict)
    protocols_by_urgency: Dict[str, int] = field(default_factory=dict)
    avg_validation_score: float = 0.0
    processing_time: float = 0.0

class ProtocolIntegrator:
    """
    Intégrateur de protocoles de soins DGH
    
    Objectif couvert:
    - 6. Intégrer protocoles de soins DGH
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.protocols: Dict[str, DGHProtocol] = {}
        self.validations: Dict[str, ProtocolValidation] = {}
        self.stats = IntegrationStats()
        
        # Configuration
        self.min_validation_score = self.config.get("min_validation_score", 0.7)
        self.auto_approve_threshold = self.config.get("auto_approve_threshold", 0.9)
        self.require_review = self.config.get("require_review", True)
        
        # Initialiser les protocoles de base DGH
        self._init_dgh_protocols()
        
        logger.info("Intégrateur de protocoles DGH initialisé")
    
    def _init_dgh_protocols(self):
        """Initialise les protocoles de base de l'Hôpital Général de Douala"""
        base_protocols = self._get_base_dgh_protocols()
        
        for protocol_data in base_protocols:
            protocol = DGHProtocol(**protocol_data)
            self.add_protocol(protocol)
        
        logger.info(f"Protocoles DGH initialisés: {len(base_protocols)} protocoles")
    
    def _get_base_dgh_protocols(self) -> List[Dict[str, Any]]:
        """Retourne les protocoles de base DGH"""
        return [
            {
                "title": "Prise en charge du paludisme grave",
                "protocol_type": ProtocolType.EMERGENCY,
                "specialty": "infectiologie",
                "description": "Protocole de prise en charge d'urgence du paludisme grave à l'HGD",
                "urgency_level": UrgencyLevel.IMMEDIATE,
                "indications": [
                    "Paludisme avec signes de gravité",
                    "Convulsions",
                    "Coma",
                    "Détresse respiratoire",
                    "Choc"
                ],
                "contraindications": [
                    "Allergie connue à l'artésunate",
                    "Grossesse premier trimestre (relatif)"
                ],
                "steps": [
                    ProtocolStep(
                        step_number=1,
                        title="Évaluation initiale",
                        description="Évaluation rapide de l'état général, constantes vitales, score de Glasgow",
                        duration_minutes=5,
                        required_personnel=["médecin urgentiste", "infirmier"],
                        required_equipment=["tensiomètre", "thermomètre", "oxymètre"]
                    ),
                    ProtocolStep(
                        step_number=2,
                        title="Prélèvements urgents",
                        description="TDR paludisme, glycémie, hémogramme, créatinine",
                        duration_minutes=10,
                        required_personnel=["infirmier", "laborantin"],
                        required_equipment=["TDR paludisme", "glucomètre", "matériel prélèvement"]
                    ),
                    ProtocolStep(
                        step_number=3,
                        title="Traitement immédiat",
                        description="Artésunate IV 2.4 mg/kg, correction hypoglycémie si nécessaire",
                        duration_minutes=15,
                        required_personnel=["médecin", "infirmier"],
                        medications=["Artésunate 60mg", "Glucose 30%", "Sérum physiologique"],
                        contraindications=["Allergie artésunate"]
                    )
                ],
                "authors": ["Dr. Mballa", "Dr. Nkomo"],
                "status": ProtocolStatus.ACTIVE,
                "version": "2.1",
                "keywords": ["paludisme", "urgence", "artésunate", "TDR"]
            },
            
            {
                "title": "Protocole césarienne d'urgence",
                "protocol_type": ProtocolType.SURGICAL,
                "specialty": "gynecologie",
                "description": "Protocole de césarienne en urgence au bloc opératoire DGH",
                "urgency_level": UrgencyLevel.IMMEDIATE,
                "indications": [
                    "Souffrance fœtale aiguë",
                    "Procidence du cordon",
                    "Rupture utérine",
                    "Hémorragie du 3ème trimestre"
                ],
                "contraindications": [
                    "Mort fœtale in utero",
                    "Malformation fœtale incompatible avec la vie"
                ],
                "steps": [
                    ProtocolStep(
                        step_number=1,
                        title="Préparation urgente",
                        description="Information patiente, préparation bloc, équipe chirurgicale",
                        duration_minutes=10,
                        required_personnel=["chirurgien", "anesthésiste", "sage-femme", "IBODE"],
                        required_equipment=["bloc opératoire", "matériel anesthésie", "matériel chirurgie"]
                    ),
                    ProtocolStep(
                        step_number=2,
                        title="Anesthésie",
                        description="Rachianesthésie ou anesthésie générale selon contexte",
                        duration_minutes=15,
                        required_personnel=["anesthésiste", "IADE"],
                        medications=["Bupivacaïne", "Propofol", "Suxaméthonium"],
                        contraindications=["Troubles coagulation", "Infection point ponction"]
                    ),
                    ProtocolStep(
                        step_number=3,
                        title="Intervention chirurgicale",
                        description="Incision, extraction fœtale, délivrance, sutures",
                        duration_minutes=45,
                        required_personnel=["chirurgien", "aide opératoire", "IBODE"],
                        success_criteria=["Extraction fœtale rapide", "Hémostase correcte"]
                    )
                ],
                "authors": ["Dr. Essomba", "Dr. Atangana"],
                "status": ProtocolStatus.ACTIVE,
                "version": "1.8",
                "keywords": ["césarienne", "urgence", "obstétrique", "bloc"]
            },
            
            {
                "title": "Prise en charge crise d'asthme",
                "protocol_type": ProtocolType.THERAPEUTIC,
                "specialty": "pneumologie",
                "description": "Protocole de traitement de la crise d'asthme aux urgences DGH",
                "urgency_level": UrgencyLevel.URGENT,
                "indications": [
                    "Dyspnée aiguë",
                    "Sibilants",
                    "Toux sèche",
                    "Oppression thoracique"
                ],
                "steps": [
                    ProtocolStep(
                        step_number=1,
                        title="Évaluation sévérité",
                        description="Score de sévérité, saturation O2, fréquence respiratoire",
                        duration_minutes=5,
                        required_personnel=["médecin", "infirmier"],
                        required_equipment=["oxymètre", "stéthoscope"]
                    ),
                    ProtocolStep(
                        step_number=2,
                        title="Bronchodilatateurs",
                        description="Salbutamol nébulisé 5mg + Ipratropium 0.5mg",
                        duration_minutes=20,
                        required_personnel=["infirmier"],
                        medications=["Salbutamol 5mg", "Ipratropium 0.5mg"],
                        required_equipment=["nébuliseur", "masque"]
                    ),
                    ProtocolStep(
                        step_number=3,
                        title="Corticothérapie",
                        description="Prednisolone 1mg/kg PO ou Hydrocortisone IV si sévère",
                        duration_minutes=5,
                        medications=["Prednisolone", "Hydrocortisone"],
                        success_criteria=["Amélioration dyspnée", "Diminution sibilants"]
                    )
                ],
                "authors": ["Dr. Fouda"],
                "status": ProtocolStatus.ACTIVE,
                "version": "1.5",
                "keywords": ["asthme", "bronchodilatateur", "nébulisation"]
            },
            
            {
                "title": "Protocole transfusion sanguine",
                "protocol_type": ProtocolType.THERAPEUTIC,
                "specialty": "hematologie",
                "description": "Protocole de transfusion sanguine sécurisée à l'HGD",
                "urgency_level": UrgencyLevel.SEMI_URGENT,
                "indications": [
                    "Anémie sévère < 7g/dL",
                    "Hémorragie active",
                    "Choc hémorragique",
                    "Préparation chirurgicale"
                ],
                "contraindications": [
                    "Refus patient",
                    "Surcharge volémique",
                    "Antécédent réaction transfusionnelle grave"
                ],
                "steps": [
                    ProtocolStep(
                        step_number=1,
                        title="Vérifications pré-transfusionnelles",
                        description="Groupage ABO-Rh, RAI, cross-match, consentement",
                        duration_minutes=30,
                        required_personnel=["médecin", "laborantin"],
                        required_equipment=["tubes EDTA", "étiquettes"]
                    ),
                    ProtocolStep(
                        step_number=2,
                        title="Préparation transfusion",
                        description="Vérification identité, compatibilité, voie veineuse",
                        duration_minutes=15,
                        required_personnel=["infirmier", "médecin"],
                        required_equipment=["cathéter 18G", "transfuseur"]
                    ),
                    ProtocolStep(
                        step_number=3,
                        title="Surveillance transfusion",
                        description="Surveillance clinique continue, constantes toutes les 15min",
                        duration_minutes=120,
                        required_personnel=["infirmier"],
                        complications=["Réaction hémolytique", "Surcharge", "Infection"]
                    )
                ],
                "authors": ["Dr. Kamga", "Dr. Njoya"],
                "status": ProtocolStatus.ACTIVE,
                "version": "2.0",
                "keywords": ["transfusion", "groupage", "compatibilité", "surveillance"]
            },
            
            {
                "title": "Protocole isolement contact COVID-19",
                "protocol_type": ProtocolType.INFECTION_CONTROL,
                "specialty": "infectiologie",
                "description": "Protocole d'isolement et précautions contact pour COVID-19",
                "urgency_level": UrgencyLevel.IMMEDIATE,
                "indications": [
                    "Cas suspect COVID-19",
                    "Cas confirmé COVID-19",
                    "Contact à haut risque"
                ],
                "steps": [
                    ProtocolStep(
                        step_number=1,
                        title="Identification et signalement",
                        description="Identification cas, signalement CLIN, isolement immédiat",
                        duration_minutes=10,
                        required_personnel=["médecin", "infirmier", "hygiéniste"],
                        required_equipment=["chambre individuelle", "signalétique"]
                    ),
                    ProtocolStep(
                        step_number=2,
                        title="Équipements de protection",
                        description="Port obligatoire masque FFP2, gants, surblouse, lunettes",
                        duration_minutes=5,
                        required_personnel=["tout personnel"],
                        required_equipment=["FFP2", "gants", "surblouse", "lunettes"]
                    ),
                    ProtocolStep(
                        step_number=3,
                        title="Prélèvements diagnostiques",
                        description="RT-PCR SARS-CoV-2, antigénémie si disponible",
                        duration_minutes=15,
                        required_personnel=["infirmier", "laborantin"],
                        required_equipment=["écouvillon", "milieu transport"]
                    )
                ],
                "authors": ["Dr. Biwole", "Équipe CLIN"],
                "status": ProtocolStatus.ACTIVE,
                "version": "3.2",
                "keywords": ["COVID-19", "isolement", "EPI", "CLIN"]
            }
        ]
    
    async def integrate_protocols(self, protocols: List[DGHProtocol]) -> IntegrationStats:
        """
        Intègre une liste de protocoles DGH
        
        Args:
            protocols: Liste de protocoles à intégrer
        
        Returns:
            IntegrationStats: Statistiques d'intégration
        """
        import time
        start_time = time.time()
        
        logger.info(f"Intégration de {len(protocols)} protocoles DGH")
        
        # Réinitialiser les statistiques
        self.stats = IntegrationStats()
        self.stats.total_protocols = len(protocols)
        
        # Traiter chaque protocole
        integration_tasks = []
        for protocol in protocols:
            task = asyncio.create_task(self._process_single_protocol(protocol))
            integration_tasks.append(task)
        
        results = await asyncio.gather(*integration_tasks)
        
        # Compiler les résultats
        total_validation_score = 0.0
        valid_protocols = 0
        
        for validation in results:
            if validation:
                if validation.is_valid and validation.validation_score >= self.min_validation_score:
                    self.stats.integrated_protocols += 1
                    total_validation_score += validation.validation_score
                    valid_protocols += 1
                    
                    # Mettre à jour les statistiques par catégorie
                    protocol = self.protocols[validation.protocol_id]
                    self._update_category_stats(protocol)
                else:
                    self.stats.rejected_protocols += 1
        
        # Calculer les statistiques finales
        if valid_protocols > 0:
            self.stats.avg_validation_score = total_validation_score / valid_protocols
        
        self.stats.processing_time = time.time() - start_time
        
        logger.info(f"Intégration terminée en {self.stats.processing_time:.2f}s")
        logger.info(f"Protocoles intégrés: {self.stats.integrated_protocols}/{self.stats.total_protocols}")
        
        return self.stats
    
    async def _process_single_protocol(self, protocol: DGHProtocol) -> Optional[ProtocolValidation]:
        """
        Traite un protocole individuel
        
        Args:
            protocol: Protocole à traiter
        
        Returns:
            Optional[ProtocolValidation]: Résultat de validation
        """
        try:
            # Valider le protocole
            validation = await self._validate_protocol(protocol)
            
            # Stocker la validation
            self.validations[protocol.id] = validation
            
            # Intégrer le protocole s'il est valide
            if validation.is_valid and validation.validation_score >= self.min_validation_score:
                # Auto-approbation si score élevé
                if validation.validation_score >= self.auto_approve_threshold:
                    protocol.status = ProtocolStatus.APPROVED
                    protocol.approval_date = datetime.now()
                    protocol.approved_by = "system_auto"
                elif not self.require_review:
                    protocol.status = ProtocolStatus.ACTIVE
                
                # Ajouter le protocole
                self.protocols[protocol.id] = protocol
                
                logger.debug(f"Protocole intégré: {protocol.title} (Score: {validation.validation_score:.3f})")
            else:
                logger.warning(f"Protocole rejeté: {protocol.title} (Score: {validation.validation_score:.3f})")
            
            return validation
        
        except Exception as e:
            logger.error(f"Erreur lors du traitement du protocole {protocol.title}: {e}")
            return None
    
    async def _validate_protocol(self, protocol: DGHProtocol) -> ProtocolValidation:
        """
        Valide un protocole DGH
        
        Args:
            protocol: Protocole à valider
        
        Returns:
            ProtocolValidation: Résultat de validation
        """
        issues = []
        recommendations = []
        
        # Validation de la complétude
        completeness_score = self._validate_completeness(protocol, issues, recommendations)
        
        # Validation de la sécurité
        safety_score = self._validate_safety(protocol, issues, recommendations)
        
        # Validation de la conformité
        compliance_score = self._validate_compliance(protocol, issues, recommendations)
        
        # Score global
        validation_score = (completeness_score + safety_score + compliance_score) / 3
        
        is_valid = validation_score >= self.min_validation_score and len(issues) == 0
        
        return ProtocolValidation(
            protocol_id=protocol.id,
            is_valid=is_valid,
            validation_score=validation_score,
            issues=issues,
            recommendations=recommendations,
            completeness_score=completeness_score,
            safety_score=safety_score,
            compliance_score=compliance_score
        )
    
    def _validate_completeness(self, protocol: DGHProtocol, issues: List[str], 
                             recommendations: List[str]) -> float:
        """Valide la complétude du protocole"""
        score = 0.0
        
        # Vérifier les champs obligatoires
        if protocol.title and len(protocol.title) > 5:
            score += 0.15
        else:
            issues.append("Titre manquant ou trop court")
        
        if protocol.description and len(protocol.description) > 20:
            score += 0.15
        else:
            issues.append("Description manquante ou insuffisante")
        
        if protocol.steps and len(protocol.steps) >= 2:
            score += 0.2
        else:
            issues.append("Nombre d'étapes insuffisant (minimum 2)")
        
        if protocol.indications:
            score += 0.1
        else:
            recommendations.append("Ajouter les indications du protocole")
        
        if protocol.contraindications:
            score += 0.1
        else:
            recommendations.append("Ajouter les contre-indications")
        
        if protocol.authors:
            score += 0.1
        else:
            recommendations.append("Identifier les auteurs du protocole")
        
        # Vérifier la cohérence des étapes
        if protocol.steps:
            steps_valid = True
            for i, step in enumerate(protocol.steps):
                if step.step_number != i + 1:
                    steps_valid = False
                    break
                if not step.title or not step.description:
                    steps_valid = False
                    break
            
            if steps_valid:
                score += 0.2
            else:
                issues.append("Étapes mal structurées ou incomplètes")
        
        return min(score, 1.0)
    
    def _validate_safety(self, protocol: DGHProtocol, issues: List[str], 
                        recommendations: List[str]) -> float:
        """Valide la sécurité du protocole"""
        score = 0.0
        
        # Vérifier les contre-indications
        if protocol.contraindications and len(protocol.contraindications) >= 1:
            score += 0.3
        else:
            issues.append("Contre-indications non spécifiées")
        
        # Vérifier les complications mentionnées
        complications_mentioned = False
        for step in protocol.steps:
            if step.complications:
                complications_mentioned = True
                break
        
        if complications_mentioned:
            score += 0.2
        else:
            recommendations.append("Mentionner les complications possibles")
        
        # Vérifier les critères de succès
        success_criteria_present = False
        for step in protocol.steps:
            if step.success_criteria:
                success_criteria_present = True
                break
        
        if success_criteria_present:
            score += 0.2
        else:
            recommendations.append("Définir les critères de succès")
        
        # Vérifier la cohérence des médicaments
        if protocol.protocol_type in [ProtocolType.THERAPEUTIC, ProtocolType.EMERGENCY]:
            medications_present = any(step.medications for step in protocol.steps)
            if medications_present:
                score += 0.15
            else:
                recommendations.append("Spécifier les médicaments utilisés")
        else:
            score += 0.15  # Non applicable
        
        # Vérifier le personnel requis
        personnel_specified = any(step.required_personnel for step in protocol.steps)
        if personnel_specified:
            score += 0.15
        else:
            recommendations.append("Spécifier le personnel requis")
        
        return min(score, 1.0)
    
    def _validate_compliance(self, protocol: DGHProtocol, issues: List[str], 
                           recommendations: List[str]) -> float:
        """Valide la conformité aux standards DGH"""
        score = 0.0
        
        # Vérifier le statut
        if protocol.status in [ProtocolStatus.APPROVED, ProtocolStatus.ACTIVE]:
            score += 0.2
        elif protocol.status == ProtocolStatus.UNDER_REVIEW:
            score += 0.1
        
        # Vérifier la version
        if protocol.version and re.match(r'^\d+\.\d+$', protocol.version):
            score += 0.1
        else:
            recommendations.append("Format de version incorrect (ex: 1.0)")
        
        # Vérifier la date de révision
        if protocol.review_date:
            days_since_review = (datetime.now() - protocol.review_date).days
            if days_since_review <= 365:  # Révisé dans l'année
                score += 0.2
            else:
                recommendations.append("Protocole nécessite une révision")
        else:
            recommendations.append("Planifier une date de révision")
        
        # Vérifier l'urgence appropriée
        if protocol.urgency_level:
            if protocol.protocol_type == ProtocolType.EMERGENCY:
                if protocol.urgency_level in [UrgencyLevel.IMMEDIATE, UrgencyLevel.URGENT]:
                    score += 0.15
                else:
                    issues.append("Niveau d'urgence inapproprié pour un protocole d'urgence")
            else:
                score += 0.15  # Acceptable pour autres types
        
        # Vérifier les mots-clés
        if protocol.keywords and len(protocol.keywords) >= 3:
            score += 0.1
        else:
            recommendations.append("Ajouter des mots-clés (minimum 3)")
        
        # Vérifier la spécialité
        valid_specialties = [
            "cardiologie", "endocrinologie", "infectiologie", "pneumologie",
            "neurologie", "pediatrie", "gynecologie", "chirurgie", "urgences",
            "anesthesie", "radiologie", "laboratoire", "pharmacie"
        ]
        
        if protocol.specialty.lower() in valid_specialties:
            score += 0.15
        else:
            recommendations.append(f"Spécialité non reconnue: {protocol.specialty}")
        
        # Vérifier la durée estimée
        if protocol.estimated_duration and protocol.estimated_duration > 0:
            score += 0.1
        else:
            recommendations.append("Estimer la durée du protocole")
        
        return min(score, 1.0)
    
    def _update_category_stats(self, protocol: DGHProtocol):
        """Met à jour les statistiques par catégorie"""
        # Par type
        type_name = protocol.protocol_type.value
        if type_name in self.stats.protocols_by_type:
            self.stats.protocols_by_type[type_name] += 1
        else:
            self.stats.protocols_by_type[type_name] = 1
        
        # Par spécialité
        if protocol.specialty in self.stats.protocols_by_specialty:
            self.stats.protocols_by_specialty[protocol.specialty] += 1
        else:
            self.stats.protocols_by_specialty[protocol.specialty] = 1
        
        # Par urgence
        urgency_name = protocol.urgency_level.value
        if urgency_name in self.stats.protocols_by_urgency:
            self.stats.protocols_by_urgency[urgency_name] += 1
        else:
            self.stats.protocols_by_urgency[urgency_name] = 1
    
    def add_protocol(self, protocol: DGHProtocol) -> bool:
        """
        Ajoute un protocole manuellement
        
        Args:
            protocol: Protocole à ajouter
        
        Returns:
            bool: True si ajouté avec succès
        """
        try:
            if protocol.id in self.protocols:
                logger.warning(f"Protocole déjà existant: {protocol.id}")
                return False
            
            self.protocols[protocol.id] = protocol
            logger.debug(f"Protocole ajouté: {protocol.title}")
            return True
        
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du protocole: {e}")
            return False
    
    def get_protocol(self, protocol_id: str) -> Optional[DGHProtocol]:
        """Retourne un protocole par son ID"""
        return self.protocols.get(protocol_id)
    
    def get_protocols_by_type(self, protocol_type: ProtocolType) -> List[DGHProtocol]:
        """Retourne tous les protocoles d'un type donné"""
        return [p for p in self.protocols.values() if p.protocol_type == protocol_type]
    
    def get_protocols_by_specialty(self, specialty: str) -> List[DGHProtocol]:
        """Retourne tous les protocoles d'une spécialité"""
        return [p for p in self.protocols.values() if p.specialty.lower() == specialty.lower()]
    
    def get_protocols_by_urgency(self, urgency: UrgencyLevel) -> List[DGHProtocol]:
        """Retourne tous les protocoles d'un niveau d'urgence"""
        return [p for p in self.protocols.values() if p.urgency_level == urgency]
    
    def search_protocols(self, query: str) -> List[DGHProtocol]:
        """Recherche des protocoles par mots-clés"""
        results = []
        query_lower = query.lower()
        
        for protocol in self.protocols.values():
            # Rechercher dans le titre
            if query_lower in protocol.title.lower():
                results.append(protocol)
                continue
            
            # Rechercher dans la description
            if query_lower in protocol.description.lower():
                results.append(protocol)
                continue
            
            # Rechercher dans les mots-clés
            if any(query_lower in keyword.lower() for keyword in protocol.keywords):
                results.append(protocol)
                continue
            
            # Rechercher dans les indications
            if any(query_lower in indication.lower() for indication in protocol.indications):
                results.append(protocol)
                continue
        
        return results
    
    def export_protocols_report(self, output_path: str):
        """Exporte un rapport des protocoles intégrés"""
        report = {
            "integration_summary": {
                "total_protocols": self.stats.total_protocols,
                "integrated_protocols": self.stats.integrated_protocols,
                "rejected_protocols": self.stats.rejected_protocols,
                "integration_rate": self.stats.integrated_protocols / self.stats.total_protocols if self.stats.total_protocols > 0 else 0,
                "avg_validation_score": self.stats.avg_validation_score,
                "processing_time": self.stats.processing_time
            },
            "protocols_by_type": self.stats.protocols_by_type,
            "protocols_by_specialty": self.stats.protocols_by_specialty,
            "protocols_by_urgency": self.stats.protocols_by_urgency,
            "protocols": {
                protocol_id: {
                    "title": protocol.title,
                    "type": protocol.protocol_type.value,
                    "specialty": protocol.specialty,
                    "urgency": protocol.urgency_level.value,
                    "status": protocol.status.value,
                    "version": protocol.version,
                    "steps_count": len(protocol.steps),
                    "estimated_duration": protocol.estimated_duration,
                    "keywords": protocol.keywords
                }
                for protocol_id, protocol in self.protocols.items()
            },
            "validations": {
                protocol_id: {
                    "is_valid": validation.is_valid,
                    "validation_score": validation.validation_score,
                    "completeness_score": validation.completeness_score,
                    "safety_score": validation.safety_score,
                    "compliance_score": validation.compliance_score,
                    "issues_count": len(validation.issues),
                    "recommendations_count": len(validation.recommendations)
                }
                for protocol_id, validation in self.validations.items()
            },
            "timestamp": datetime.now().isoformat()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Rapport des protocoles exporté: {output_path}")

# Test de démonstration
async def main():
    """Fonction de test principale"""
    print("🏥 Test de l'Intégrateur de Protocoles DGH")
    
    # Créer l'intégrateur
    integrator = ProtocolIntegrator({
        "min_validation_score": 0.6,
        "auto_approve_threshold": 0.85,
        "require_review": False
    })
    
    # Afficher les protocoles existants
    print(f"\n📋 Protocoles DGH disponibles: {len(integrator.protocols)}")
    for protocol in list(integrator.protocols.values())[:3]:  # Afficher les 3 premiers
        print(f"  - {protocol.title} ({protocol.specialty})")
        print(f"    Type: {protocol.protocol_type.value}, Urgence: {protocol.urgency_level.value}")
        print(f"    Étapes: {len(protocol.steps)}, Durée: {protocol.estimated_duration}min")
    
    # Rechercher des protocoles
    print("\n🔍 Recherche 'paludisme':")
    malaria_protocols = integrator.search_protocols("paludisme")
    for protocol in malaria_protocols:
        print(f"  - {protocol.title}")
    
    # Protocoles par urgence
    print("\n🚨 Protocoles d'urgence immédiate:")
    immediate_protocols = integrator.get_protocols_by_urgency(UrgencyLevel.IMMEDIATE)
    for protocol in immediate_protocols:
        print(f"  - {protocol.title} ({protocol.specialty})")
    
    # Protocoles par spécialité
    print("\n🫀 Protocoles d'infectiologie:")
    infectio_protocols = integrator.get_protocols_by_specialty("infectiologie")
    for protocol in infectio_protocols:
        print(f"  - {protocol.title}")
    
    # Exporter le rapport
    integrator.export_protocols_report("dgh_protocols_report.json")
    print("\n✅ Rapport exporté: dgh_protocols_report.json")

if __name__ == "__main__":
    asyncio.run(main())