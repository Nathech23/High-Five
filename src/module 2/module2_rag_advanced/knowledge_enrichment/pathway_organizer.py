#!/usr/bin/env python3
"""
Organisateur de Parcours de Soins Patient

Objectif 10: Organiser par parcours de soins patient

Ce module organise les informations médicales selon les parcours
de soins standardisés pour optimiser la prise en charge des patients.

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
from collections import defaultdict

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PathwayType(Enum):
    """Types de parcours de soins"""
    EMERGENCY = "urgence"
    PREVENTIVE = "preventif"
    CHRONIC = "chronique"
    ACUTE = "aigu"
    REHABILITATION = "readaptation"
    PALLIATIVE = "palliatif"
    MATERNAL = "maternel"
    PEDIATRIC = "pediatrique"
    SURGICAL = "chirurgical"
    OUTPATIENT = "ambulatoire"
    INPATIENT = "hospitalisation"
    FOLLOW_UP = "suivi"

class PathwayStage(Enum):
    """Étapes du parcours de soins"""
    PREVENTION = "prevention"
    SCREENING = "depistage"
    DIAGNOSIS = "diagnostic"
    TREATMENT = "traitement"
    MONITORING = "surveillance"
    FOLLOW_UP = "suivi"
    REHABILITATION = "readaptation"
    PALLIATIVE_CARE = "soins_palliatifs"
    DISCHARGE = "sortie"
    COMMUNITY_CARE = "soins_communautaires"

class UrgencyLevel(Enum):
    """Niveaux d'urgence"""
    IMMEDIATE = "immediat"  # < 15 minutes
    URGENT = "urgent"      # < 1 heure
    SEMI_URGENT = "semi_urgent"  # < 4 heures
    NON_URGENT = "non_urgent"    # < 24 heures
    SCHEDULED = "programme"      # Programmé

class ResourceType(Enum):
    """Types de ressources nécessaires"""
    PERSONNEL = "personnel"
    EQUIPMENT = "equipement"
    MEDICATION = "medicament"
    LABORATORY = "laboratoire"
    IMAGING = "imagerie"
    CONSULTATION = "consultation"
    PROCEDURE = "procedure"
    EDUCATION = "education"
    TRANSPORT = "transport"
    ACCOMMODATION = "hebergement"

@dataclass
class PathwayStep:
    """Étape d'un parcours de soins"""
    id: str
    name: str
    stage: PathwayStage
    description: str
    duration_hours: Optional[float] = None
    required_resources: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)  # IDs des étapes précédentes
    outcomes: List[str] = field(default_factory=list)  # Résultats possibles
    decision_points: List[str] = field(default_factory=list)  # Points de décision
    quality_indicators: List[str] = field(default_factory=list)
    cost_estimate: Optional[float] = None
    urgency_level: UrgencyLevel = UrgencyLevel.SCHEDULED
    optional: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CarePathway:
    """Parcours de soins complet"""
    id: str
    name: str
    pathway_type: PathwayType
    condition: str  # Condition médicale principale
    description: str
    target_population: List[str] = field(default_factory=list)
    steps: List[PathwayStep] = field(default_factory=list)
    total_duration_days: Optional[float] = None
    success_criteria: List[str] = field(default_factory=list)
    quality_metrics: List[str] = field(default_factory=list)
    cost_estimate: Optional[float] = None
    evidence_level: str = "C"  # A, B, C selon les recommandations
    last_updated: datetime = field(default_factory=datetime.now)
    version: str = "1.0"
    specialty: Optional[str] = None
    complexity_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
        
        # Calculer la durée totale si non spécifiée
        if not self.total_duration_days and self.steps:
            total_hours = sum(step.duration_hours or 0 for step in self.steps)
            self.total_duration_days = total_hours / 24
        
        # Calculer le score de complexité
        if not self.complexity_score:
            self.complexity_score = self._calculate_complexity()
    
    def _generate_id(self) -> str:
        """Génère un ID unique pour le parcours"""
        import hashlib
        content = f"{self.name}_{self.condition}_{self.pathway_type.value}"
        pathway_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"pathway_{self.pathway_type.value}_{pathway_hash}"
    
    def _calculate_complexity(self) -> float:
        """Calcule le score de complexité du parcours"""
        complexity = 0.0
        
        # Complexité basée sur le nombre d'étapes
        complexity += len(self.steps) * 0.1
        
        # Complexité basée sur les points de décision
        total_decisions = sum(len(step.decision_points) for step in self.steps)
        complexity += total_decisions * 0.2
        
        # Complexité basée sur les ressources requises
        total_resources = sum(len(step.required_resources) for step in self.steps)
        complexity += total_resources * 0.05
        
        # Complexité basée sur la durée
        if self.total_duration_days:
            if self.total_duration_days > 30:
                complexity += 0.5
            elif self.total_duration_days > 7:
                complexity += 0.3
            elif self.total_duration_days > 1:
                complexity += 0.1
        
        # Complexité basée sur le type de parcours
        type_complexity = {
            PathwayType.EMERGENCY: 0.8,
            PathwayType.SURGICAL: 0.7,
            PathwayType.CHRONIC: 0.6,
            PathwayType.ACUTE: 0.5,
            PathwayType.PREVENTIVE: 0.2
        }
        complexity += type_complexity.get(self.pathway_type, 0.3)
        
        return min(complexity, 10.0)  # Score max de 10

