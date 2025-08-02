#!/usr/bin/env python3
"""
Validateur médical pour vérifier l'exactitude et la qualité des contenus médicaux
Utilise des règles expertes et des bases de connaissances pour valider les informations
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
from collections import Counter, defaultdict

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Résultat de validation d'un document médical"""
    document_id: str
    is_valid: bool
    confidence_score: float
    
    # Scores détaillés
    medical_accuracy_score: float
    source_credibility_score: float
    content_quality_score: float
    completeness_score: float
    
    # Détails de validation
    validated_facts: List[Dict[str, Any]]
    flagged_issues: List[Dict[str, Any]]
    missing_information: List[str]
    contradictions: List[Dict[str, Any]]
    
    # Recommandations
    recommendations: List[str]
    required_corrections: List[str]
    
    # Métadonnées
    validation_date: datetime
    validator_version: str
    validation_rules_applied: List[str]

@dataclass
class MedicalFact:
    """Fait médical structuré"""
    fact_type: str  # 'symptom', 'treatment', 'diagnosis', 'medication', 'procedure'
    entity: str
    attribute: str
    value: str
    confidence: float
    source_sentence: str
    context: str

class MedicalValidator:
    """Validateur principal pour les contenus médicaux"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.validator_version = "1.0.0"
        
        # Seuils de validation
        self.min_confidence_threshold = config.get('min_confidence_threshold', 0.7)
        self.min_source_credibility = config.get('min_source_credibility', 0.6)
        
        # Charger les bases de connaissances
        self.medical_knowledge = self._load_medical_knowledge()
        self.drug_database = self._load_drug_database()
        self.disease_database = self._load_disease_database()
        self.trusted_sources = self._load_trusted_sources()
        
        # Règles de validation
        self.validation_rules = self._initialize_validation_rules()
        
        # Patterns de détection
        self.medical_patterns = self._initialize_medical_patterns()
        
        # Statistiques
        self.validation_stats = {
            'total_validated': 0,
            'valid_documents': 0,
            'invalid_documents': 0,
            'flagged_issues': Counter(),
            'validation_scores': [],
            'source_distribution': Counter()
        }
    
    def _load_medical_knowledge(self) -> Dict[str, Any]:
        """Charge la base de connaissances médicales"""
        return {
            # Symptômes par maladie
            'disease_symptoms': {
                'hypertension': {
                    'common': ['maux de tête', 'fatigue', 'essoufflement'],
                    'rare': ['saignements de nez', 'troubles visuels'],
                    'emergency': ['douleur thoracique', 'confusion', 'convulsions']
                },
                'diabète': {
                    'common': ['soif excessive', 'urination fréquente', 'fatigue'],
                    'rare': ['vision floue', 'cicatrisation lente'],
                    'emergency': ['coma', 'respiration rapide', 'vomissements']
                },
                'paludisme': {
                    'common': ['fièvre', 'frissons', 'maux de tête', 'fatigue'],
                    'rare': ['jaunisse', 'convulsions'],
                    'emergency': ['coma', 'détresse respiratoire', 'choc']
                },
                'tuberculose': {
                    'common': ['toux persistante', 'fièvre', 'sueurs nocturnes', 'perte de poids'],
                    'rare': ['crachats sanglants', 'douleur thoracique'],
                    'emergency': ['détresse respiratoire', 'hémoptysie massive']
                }
            },
            
            # Traitements standards
            'standard_treatments': {
                'hypertension': {
                    'first_line': ['IEC', 'ARA2', 'diurétiques thiazidiques', 'inhibiteurs calciques'],
                    'lifestyle': ['régime pauvre en sel', 'exercice physique', 'arrêt tabac']
                },
                'diabète': {
                    'type1': ['insuline'],
                    'type2': ['metformine', 'sulfamides', 'inhibiteurs DPP4'],
                    'lifestyle': ['régime diabétique', 'exercice physique', 'surveillance glycémique']
                },
                'paludisme': {
                    'simple': ['artéméther-luméfantrine', 'artésunate-amodiaquine'],
                    'severe': ['artésunate IV', 'quinine IV'],
                    'prevention': ['moustiquaires imprégnées', 'répulsifs']
                }
            },
            
            # Valeurs normales
            'normal_values': {
                'tension_arterielle': {
                    'normale': '<120/80 mmHg',
                    'elevee': '120-129/<80 mmHg',
                    'hypertension_grade1': '130-139/80-89 mmHg',
                    'hypertension_grade2': '≥140/90 mmHg'
                },
                'glycemie': {
                    'normale_jeun': '0.7-1.0 g/L',
                    'intolerance_glucose': '1.0-1.26 g/L',
                    'diabete': '≥1.26 g/L'
                }
            },
            
            # Contre-indications importantes
            'contraindications': {
                'aspirine': ['allergie aspirine', 'ulcère gastrique actif', 'grossesse 3e trimestre'],
                'metformine': ['insuffisance rénale sévère', 'acidose métabolique'],
                'IEC': ['grossesse', 'hyperkaliémie', 'sténose artère rénale bilatérale']
            }
        }
    
    def _load_drug_database(self) -> Dict[str, Any]:
        """Charge la base de données des médicaments"""
        return {
            'approved_drugs': {
                # Antihypertenseurs
                'enalapril': {
                    'class': 'IEC',
                    'indications': ['hypertension', 'insuffisance cardiaque'],
                    'dosage': '5-40 mg/jour',
                    'contraindications': ['grossesse', 'hyperkaliémie']
                },
                'amlodipine': {
                    'class': 'inhibiteur calcique',
                    'indications': ['hypertension', 'angor'],
                    'dosage': '5-10 mg/jour',
                    'contraindications': ['choc cardiogénique']
                },
                
                # Antidiabétiques
                'metformine': {
                    'class': 'biguanide',
                    'indications': ['diabète type 2'],
                    'dosage': '500-2000 mg/jour',
                    'contraindications': ['insuffisance rénale', 'acidose']
                },
                
                # Antipaludiques
                'artemether_lumefantrine': {
                    'class': 'antipaludique',
                    'indications': ['paludisme simple'],
                    'dosage': 'selon poids corporel',
                    'contraindications': ['allergie artémisinine']
                }
            },
            
            'drug_interactions': {
                'warfarine': ['aspirine', 'amiodarone', 'fluconazole'],
                'digoxine': ['amiodarone', 'vérapamil', 'quinidine'],
                'metformine': ['produits de contraste iodés', 'alcool']
            }
        }
    
    def _load_disease_database(self) -> Dict[str, Any]:
        """Charge la base de données des maladies"""
        return {
            'diseases': {
                'hypertension_arterielle': {
                    'icd10': 'I10-I15',
                    'prevalence_cameroon': '30%',
                    'risk_factors': ['âge', 'obésité', 'sel', 'sédentarité', 'stress'],
                    'complications': ['AVC', 'infarctus', 'insuffisance rénale', 'rétinopathie']
                },
                'diabete_type2': {
                    'icd10': 'E11',
                    'prevalence_cameroon': '6%',
                    'risk_factors': ['obésité', 'sédentarité', 'hérédité', 'âge'],
                    'complications': ['rétinopathie', 'néphropathie', 'neuropathie', 'macroangiopathie']
                },
                'paludisme': {
                    'icd10': 'B50-B54',
                    'prevalence_cameroon': 'endémique',
                    'agent': 'Plasmodium falciparum (90%)',
                    'transmission': 'Anopheles gambiae'
                }
            }
        }
    
    def _load_trusted_sources(self) -> Dict[str, float]:
        """Charge la liste des sources fiables avec leurs scores de crédibilité"""
        return {
            # Sources internationales
            'who.int': 0.95,
            'cdc.gov': 0.90,
            'nih.gov': 0.90,
            'pubmed.ncbi.nlm.nih.gov': 0.85,
            'cochrane.org': 0.90,
            
            # Sources françaises
            'has-sante.fr': 0.85,
            'ameli.fr': 0.80,
            'vidal.fr': 0.80,
            'ansm.sante.fr': 0.85,
            
            # Sources africaines
            'minsante.cm': 0.75,
            'pasteur-yaounde.org': 0.80,
            'afro.who.int': 0.85,
            
            # Journaux médicaux
            'nejm.org': 0.90,
            'thelancet.com': 0.90,
            'bmj.com': 0.85,
            
            # Sources moins fiables
            'wikipedia.org': 0.60,
            'doctissimo.fr': 0.50,
            'passeportsante.net': 0.55
        }
    
    def _initialize_validation_rules(self) -> List[Dict[str, Any]]:
        """Initialise les règles de validation"""
        return [
            {
                'name': 'dosage_validation',
                'description': 'Vérifier la cohérence des dosages médicamenteux',
                'pattern': r'(\d+(?:\.\d+)?)\s*(mg|g|ml|l|UI)(?:/(?:jour|day|kg))?',
                'validator': self._validate_dosage
            },
            {
                'name': 'contraindication_check',
                'description': 'Vérifier les contre-indications mentionnées',
                'pattern': r'contre[- ]?indication|ne pas utiliser|éviter',
                'validator': self._validate_contraindications
            },
            {
                'name': 'symptom_disease_consistency',
                'description': 'Vérifier la cohérence symptômes-maladie',
                'pattern': r'symptômes?|signes?|manifestations?',
                'validator': self._validate_symptom_consistency
            },
            {
                'name': 'treatment_appropriateness',
                'description': 'Vérifier l\'appropriété des traitements',
                'pattern': r'traitement|thérapie|médicament',
                'validator': self._validate_treatment_appropriateness
            },
            {
                'name': 'emergency_signs',
                'description': 'Vérifier les signes d\'urgence',
                'pattern': r'urgence|emergency|grave|sévère',
                'validator': self._validate_emergency_signs
            }
        ]
    
    def _initialize_medical_patterns(self) -> Dict[str, str]:
        """Initialise les patterns de détection médicale"""
        return {
            'medication': r'\b(?:mg|g|ml|l|UI|comprimés?|gélules?)\b',
            'dosage': r'\b\d+(?:\.\d+)?\s*(?:mg|g|ml|l|UI)(?:/(?:jour|day|kg))?\b',
            'vital_signs': r'\b(?:TA|tension|pression)\s*:?\s*\d+/\d+|\b(?:FC|fréquence cardiaque)\s*:?\s*\d+',
            'lab_values': r'\b(?:glycémie|créatinine|urée|cholestérol)\s*:?\s*\d+(?:\.\d+)?',
            'symptoms': r'\b(?:douleur|fièvre|fatigue|nausée|vomissement|toux|essoufflement)\b',
            'procedures': r'\b(?:chirurgie|opération|intervention|examen|analyse|radiographie|échographie)\b'
        }
    
    def validate_document(self, document: Dict[str, Any]) -> ValidationResult:
        """Valide un document médical complet"""
        try:
            self.validation_stats['total_validated'] += 1
            
            doc_id = document.get('file_hash', f"doc_{self.validation_stats['total_validated']}")
            content = document.get('cleaned_content', document.get('content', ''))
            source_url = document.get('original_url', '')
            
            logger.info(f"🔍 Validation du document: {document.get('title', 'Sans titre')[:50]}...")
            
            # 1. Validation de la crédibilité de la source
            source_credibility_score = self._validate_source_credibility(source_url)
            
            # 2. Extraction des faits médicaux
            medical_facts = self._extract_medical_facts(content)
            
            # 3. Validation des faits médicaux
            validated_facts, flagged_issues = self._validate_medical_facts(medical_facts)
            
            # 4. Vérification de la complétude
            completeness_score, missing_info = self._check_completeness(document, medical_facts)
            
            # 5. Détection des contradictions
            contradictions = self._detect_contradictions(medical_facts)
            
            # 6. Calcul des scores
            medical_accuracy_score = self._calculate_medical_accuracy(validated_facts, flagged_issues)
            content_quality_score = self._calculate_content_quality(content, medical_facts)
            
            # 7. Score de confiance global
            confidence_score = self._calculate_confidence_score(
                medical_accuracy_score,
                source_credibility_score,
                content_quality_score,
                completeness_score
            )
            
            # 8. Détermination de la validité
            is_valid = (
                confidence_score >= self.min_confidence_threshold and
                source_credibility_score >= self.min_source_credibility and
                len([issue for issue in flagged_issues if issue['severity'] == 'critical']) == 0
            )
            
            # 9. Génération des recommandations
            recommendations = self._generate_recommendations(flagged_issues, missing_info, contradictions)
            required_corrections = self._identify_required_corrections(flagged_issues)
            
            # 10. Création du résultat
            result = ValidationResult(
                document_id=doc_id,
                is_valid=is_valid,
                confidence_score=confidence_score,
                medical_accuracy_score=medical_accuracy_score,
                source_credibility_score=source_credibility_score,
                content_quality_score=content_quality_score,
                completeness_score=completeness_score,
                validated_facts=[asdict(fact) for fact in validated_facts],
                flagged_issues=flagged_issues,
                missing_information=missing_info,
                contradictions=contradictions,
                recommendations=recommendations,
                required_corrections=required_corrections,
                validation_date=datetime.now(),
                validator_version=self.validator_version,
                validation_rules_applied=[rule['name'] for rule in self.validation_rules]
            )
            
            # Mise à jour des statistiques
            if is_valid:
                self.validation_stats['valid_documents'] += 1
            else:
                self.validation_stats['invalid_documents'] += 1
            
            self.validation_stats['validation_scores'].append(confidence_score)
            self.validation_stats['source_distribution'][self._extract_domain(source_url)] += 1
            
            for issue in flagged_issues:
                self.validation_stats['flagged_issues'][issue['type']] += 1
            
            logger.info(f"✅ Validation terminée - Score: {confidence_score:.2f} - Valide: {is_valid}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la validation: {e}")
            return self._create_error_result(doc_id, str(e))
    
    def _validate_source_credibility(self, source_url: str) -> float:
        """Valide la crédibilité de la source"""
        if not source_url:
            return 0.3  # Score faible pour source inconnue
        
        domain = self._extract_domain(source_url)
        
        # Vérifier dans la liste des sources fiables
        for trusted_domain, score in self.trusted_sources.items():
            if trusted_domain in domain:
                return score
        
        # Heuristiques pour sources non répertoriées
        if any(indicator in domain for indicator in ['.gov', '.edu', '.org']):
            return 0.70
        elif any(indicator in domain for indicator in ['hospital', 'clinic', 'medical']):
            return 0.65
        elif '.com' in domain:
            return 0.40
        else:
            return 0.30
    
    def _extract_domain(self, url: str) -> str:
        """Extrait le domaine d'une URL"""
        if not url:
            return ''
        
        # Supprimer le protocole
        domain = re.sub(r'^https?://', '', url)
        # Prendre seulement le domaine
        domain = domain.split('/')[0]
        # Supprimer www.
        domain = re.sub(r'^www\.', '', domain)
        
        return domain.lower()
    
    def _extract_medical_facts(self, content: str) -> List[MedicalFact]:
        """Extrait les faits médicaux du contenu"""
        facts = []
        sentences = self._split_into_sentences(content)
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            # Extraire les médicaments et dosages
            medication_facts = self._extract_medication_facts(sentence)
            facts.extend(medication_facts)
            
            # Extraire les symptômes
            symptom_facts = self._extract_symptom_facts(sentence)
            facts.extend(symptom_facts)
            
            # Extraire les traitements
            treatment_facts = self._extract_treatment_facts(sentence)
            facts.extend(treatment_facts)
            
            # Extraire les valeurs biologiques
            lab_facts = self._extract_lab_value_facts(sentence)
            facts.extend(lab_facts)
        
        return facts
    
    def _extract_medication_facts(self, sentence: str) -> List[MedicalFact]:
        """Extrait les faits sur les médicaments"""
        facts = []
        
        # Pattern pour médicament + dosage
        med_pattern = r'(\w+)\s+(\d+(?:\.\d+)?)\s*(mg|g|ml|l|UI)(?:/(?:jour|day|kg))?'
        matches = re.finditer(med_pattern, sentence, re.IGNORECASE)
        
        for match in matches:
            medication = match.group(1)
            dosage = f"{match.group(2)} {match.group(3)}"
            
            fact = MedicalFact(
                fact_type='medication',
                entity=medication,
                attribute='dosage',
                value=dosage,
                confidence=0.8,
                source_sentence=sentence,
                context='dosage_information'
            )
            facts.append(fact)
        
        return facts
    
    def _extract_symptom_facts(self, sentence: str) -> List[MedicalFact]:
        """Extrait les faits sur les symptômes"""
        facts = []
        
        # Symptômes courants
        symptoms = [
            'fièvre', 'douleur', 'fatigue', 'nausée', 'vomissement',
            'toux', 'essoufflement', 'maux de tête', 'vertiges'
        ]
        
        sentence_lower = sentence.lower()
        
        for symptom in symptoms:
            if symptom in sentence_lower:
                # Chercher le contexte (maladie associée)
                context = self._find_disease_context(sentence)
                
                fact = MedicalFact(
                    fact_type='symptom',
                    entity=symptom,
                    attribute='presence',
                    value='present',
                    confidence=0.7,
                    source_sentence=sentence,
                    context=context or 'general'
                )
                facts.append(fact)
        
        return facts
    
    def _extract_treatment_facts(self, sentence: str) -> List[MedicalFact]:
        """Extrait les faits sur les traitements"""
        facts = []
        
        # Patterns de traitement
        treatment_patterns = [
            r'traitement\s+(?:de\s+)?(?:première\s+)?ligne\s*:?\s*([^.]+)',
            r'thérapie\s+recommandée\s*:?\s*([^.]+)',
            r'administrer\s+([^.]+)'
        ]
        
        for pattern in treatment_patterns:
            matches = re.finditer(pattern, sentence, re.IGNORECASE)
            for match in matches:
                treatment = match.group(1).strip()
                
                fact = MedicalFact(
                    fact_type='treatment',
                    entity=treatment,
                    attribute='recommendation',
                    value='recommended',
                    confidence=0.8,
                    source_sentence=sentence,
                    context='treatment_guideline'
                )
                facts.append(fact)
        
        return facts
    
    def _extract_lab_value_facts(self, sentence: str) -> List[MedicalFact]:
        """Extrait les valeurs biologiques"""
        facts = []
        
        # Pattern pour valeurs biologiques
        lab_pattern = r'(glycémie|créatinine|urée|cholestérol|TA|tension)\s*:?\s*(\d+(?:\.\d+)?(?:/\d+)?)'  
        matches = re.finditer(lab_pattern, sentence, re.IGNORECASE)
        
        for match in matches:
            parameter = match.group(1)
            value = match.group(2)
            
            fact = MedicalFact(
                fact_type='lab_value',
                entity=parameter,
                attribute='measurement',
                value=value,
                confidence=0.9,
                source_sentence=sentence,
                context='laboratory_result'
            )
            facts.append(fact)
        
        return facts
    
    def _find_disease_context(self, sentence: str) -> Optional[str]:
        """Trouve le contexte de maladie dans une phrase"""
        diseases = ['hypertension', 'diabète', 'paludisme', 'tuberculose', 'asthme']
        
        sentence_lower = sentence.lower()
        for disease in diseases:
            if disease in sentence_lower:
                return disease
        
        return None
    
    def _validate_medical_facts(self, facts: List[MedicalFact]) -> Tuple[List[MedicalFact], List[Dict[str, Any]]]:
        """Valide les faits médicaux extraits"""
        validated_facts = []
        flagged_issues = []
        
        for fact in facts:
            validation_result = self._validate_single_fact(fact)
            
            if validation_result['is_valid']:
                validated_facts.append(fact)
            else:
                flagged_issues.append({
                    'type': 'invalid_medical_fact',
                    'severity': validation_result['severity'],
                    'description': validation_result['description'],
                    'fact': asdict(fact),
                    'suggestion': validation_result.get('suggestion', '')
                })
        
        return validated_facts, flagged_issues
    
    def _validate_single_fact(self, fact: MedicalFact) -> Dict[str, Any]:
        """Valide un fait médical individuel"""
        if fact.fact_type == 'medication':
            return self._validate_medication_fact(fact)
        elif fact.fact_type == 'symptom':
            return self._validate_symptom_fact(fact)
        elif fact.fact_type == 'treatment':
            return self._validate_treatment_fact(fact)
        elif fact.fact_type == 'lab_value':
            return self._validate_lab_value_fact(fact)
        else:
            return {'is_valid': True, 'severity': 'info'}
    
    def _validate_medication_fact(self, fact: MedicalFact) -> Dict[str, Any]:
        """Valide un fait sur un médicament"""
        medication = fact.entity.lower()
        
        # Vérifier si le médicament est dans la base
        if medication in self.drug_database['approved_drugs']:
            drug_info = self.drug_database['approved_drugs'][medication]
            
            # Vérifier le dosage
            if fact.attribute == 'dosage':
                dosage_valid = self._validate_dosage_range(fact.value, drug_info.get('dosage', ''))
                if not dosage_valid:
                    return {
                        'is_valid': False,
                        'severity': 'warning',
                        'description': f"Dosage inhabituel pour {medication}: {fact.value}",
                        'suggestion': f"Dosage recommandé: {drug_info.get('dosage', 'Non spécifié')}"
                    }
        
        return {'is_valid': True, 'severity': 'info'}
    
    def _validate_symptom_fact(self, fact: MedicalFact) -> Dict[str, Any]:
        """Valide un fait sur un symptôme"""
        symptom = fact.entity.lower()
        context = fact.context
        
        # Vérifier la cohérence symptôme-maladie
        if context in self.medical_knowledge['disease_symptoms']:
            disease_symptoms = self.medical_knowledge['disease_symptoms'][context]
            all_symptoms = disease_symptoms.get('common', []) + disease_symptoms.get('rare', []) + disease_symptoms.get('emergency', [])
            
            if symptom not in [s.lower() for s in all_symptoms]:
                return {
                    'is_valid': False,
                    'severity': 'warning',
                    'description': f"Symptôme '{symptom}' inhabituel pour {context}",
                    'suggestion': f"Symptômes typiques: {', '.join(disease_symptoms.get('common', []))}"
                }
        
        return {'is_valid': True, 'severity': 'info'}
    
    def _validate_treatment_fact(self, fact: MedicalFact) -> Dict[str, Any]:
        """Valide un fait sur un traitement"""
        treatment = fact.entity.lower()
        
        # Vérifier si le traitement est approprié
        # (Logique simplifiée - pourrait être étendue)
        
        return {'is_valid': True, 'severity': 'info'}
    
    def _validate_lab_value_fact(self, fact: MedicalFact) -> Dict[str, Any]:
        """Valide une valeur biologique"""
        parameter = fact.entity.lower()
        value = fact.value
        
        # Vérifier les valeurs normales
        if parameter in ['glycémie', 'glycemia']:
            try:
                numeric_value = float(re.search(r'\d+(?:\.\d+)?', value).group())
                if numeric_value > 5.0:  # Valeur très élevée
                    return {
                        'is_valid': False,
                        'severity': 'warning',
                        'description': f"Glycémie très élevée: {value}",
                        'suggestion': "Vérifier l'unité et la valeur"
                    }
            except:
                pass
        
        return {'is_valid': True, 'severity': 'info'}
    
    def _check_completeness(self, document: Dict[str, Any], facts: List[MedicalFact]) -> Tuple[float, List[str]]:
        """Vérifie la complétude du document"""
        missing_info = []
        
        # Éléments essentiels selon le type de document
        doc_type = document.get('document_type', 'unknown')
        category = document.get('category', 'general')
        
        if doc_type == 'guideline':
            required_elements = ['diagnostic', 'traitement', 'symptômes']
        elif doc_type == 'fact_sheet':
            required_elements = ['définition', 'symptômes', 'prévention']
        else:
            required_elements = ['symptômes', 'traitement']
        
        content_lower = document.get('cleaned_content', '').lower()
        
        for element in required_elements:
            if element not in content_lower:
                missing_info.append(f"Information manquante: {element}")
        
        # Calculer le score de complétude
        completeness_score = 1.0 - (len(missing_info) / len(required_elements))
        
        return max(completeness_score, 0.0), missing_info
    
    def _detect_contradictions(self, facts: List[MedicalFact]) -> List[Dict[str, Any]]:
        """Détecte les contradictions dans les faits"""
        contradictions = []
        
        # Grouper les faits par entité
        facts_by_entity = defaultdict(list)
        for fact in facts:
            facts_by_entity[fact.entity].append(fact)
        
        # Chercher des contradictions
        for entity, entity_facts in facts_by_entity.items():
            if len(entity_facts) > 1:
                # Vérifier les valeurs contradictoires
                values = [fact.value for fact in entity_facts if fact.attribute == 'dosage']
                if len(set(values)) > 1:
                    contradictions.append({
                        'type': 'dosage_contradiction',
                        'entity': entity,
                        'conflicting_values': values,
                        'description': f"Dosages contradictoires pour {entity}: {', '.join(values)}"
                    })
        
        return contradictions
    
    def _calculate_medical_accuracy(self, validated_facts: List[MedicalFact], flagged_issues: List[Dict[str, Any]]) -> float:
        """Calcule le score d'exactitude médicale"""
        total_facts = len(validated_facts) + len(flagged_issues)
        
        if total_facts == 0:
            return 0.5  # Score neutre si pas de faits médicaux
        
        # Pondérer selon la sévérité des problèmes
        penalty = 0
        for issue in flagged_issues:
            if issue['severity'] == 'critical':
                penalty += 0.3
            elif issue['severity'] == 'warning':
                penalty += 0.1
            else:
                penalty += 0.05
        
        accuracy = len(validated_facts) / total_facts - penalty
        return max(accuracy, 0.0)
    
    def _calculate_content_quality(self, content: str, facts: List[MedicalFact]) -> float:
        """Calcule le score de qualité du contenu"""
        score = 0.0
        
        # Longueur appropriée
        length = len(content)
        if 1000 <= length <= 5000:
            score += 0.3
        elif 500 <= length < 1000 or 5000 < length <= 10000:
            score += 0.2
        
        # Densité de faits médicaux
        fact_density = len(facts) / (length / 1000)  # faits par 1000 caractères
        if fact_density > 2:
            score += 0.3
        elif fact_density > 1:
            score += 0.2
        
        # Structure (présence de sections)
        if re.search(r'\n\s*[A-Z][^\n]{10,50}\s*\n', content):
            score += 0.2
        
        # Références ou sources
        if re.search(r'(source|référence|study|étude)', content, re.IGNORECASE):
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_confidence_score(self, medical_accuracy: float, source_credibility: float, 
                                  content_quality: float, completeness: float) -> float:
        """Calcule le score de confiance global"""
        # Pondération des différents scores
        weights = {
            'medical_accuracy': 0.4,
            'source_credibility': 0.3,
            'content_quality': 0.2,
            'completeness': 0.1
        }
        
        confidence = (
            medical_accuracy * weights['medical_accuracy'] +
            source_credibility * weights['source_credibility'] +
            content_quality * weights['content_quality'] +
            completeness * weights['completeness']
        )
        
        return min(confidence, 1.0)
    
    def _generate_recommendations(self, flagged_issues: List[Dict[str, Any]], 
                                missing_info: List[str], contradictions: List[Dict[str, Any]]) -> List[str]:
        """Génère des recommandations d'amélioration"""
        recommendations = []
        
        # Recommandations basées sur les problèmes détectés
        critical_issues = [issue for issue in flagged_issues if issue['severity'] == 'critical']
        if critical_issues:
            recommendations.append("Corriger les erreurs critiques avant publication")
        
        warning_issues = [issue for issue in flagged_issues if issue['severity'] == 'warning']
        if warning_issues:
            recommendations.append("Vérifier et corriger les avertissements")
        
        # Recommandations pour informations manquantes
        if missing_info:
            recommendations.append(f"Ajouter les informations manquantes: {', '.join(missing_info[:3])}")
        
        # Recommandations pour contradictions
        if contradictions:
            recommendations.append("Résoudre les contradictions identifiées")
        
        # Recommandations générales
        if len(flagged_issues) == 0:
            recommendations.append("Document de bonne qualité - révision mineure recommandée")
        
        return recommendations
    
    def _identify_required_corrections(self, flagged_issues: List[Dict[str, Any]]) -> List[str]:
        """Identifie les corrections obligatoires"""
        corrections = []
        
        for issue in flagged_issues:
            if issue['severity'] == 'critical':
                corrections.append(f"CRITIQUE: {issue['description']}")
            elif issue['severity'] == 'warning' and 'dosage' in issue['type']:
                corrections.append(f"DOSAGE: {issue['description']}")
        
        return corrections
    
    def _create_error_result(self, doc_id: str, error_message: str) -> ValidationResult:
        """Crée un résultat d'erreur"""
        return ValidationResult(
            document_id=doc_id,
            is_valid=False,
            confidence_score=0.0,
            medical_accuracy_score=0.0,
            source_credibility_score=0.0,
            content_quality_score=0.0,
            completeness_score=0.0,
            validated_facts=[],
            flagged_issues=[{
                'type': 'validation_error',
                'severity': 'critical',
                'description': f"Erreur de validation: {error_message}"
            }],
            missing_information=[],
            contradictions=[],
            recommendations=["Corriger l'erreur de validation"],
            required_corrections=[f"ERREUR: {error_message}"],
            validation_date=datetime.now(),
            validator_version=self.validator_version,
            validation_rules_applied=[]
        )
    
    def _split_into_sentences(self, content: str) -> List[str]:
        """Divise le contenu en phrases"""
        sentences = re.split(r'[.!?]+\s+', content)
        return [s.strip() for s in sentences if len(s.strip()) > 10]
    
    def _validate_dosage(self, content: str) -> List[Dict[str, Any]]:
        """Règle de validation des dosages"""
        issues = []
        # Implémentation de la validation des dosages
        return issues
    
    def _validate_contraindications(self, content: str) -> List[Dict[str, Any]]:
        """Règle de validation des contre-indications"""
        issues = []
        # Implémentation de la validation des contre-indications
        return issues
    
    def _validate_symptom_consistency(self, content: str) -> List[Dict[str, Any]]:
        """Règle de validation de la cohérence des symptômes"""
        issues = []
        # Implémentation de la validation de cohérence
        return issues
    
    def _validate_treatment_appropriateness(self, content: str) -> List[Dict[str, Any]]:
        """Règle de validation de l'appropriété des traitements"""
        issues = []
        # Implémentation de la validation des traitements
        return issues
    
    def _validate_emergency_signs(self, content: str) -> List[Dict[str, Any]]:
        """Règle de validation des signes d'urgence"""
        issues = []
        # Implémentation de la validation des urgences
        return issues
    
    def _validate_dosage_range(self, given_dosage: str, standard_dosage: str) -> bool:
        """Valide si un dosage est dans la plage acceptable"""
        # Implémentation simplifiée
        return True
    
    def validate_batch(self, documents: List[Dict[str, Any]]) -> List[ValidationResult]:
        """Valide un lot de documents"""
        logger.info(f"🔍 Validation de {len(documents)} documents...")
        
        results = []
        for i, doc in enumerate(documents):
            logger.info(f"📋 Validation {i+1}/{len(documents)}: {doc.get('title', 'Sans titre')[:50]}...")
            result = self.validate_document(doc)
            results.append(result)
        
        logger.info(f"✅ Validation terminée: {len([r for r in results if r.is_valid])}/{len(results)} documents valides")
        
        return results
    
    def save_validation_results(self, results: List[ValidationResult], output_path: Path) -> bool:
        """Sauvegarde les résultats de validation"""
        try:
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Sauvegarder chaque résultat
            for result in results:
                filename = f"validation_{result.document_id}.json"
                filepath = output_path / filename
                
                # Convertir en dictionnaire
                result_dict = asdict(result)
                result_dict['validation_date'] = result.validation_date.isoformat()
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(result_dict, f, ensure_ascii=False, indent=2)
            
            # Sauvegarder le rapport de synthèse
            summary = self._generate_validation_summary(results)
            summary_path = output_path / "validation_summary.json"
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 Résultats de validation sauvegardés dans {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde: {e}")
            return False
    
    def _generate_validation_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """Génère un résumé des validations"""
        valid_count = len([r for r in results if r.is_valid])
        
        return {
            'total_documents': len(results),
            'valid_documents': valid_count,
            'invalid_documents': len(results) - valid_count,
            'validation_rate': valid_count / len(results) * 100 if results else 0,
            'average_confidence': sum(r.confidence_score for r in results) / len(results) if results else 0,
            'average_medical_accuracy': sum(r.medical_accuracy_score for r in results) / len(results) if results else 0,
            'average_source_credibility': sum(r.source_credibility_score for r in results) / len(results) if results else 0,
            'common_issues': dict(self.validation_stats['flagged_issues'].most_common(10)),
            'validation_statistics': self.validation_stats,
            'generated_at': datetime.now().isoformat()
        }
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques de validation"""
        return self.validation_stats.copy()

def main():
    """Fonction principale pour tester le validateur"""
    # Configuration de test
    config = {
        'min_confidence_threshold': 0.7,
        'min_source_credibility': 0.6
    }
    
    validator = MedicalValidator(config)
    
    # Document de test
    test_document = {
        'title': 'Traitement de l\'hypertension artérielle',
        'cleaned_content': '''
        L'hypertension artérielle se définit par une pression artérielle ≥ 140/90 mmHg.
        
        Symptômes: maux de tête, fatigue, essoufflement.
        
        Traitement de première ligne: enalapril 10 mg/jour ou amlodipine 5 mg/jour.
        
        Contre-indications: grossesse pour les IEC, choc cardiogénique pour l'amlodipine.
        
        Surveillance: glycémie, créatinine, ionogramme.
        ''',
        'original_url': 'https://who.int/hypertension-guidelines',
        'source': 'WHO',
        'category': 'maladies_chroniques',
        'document_type': 'guideline',
        'file_hash': 'test123'
    }
    
    logger.info("🧪 Test du validateur médical...")
    
    result = validator.validate_document(test_document)
    
    logger.info(f"✅ Validation terminée")
    logger.info(f"📊 Document valide: {result.is_valid}")
    logger.info(f"🎯 Score de confiance: {result.confidence_score:.2f}")
    logger.info(f"🏥 Exactitude médicale: {result.medical_accuracy_score:.2f}")
    logger.info(f"🔗 Crédibilité source: {result.source_credibility_score:.2f}")
    logger.info(f"📋 Faits validés: {len(result.validated_facts)}")
    logger.info(f"⚠️ Problèmes détectés: {len(result.flagged_issues)}")
    
    if result.recommendations:
        logger.info(f"💡 Recommandations: {result.recommendations[:3]}")
    
    # Sauvegarder le test
    output_path = Path("../data/validation/test")
    validator.save_validation_results([result], output_path)
    
    # Afficher les statistiques
    stats = validator.get_validation_statistics()
    logger.info(f"📈 Statistiques: {stats}")

if __name__ == "__main__":
    main()