@dataclass
class PathwayValidation:
    """Validation d'un parcours de soins"""
    pathway_id: str
    is_valid: bool
    completeness_score: float
    evidence_quality: str
    clinical_relevance: float
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    validator: Optional[str] = None
    validation_date: datetime = field(default_factory=datetime.now)

@dataclass
class OrganizationStats:
    """Statistiques d'organisation des parcours"""
    total_pathways: int = 0
    pathways_by_type: Dict[str, int] = field(default_factory=dict)
    pathways_by_specialty: Dict[str, int] = field(default_factory=dict)
    avg_complexity: float = 0.0
    avg_duration: float = 0.0
    total_steps: int = 0
    validation_rate: float = 0.0
    processing_time: float = 0.0

class PathwayOrganizer:
    """
    Organisateur de parcours de soins patient
    
    Objectif couvert:
    - 10. Organiser par parcours de soins patient
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.pathways: Dict[str, CarePathway] = {}
        self.validations: Dict[str, PathwayValidation] = {}
        self.stats = OrganizationStats()
        
        # Index pour recherche rapide
        self.pathways_by_condition: Dict[str, List[str]] = defaultdict(list)
        self.pathways_by_type: Dict[PathwayType, List[str]] = defaultdict(list)
        self.pathways_by_specialty: Dict[str, List[str]] = defaultdict(list)
        
        # Configuration
        self.min_completeness_score = self.config.get("min_completeness_score", 0.7)
        self.auto_validate_threshold = self.config.get("auto_validate_threshold", 0.9)
        
        # Initialiser les parcours de base
        self._init_base_pathways()
        
        logger.info("Organisateur de parcours de soins initialisé")
    
    def _init_base_pathways(self):
        """Initialise les parcours de soins de base pour l'HGD"""
        base_pathways = self._get_base_pathways()
        
        for pathway_data in base_pathways:
            pathway = CarePathway(**pathway_data)
            self.add_pathway(pathway)
        
        logger.info(f"Parcours de base initialisés: {len(base_pathways)} parcours")
    
    def _get_base_pathways(self) -> List[Dict[str, Any]]:
        """Retourne les parcours de soins de base"""
        return [
            # Parcours Paludisme
            {
                "name": "Prise en charge du paludisme simple",
                "pathway_type": PathwayType.ACUTE,
                "condition": "paludisme",
                "description": "Parcours standardisé pour la prise en charge du paludisme simple chez l'adulte",
                "target_population": ["adultes", "adolescents > 15 ans"],
                "specialty": "infectiologie",
                "evidence_level": "A",
                "steps": [
                    PathwayStep(
                        id="paludisme_01",
                        name="Accueil et triage",
                        stage=PathwayStage.SCREENING,
                        description="Évaluation initiale des symptômes et signes vitaux",
                        duration_hours=0.5,
                        required_resources=["personnel_infirmier", "thermometre", "tensiometre"],
                        urgency_level=UrgencyLevel.URGENT,
                        quality_indicators=["temps_attente < 30min", "evaluation_complete"]
                    ),
                    PathwayStep(
                        id="paludisme_02",
                        name="Diagnostic rapide",
                        stage=PathwayStage.DIAGNOSIS,
                        description="TDR paludisme et évaluation clinique",
                        duration_hours=0.5,
                        required_resources=["TDR_paludisme", "personnel_laboratoire"],
                        prerequisites=["paludisme_01"],
                        outcomes=["TDR_positif", "TDR_negatif", "TDR_invalide"],
                        decision_points=["si_TDR_positif_continuer", "si_TDR_negatif_rechercher_autre_cause"],
                        quality_indicators=["TDR_realise_correctement", "resultat_disponible < 30min"]
                    ),
                    PathwayStep(
                        id="paludisme_03",
                        name="Traitement antipaludique",
                        stage=PathwayStage.TREATMENT,
                        description="Administration d'artéméther-luméfantrine selon le poids",
                        duration_hours=1.0,
                        required_resources=["artemether_lumefantrine", "balance", "personnel_medical"],
                        prerequisites=["paludisme_02"],
                        outcomes=["traitement_administre", "allergie_medicamenteuse", "vomissements"],
                        decision_points=["ajuster_dose_selon_poids", "surveiller_tolerance"],
                        quality_indicators=["dose_correcte", "education_patient_realisee"],
                        cost_estimate=15.0  # USD
                    ),
                    PathwayStep(
                        id="paludisme_04",
                        name="Surveillance et éducation",
                        stage=PathwayStage.MONITORING,
                        description="Surveillance de la tolérance et éducation du patient",
                        duration_hours=2.0,
                        required_resources=["personnel_infirmier", "materiel_education"],
                        prerequisites=["paludisme_03"],
                        outcomes=["tolerance_bonne", "effets_secondaires", "amelioration_symptomes"],
                        quality_indicators=["patient_eduque", "signes_alarme_expliques"]
                    ),
                    PathwayStep(
                        id="paludisme_05",
                        name="Sortie et suivi",
                        stage=PathwayStage.DISCHARGE,
                        description="Planification du suivi et conseils de sortie",
                        duration_hours=0.5,
                        required_resources=["personnel_medical", "ordonnance"],
                        prerequisites=["paludisme_04"],
                        outcomes=["sortie_autorisee", "hospitalisation_necessaire"],
                        decision_points=["evaluer_criteres_sortie"],
                        quality_indicators=["rdv_suivi_programme", "ordonnance_complete"]
                    )
                ],
                "success_criteria": [
                    "TDR négatif à J3",
                    "Disparition de la fièvre < 48h",
                    "Amélioration clinique",
                    "Observance thérapeutique"
                ],
                "quality_metrics": [
                    "Taux de guérison > 95%",
                    "Temps de prise en charge < 4h",
                    "Satisfaction patient > 80%"
                ],
                "cost_estimate": 25.0
            },
            
            # Parcours Diabète
            {
                "name": "Suivi du diabète de type 2",
                "pathway_type": PathwayType.CHRONIC,
                "condition": "diabete_type2",
                "description": "Parcours de suivi chronique du diabète de type 2",
                "target_population": ["adultes", "diabetiques_type2"],
                "specialty": "endocrinologie",
                "evidence_level": "A",
                "steps": [
                    PathwayStep(
                        id="diabete_01",
                        name="Consultation de suivi",
                        stage=PathwayStage.MONITORING,
                        description="Évaluation clinique trimestrielle",
                        duration_hours=1.0,
                        required_resources=["personnel_medical", "glucometre", "tensiometre"],
                        urgency_level=UrgencyLevel.SCHEDULED,
                        quality_indicators=["HbA1c_mesuree", "poids_mesure", "TA_mesuree"]
                    ),
                    PathwayStep(
                        id="diabete_02",
                        name="Examens biologiques",
                        stage=PathwayStage.MONITORING,
                        description="HbA1c, créatininémie, bilan lipidique",
                        duration_hours=0.5,
                        required_resources=["laboratoire", "tubes_prelevement"],
                        prerequisites=["diabete_01"],
                        quality_indicators=["prelevements_realises", "resultats_disponibles < 24h"]
                    ),
                    PathwayStep(
                        id="diabete_03",
                        name="Ajustement thérapeutique",
                        stage=PathwayStage.TREATMENT,
                        description="Adaptation du traitement selon les résultats",
                        duration_hours=0.5,
                        required_resources=["personnel_medical", "guidelines_diabete"],
                        prerequisites=["diabete_02"],
                        decision_points=["si_HbA1c > 7%_intensifier", "si_hypoglycemies_reduire"],
                        quality_indicators=["objectifs_glycemiques_definis"]
                    ),
                    PathwayStep(
                        id="diabete_04",
                        name="Éducation thérapeutique",
                        stage=PathwayStage.EDUCATION,
                        description="Renforcement de l'éducation du patient",
                        duration_hours=1.0,
                        required_resources=["educateur_diabete", "materiel_pedagogique"],
                        prerequisites=["diabete_03"],
                        quality_indicators=["competences_evaluees", "plan_education_actualise"]
                    ),
                    PathwayStep(
                        id="diabete_05",
                        name="Dépistage complications",
                        stage=PathwayStage.SCREENING,
                        description="Recherche de complications micro et macrovasculaires",
                        duration_hours=1.0,
                        required_resources=["ophtalmoscope", "monofilament", "ECG"],
                        prerequisites=["diabete_01"],
                        outcomes=["complications_detectees", "pas_complications"],
                        quality_indicators=["examen_pieds_realise", "fond_oeil_programme"]
                    )
                ],
                "success_criteria": [
                    "HbA1c < 7%",
                    "TA < 140/90 mmHg",
                    "LDL < 1g/L",
                    "Absence de complications"
                ],
                "quality_metrics": [
                    "Taux d'atteinte objectifs glycémiques > 60%",
                    "Observance thérapeutique > 80%",
                    "Satisfaction patient > 85%"
                ],
                "cost_estimate": 45.0
            },
            
            # Parcours Hypertension
            {
                "name": "Prise en charge de l'hypertension artérielle",
                "pathway_type": PathwayType.CHRONIC,
                "condition": "hypertension",
                "description": "Parcours de diagnostic et suivi de l'HTA",
                "target_population": ["adultes", "hypertendus"],
                "specialty": "cardiologie",
                "evidence_level": "A",
                "steps": [
                    PathwayStep(
                        id="hta_01",
                        name="Diagnostic initial",
                        stage=PathwayStage.DIAGNOSIS,
                        description="Confirmation du diagnostic d'HTA",
                        duration_hours=1.0,
                        required_resources=["tensiometre_valide", "personnel_forme"],
                        urgency_level=UrgencyLevel.SEMI_URGENT,
                        quality_indicators=["3_mesures_realisees", "technique_correcte"]
                    ),
                    PathwayStep(
                        id="hta_02",
                        name="Bilan initial",
                        stage=PathwayStage.DIAGNOSIS,
                        description="Recherche de facteurs de risque et complications",
                        duration_hours=1.5,
                        required_resources=["ECG", "laboratoire", "personnel_medical"],
                        prerequisites=["hta_01"],
                        quality_indicators=["bilan_complet_realise", "stratification_risque"]
                    ),
                    PathwayStep(
                        id="hta_03",
                        name="Initiation traitement",
                        stage=PathwayStage.TREATMENT,
                        description="Début du traitement antihypertenseur",
                        duration_hours=0.5,
                        required_resources=["antihypertenseurs", "personnel_medical"],
                        prerequisites=["hta_02"],
                        decision_points=["choix_molecule_selon_profil"],
                        quality_indicators=["molecule_appropriee", "posologie_correcte"]
                    ),
                    PathwayStep(
                        id="hta_04",
                        name="Suivi rapproché",
                        stage=PathwayStage.MONITORING,
                        description="Surveillance mensuelle les 3 premiers mois",
                        duration_hours=0.5,
                        required_resources=["tensiometre", "personnel_infirmier"],
                        prerequisites=["hta_03"],
                        outcomes=["objectif_atteint", "ajustement_necessaire"],
                        quality_indicators=["TA_controlee < 140/90"]
                    )
                ],
                "success_criteria": [
                    "TA < 140/90 mmHg",
                    "Observance > 80%",
                    "Absence d'effets secondaires majeurs"
                ],
                "quality_metrics": [
                    "Taux de contrôle tensionnel > 70%",
                    "Observance thérapeutique > 75%"
                ],
                "cost_estimate": 35.0
            },
            
            # Parcours Urgence
            {
                "name": "Triage et prise en charge urgences",
                "pathway_type": PathwayType.EMERGENCY,
                "condition": "urgence_generale",
                "description": "Parcours de triage et orientation aux urgences",
                "target_population": ["tous_ages", "urgences"],
                "specialty": "urgences",
                "evidence_level": "B",
                "steps": [
                    PathwayStep(
                        id="urgence_01",
                        name="Accueil et triage",
                        stage=PathwayStage.SCREENING,
                        description="Évaluation rapide de la gravité",
                        duration_hours=0.25,
                        required_resources=["infirmier_triage", "echelle_triage"],
                        urgency_level=UrgencyLevel.IMMEDIATE,
                        outcomes=["P1_vital", "P2_urgent", "P3_semi_urgent", "P4_non_urgent"],
                        decision_points=["orientation_selon_gravite"],
                        quality_indicators=["triage_realise < 15min", "classification_correcte"]
                    ),
                    PathwayStep(
                        id="urgence_02",
                        name="Prise en charge médicale",
                        stage=PathwayStage.DIAGNOSIS,
                        description="Évaluation médicale selon priorité",
                        duration_hours=1.0,
                        required_resources=["medecin_urgentiste", "materiel_urgence"],
                        prerequisites=["urgence_01"],
                        outcomes=["diagnostic_pose", "examens_complementaires", "transfert_specialiste"],
                        quality_indicators=["delai_prise_charge_respecte"]
                    ),
                    PathwayStep(
                        id="urgence_03",
                        name="Traitement et stabilisation",
                        stage=PathwayStage.TREATMENT,
                        description="Traitement initial et stabilisation",
                        duration_hours=2.0,
                        required_resources=["medicaments_urgence", "materiel_ranimation"],
                        prerequisites=["urgence_02"],
                        outcomes=["patient_stabilise", "transfert_reanimation", "deces"],
                        quality_indicators=["stabilisation_obtenue"]
                    ),
                    PathwayStep(
                        id="urgence_04",
                        name="Orientation",
                        stage=PathwayStage.DISCHARGE,
                        description="Décision d'hospitalisation ou sortie",
                        duration_hours=0.5,
                        required_resources=["medecin_senior", "lits_disponibles"],
                        prerequisites=["urgence_03"],
                        outcomes=["hospitalisation", "sortie_domicile", "transfert_autre_hopital"],
                        decision_points=["criteres_hospitalisation"],
                        quality_indicators=["decision_appropriee", "famille_informee"]
                    )
                ],
                "success_criteria": [
                    "Délais de prise en charge respectés",
                    "Taux de mortalité < 2%",
                    "Satisfaction usagers > 70%"
                ],
                "quality_metrics": [
                    "Temps d'attente P1 < 15min",
                    "Temps d'attente P2 < 1h",
                    "Taux de retour < 72h < 5%"
                ],
                "cost_estimate": 50.0
            },
            
            # Parcours Prévention
            {
                "name": "Consultation de médecine préventive",
                "pathway_type": PathwayType.PREVENTIVE,
                "condition": "prevention_generale",
                "description": "Parcours de prévention et dépistage",
                "target_population": ["adultes_sains", "facteurs_risque"],
                "specialty": "medecine_generale",
                "evidence_level": "B",
                "steps": [
                    PathwayStep(
                        id="prevention_01",
                        name="Anamnèse et examen",
                        stage=PathwayStage.SCREENING,
                        description="Évaluation des facteurs de risque",
                        duration_hours=1.0,
                        required_resources=["medecin_generaliste", "questionnaire_risque"],
                        urgency_level=UrgencyLevel.SCHEDULED,
                        quality_indicators=["facteurs_risque_identifies", "examen_complet"]
                    ),
                    PathwayStep(
                        id="prevention_02",
                        name="Dépistages ciblés",
                        stage=PathwayStage.SCREENING,
                        description="Dépistages selon âge et facteurs de risque",
                        duration_hours=1.0,
                        required_resources=["materiel_depistage", "laboratoire"],
                        prerequisites=["prevention_01"],
                        outcomes=["depistages_normaux", "anomalies_detectees"],
                        quality_indicators=["depistages_age_appropries"]
                    ),
                    PathwayStep(
                        id="prevention_03",
                        name="Vaccinations",
                        stage=PathwayStage.PREVENTION,
                        description="Mise à jour du calendrier vaccinal",
                        duration_hours=0.5,
                        required_resources=["vaccins", "personnel_vaccine"],
                        prerequisites=["prevention_01"],
                        outcomes=["vaccinations_a_jour", "contre_indications"],
                        quality_indicators=["calendrier_respecte"]
                    ),
                    PathwayStep(
                        id="prevention_04",
                        name="Conseils hygiéno-diététiques",
                        stage=PathwayStage.EDUCATION,
                        description="Éducation pour la santé",
                        duration_hours=0.5,
                        required_resources=["materiel_education", "dieteticien"],
                        prerequisites=["prevention_01"],
                        quality_indicators=["conseils_personnalises", "objectifs_definis"]
                    )
                ],
                "success_criteria": [
                    "Facteurs de risque identifiés",
                    "Dépistages à jour",
                    "Vaccinations complètes",
                    "Patient éduqué"
                ],
                "quality_metrics": [
                    "Taux de dépistage > 80%",
                    "Couverture vaccinale > 90%",
                    "Satisfaction patient > 85%"
                ],
                "cost_estimate": 30.0
            }
        ]
    
    def add_pathway(self, pathway: CarePathway) -> bool:
        """
        Ajoute un parcours de soins
        
        Args:
            pathway: Parcours à ajouter
        
        Returns:
            bool: True si ajouté avec succès
        """
        try:
            if pathway.id in self.pathways:
                logger.warning(f"Parcours déjà existant: {pathway.id}")
                return False
            
            # Valider le parcours
            validation = self.validate_pathway(pathway)
            if not validation.is_valid:
                logger.error(f"Parcours invalide: {pathway.id} - {validation.issues}")
                return False
            
            # Ajouter le parcours
            self.pathways[pathway.id] = pathway
            self.validations[pathway.id] = validation
            
            # Mettre à jour les index
            self.pathways_by_condition[pathway.condition.lower()].append(pathway.id)
            self.pathways_by_type[pathway.pathway_type].append(pathway.id)
            if pathway.specialty:
                self.pathways_by_specialty[pathway.specialty.lower()].append(pathway.id)
            
            logger.info(f"Parcours ajouté: {pathway.name}")
            return True
        
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du parcours: {e}")
            return False
    
    def validate_pathway(self, pathway: CarePathway) -> PathwayValidation:
        """
        Valide un parcours de soins
        
        Args:
            pathway: Parcours à valider
        
        Returns:
            PathwayValidation: Résultat de la validation
        """
        issues = []
        recommendations = []
        completeness_score = 0.0
        clinical_relevance = 0.0
        
        # Validation de base
        if not pathway.name:
            issues.append("Nom du parcours manquant")
        else:
            completeness_score += 0.1
        
        if not pathway.condition:
            issues.append("Condition médicale manquante")
        else:
            completeness_score += 0.1
        
        if not pathway.description:
            issues.append("Description manquante")
        else:
            completeness_score += 0.1
        
        # Validation des étapes
        if not pathway.steps:
            issues.append("Aucune étape définie")
        else:
            completeness_score += 0.2
            
            # Vérifier la cohérence des étapes
            step_ids = {step.id for step in pathway.steps}
            for step in pathway.steps:
                # Vérifier les prérequis
                for prereq in step.prerequisites:
                    if prereq not in step_ids:
                        issues.append(f"Prérequis invalide dans {step.id}: {prereq}")
                
                # Vérifier les ressources
                if not step.required_resources:
                    recommendations.append(f"Définir les ressources pour {step.id}")
                
                # Vérifier les indicateurs qualité
                if not step.quality_indicators:
                    recommendations.append(f"Ajouter des indicateurs qualité pour {step.id}")
            
            # Vérifier la séquence logique des étapes
            stages = [step.stage for step in pathway.steps]
            if PathwayStage.TREATMENT in stages and PathwayStage.DIAGNOSIS not in stages:
                issues.append("Traitement sans diagnostic préalable")
        
        # Validation des critères de succès
        if not pathway.success_criteria:
            recommendations.append("Définir des critères de succès")
        else:
            completeness_score += 0.1
        
        # Validation des métriques qualité
        if not pathway.quality_metrics:
            recommendations.append("Définir des métriques de qualité")
        else:
            completeness_score += 0.1
        
        # Validation de la population cible
        if not pathway.target_population:
            recommendations.append("Définir la population cible")
        else:
            completeness_score += 0.1
        
        # Validation du niveau de preuve
        if pathway.evidence_level not in ["A", "B", "C"]:
            issues.append("Niveau de preuve invalide (doit être A, B ou C)")
        else:
            completeness_score += 0.1
            
            # Score de pertinence clinique basé sur le niveau de preuve
            evidence_scores = {"A": 1.0, "B": 0.8, "C": 0.6}
            clinical_relevance = evidence_scores.get(pathway.evidence_level, 0.5)
        
        # Validation de la durée
        if pathway.total_duration_days and pathway.total_duration_days > 365:
            recommendations.append("Durée très longue, vérifier la pertinence")
        
        # Score final
        completeness_score += 0.1  # Score de base
        
        # Déterminer la validité
        is_valid = (len(issues) == 0 and 
                   completeness_score >= self.min_completeness_score)
        
        # Qualité de l'évidence
        evidence_quality = "Élevée" if pathway.evidence_level == "A" else \
                          "Modérée" if pathway.evidence_level == "B" else "Faible"
        
        return PathwayValidation(
            pathway_id=pathway.id,
            is_valid=is_valid,
            completeness_score=completeness_score,
            evidence_quality=evidence_quality,
            clinical_relevance=clinical_relevance,
            issues=issues,
            recommendations=recommendations,
            validator="system"
        )
    
    def search_pathways(self, condition: Optional[str] = None,
                       pathway_type: Optional[PathwayType] = None,
                       specialty: Optional[str] = None,
                       target_population: Optional[str] = None) -> List[CarePathway]:
        """
        Recherche des parcours selon des critères
        
        Args:
            condition: Condition médicale
            pathway_type: Type de parcours
            specialty: Spécialité médicale
            target_population: Population cible
        
        Returns:
            List[CarePathway]: Parcours correspondants
        """
        results = []
        
        # Recherche par condition
        if condition:
            pathway_ids = self.pathways_by_condition.get(condition.lower(), [])
            results.extend([self.pathways[pid] for pid in pathway_ids])
        
        # Recherche par type
        elif pathway_type:
            pathway_ids = self.pathways_by_type.get(pathway_type, [])
            results.extend([self.pathways[pid] for pid in pathway_ids])
        
        # Recherche par spécialité
        elif specialty:
            pathway_ids = self.pathways_by_specialty.get(specialty.lower(), [])
            results.extend([self.pathways[pid] for pid in pathway_ids])
        
        # Recherche générale
        else:
            results = list(self.pathways.values())
        
        # Filtrage par population cible
        if target_population:
            results = [
                pathway for pathway in results
                if any(target_population.lower() in pop.lower() 
                      for pop in pathway.target_population)
            ]
        
        # Trier par complexité (plus simple en premier)
        results.sort(key=lambda p: p.complexity_score)
        
        return results
    
    def get_pathway_recommendations(self, condition: str, 
                                  patient_profile: Dict[str, Any]) -> List[Tuple[CarePathway, float]]:
        """
        Recommande des parcours pour un patient
        
        Args:
            condition: Condition médicale
            patient_profile: Profil du patient (âge, sexe, comorbidités, etc.)
        
        Returns:
            List[Tuple[CarePathway, float]]: Parcours avec score de pertinence
        """
        pathways = self.search_pathways(condition=condition)
        recommendations = []
        
        for pathway in pathways:
            relevance_score = self._calculate_pathway_relevance(pathway, patient_profile)
            if relevance_score > 0.3:  # Seuil minimum
                recommendations.append((pathway, relevance_score))
        
        # Trier par score de pertinence
        recommendations.sort(key=lambda x: x[1], reverse=True)
        
        return recommendations
    
    def _calculate_pathway_relevance(self, pathway: CarePathway, 
                                   patient_profile: Dict[str, Any]) -> float:
        """Calcule la pertinence d'un parcours pour un patient"""
        relevance = 0.0
        
        # Pertinence basée sur l'âge
        patient_age = patient_profile.get("age", 0)
        if "adultes" in pathway.target_population and 18 <= patient_age <= 65:
            relevance += 0.3
        elif "pediatrique" in pathway.target_population and patient_age < 18:
            relevance += 0.3
        elif "geriatrique" in pathway.target_population and patient_age > 65:
            relevance += 0.3
        
        # Pertinence basée sur les comorbidités
        comorbidities = patient_profile.get("comorbidities", [])
        if comorbidities:
            # Parcours chroniques plus pertinents si comorbidités
            if pathway.pathway_type == PathwayType.CHRONIC:
                relevance += 0.2
        
        # Pertinence basée sur l'urgence
        urgency = patient_profile.get("urgency", "non_urgent")
        if urgency == "urgent" and pathway.pathway_type == PathwayType.EMERGENCY:
            relevance += 0.4
        elif urgency == "non_urgent" and pathway.pathway_type == PathwayType.PREVENTIVE:
            relevance += 0.3
        
        # Pertinence basée sur le niveau de preuve
        evidence_bonus = {"A": 0.2, "B": 0.1, "C": 0.05}
        relevance += evidence_bonus.get(pathway.evidence_level, 0)
        
        # Pertinence basée sur la complexité (préférer moins complexe)
        if pathway.complexity_score < 3.0:
            relevance += 0.1
        elif pathway.complexity_score > 7.0:
            relevance -= 0.1
        
        return min(relevance, 1.0)
    
    def generate_pathway_report(self, pathway_id: str) -> Dict[str, Any]:
        """Génère un rapport détaillé d'un parcours"""
        if pathway_id not in self.pathways:
            return {"error": "Parcours non trouvé"}
        
        pathway = self.pathways[pathway_id]
        validation = self.validations.get(pathway_id)
        
        # Calculer les statistiques des étapes
        step_stats = {
            "total_steps": len(pathway.steps),
            "avg_duration_hours": sum(step.duration_hours or 0 for step in pathway.steps) / len(pathway.steps) if pathway.steps else 0,
            "stages_distribution": {},
            "resource_requirements": set(),
            "quality_indicators_count": sum(len(step.quality_indicators) for step in pathway.steps)
        }
        
        # Distribution des étapes par stage
        for step in pathway.steps:
            stage = step.stage.value
            step_stats["stages_distribution"][stage] = step_stats["stages_distribution"].get(stage, 0) + 1
            step_stats["resource_requirements"].update(step.required_resources)
        
        step_stats["resource_requirements"] = list(step_stats["resource_requirements"])
        
        return {
            "pathway_info": {
                "id": pathway.id,
                "name": pathway.name,
                "condition": pathway.condition,
                "type": pathway.pathway_type.value,
                "specialty": pathway.specialty,
                "evidence_level": pathway.evidence_level,
                "complexity_score": pathway.complexity_score,
                "total_duration_days": pathway.total_duration_days,
                "cost_estimate": pathway.cost_estimate,
                "target_population": pathway.target_population
            },
            "validation": {
                "is_valid": validation.is_valid if validation else False,
                "completeness_score": validation.completeness_score if validation else 0,
                "evidence_quality": validation.evidence_quality if validation else "Non évaluée",
                "clinical_relevance": validation.clinical_relevance if validation else 0,
                "issues_count": len(validation.issues) if validation else 0,
                "recommendations_count": len(validation.recommendations) if validation else 0
            },
            "step_statistics": step_stats,
            "success_criteria": pathway.success_criteria,
            "quality_metrics": pathway.quality_metrics,
            "last_updated": pathway.last_updated.isoformat()
        }
    
    def generate_stats(self) -> OrganizationStats:
        """Génère les statistiques d'organisation"""
        import time
        start_time = time.time()
        
        stats = OrganizationStats()
        stats.total_pathways = len(self.pathways)
        
        if stats.total_pathways == 0:
            return stats
        
        # Statistiques par type
        for pathway_type, pathway_ids in self.pathways_by_type.items():
            stats.pathways_by_type[pathway_type.value] = len(pathway_ids)
        
        # Statistiques par spécialité
        for specialty, pathway_ids in self.pathways_by_specialty.items():
            stats.pathways_by_specialty[specialty] = len(pathway_ids)
        
        # Complexité moyenne
        total_complexity = sum(pathway.complexity_score for pathway in self.pathways.values())
        stats.avg_complexity = total_complexity / stats.total_pathways
        
        # Durée moyenne
        durations = [p.total_duration_days for p in self.pathways.values() if p.total_duration_days]
        if durations:
            stats.avg_duration = sum(durations) / len(durations)
        
        # Nombre total d'étapes
        stats.total_steps = sum(len(pathway.steps) for pathway in self.pathways.values())
        
        # Taux de validation
        validated_count = sum(1 for v in self.validations.values() if v.is_valid)
        stats.validation_rate = validated_count / stats.total_pathways if stats.total_pathways > 0 else 0
        
        stats.processing_time = time.time() - start_time
        
        self.stats = stats
        return stats
    
    def export_pathways(self, output_path: str):
        """Exporte tous les parcours"""
        export_data = {
            "metadata": {
                "total_pathways": len(self.pathways),
                "export_date": datetime.now().isoformat(),
                "version": "2.0.0",
                "organization": "Hôpital Général de Douala"
            },
            "pathways": {},
            "validations": {},
            "statistics": {
                "pathways_by_type": self.stats.pathways_by_type,
                "pathways_by_specialty": self.stats.pathways_by_specialty,
                "avg_complexity": self.stats.avg_complexity,
                "avg_duration": self.stats.avg_duration,
                "validation_rate": self.stats.validation_rate
            }
        }
        
        # Exporter les parcours
        for pathway_id, pathway in self.pathways.items():
            export_data["pathways"][pathway_id] = {
                "name": pathway.name,
                "type": pathway.pathway_type.value,
                "condition": pathway.condition,
                "description": pathway.description,
                "target_population": pathway.target_population,
                "specialty": pathway.specialty,
                "evidence_level": pathway.evidence_level,
                "complexity_score": pathway.complexity_score,
                "total_duration_days": pathway.total_duration_days,
                "cost_estimate": pathway.cost_estimate,
                "success_criteria": pathway.success_criteria,
                "quality_metrics": pathway.quality_metrics,
                "steps": [
                    {
                        "id": step.id,
                        "name": step.name,
                        "stage": step.stage.value,
                        "description": step.description,
                        "duration_hours": step.duration_hours,
                        "required_resources": step.required_resources,
                        "prerequisites": step.prerequisites,
                        "outcomes": step.outcomes,
                        "decision_points": step.decision_points,
                        "quality_indicators": step.quality_indicators,
                        "cost_estimate": step.cost_estimate,
                        "urgency_level": step.urgency_level.value,
                        "optional": step.optional
                    }
                    for step in pathway.steps
                ],
                "last_updated": pathway.last_updated.isoformat(),
                "version": pathway.version
            }
        
        # Exporter les validations
        for validation_id, validation in self.validations.items():
            export_data["validations"][validation_id] = {
                "is_valid": validation.is_valid,
                "completeness_score": validation.completeness_score,
                "evidence_quality": validation.evidence_quality,
                "clinical_relevance": validation.clinical_relevance,
                "issues": validation.issues,
                "recommendations": validation.recommendations,
                "validator": validation.validator,
                "validation_date": validation.validation_date.isoformat()
            }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Parcours exportés: {output_path}")

# Test de démonstration
async def main():
    """Fonction de test principale"""
    print("🛤️  Test de l'Organisateur de Parcours de Soins")
    
    # Créer l'organisateur
    organizer = PathwayOrganizer({
        "min_completeness_score": 0.7,
        "auto_validate_threshold": 0.9
    })
    
    # Afficher les parcours disponibles
    print(f"\n📋 Parcours disponibles: {len(organizer.pathways)}")
    for pathway in list(organizer.pathways.values()):
        print(f"  - {pathway.name} ({pathway.pathway_type.value})")
        print(f"    Condition: {pathway.condition}, Complexité: {pathway.complexity_score:.1f}")
    
    # Test de recherche
    print("\n🔍 Recherche de parcours pour le paludisme:")
    paludisme_pathways = organizer.search_pathways(condition="paludisme")
    for pathway in paludisme_pathways:
        print(f"  - {pathway.name} (Durée: {pathway.total_duration_days:.1f} jours)")
    
    # Test de recommandations
    print("\n💡 Recommandations pour un patient adulte avec paludisme:")
    patient_profile = {
        "age": 35,
        "sexe": "M",
        "urgency": "urgent",
        "comorbidities": []
    }
    
    recommendations = organizer.get_pathway_recommendations("paludisme", patient_profile)
    for pathway, score in recommendations:
        print(f"  - {pathway.name} (Score: {score:.2f})")
    
    # Test de rapport détaillé
    if organizer.pathways:
        first_pathway_id = list(organizer.pathways.keys())[0]
        print(f"\n📊 Rapport détaillé du premier parcours:")
        report = organizer.generate_pathway_report(first_pathway_id)
        
        print(f"  Nom: {report['pathway_info']['name']}")
        print(f"  Validité: {report['validation']['is_valid']}")
        print(f"  Score de complétude: {report['validation']['completeness_score']:.2f}")
        print(f"  Nombre d'étapes: {report['step_statistics']['total_steps']}")
        print(f"  Durée moyenne par étape: {report['step_statistics']['avg_duration_hours']:.1f}h")
    
    # Générer les statistiques
    stats = organizer.generate_stats()
    print(f"\n📈 Statistiques générales:")
    print(f"  Parcours totaux: {stats.total_pathways}")
    print(f"  Étapes totales: {stats.total_steps}")
    print(f"  Complexité moyenne: {stats.avg_complexity:.1f}")
    print(f"  Durée moyenne: {stats.avg_duration:.1f} jours")
    print(f"  Taux de validation: {stats.validation_rate:.1%}")
    
    print(f"\n📋 Répartition par type:")
    for pathway_type, count in stats.pathways_by_type.items():
        print(f"  {pathway_type}: {count} parcours")
    
    print(f"\n🏥 Répartition par spécialité:")
    for specialty, count in stats.pathways_by_specialty.items():
        print(f"  {specialty}: {count} parcours")
    
    # Exporter les parcours
    organizer.export_pathways("care_pathways_hgd.json")
    print("\n✅ Parcours exportés: care_pathways_hgd.json")

if __name__ == "__main__":
    asyncio.run(main())