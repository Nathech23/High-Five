#!/usr/bin/env python3
"""
Organisateur hiérarchique des connaissances médicales
Structure les documents par thèmes, catégories et niveaux de complexité
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
from collections import defaultdict, Counter
import hashlib

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class KnowledgeNode:
    """Nœud dans la hiérarchie des connaissances"""
    node_id: str
    name: str
    description: str
    level: int  # 0=racine, 1=catégorie principale, 2=sous-catégorie, etc.
    parent_id: Optional[str]
    children_ids: List[str]
    
    # Contenu associé
    document_ids: List[str]
    keywords: List[str]
    medical_terms: List[str]
    
    # Métadonnées
    complexity_level: str  # 'simple', 'intermediate', 'advanced'
    target_audience: str  # 'general_public', 'patients', 'healthcare_professionals'
    priority: int  # 1=critique, 2=important, 3=utile
    
    # Statistiques
    document_count: int
    total_content_length: int
    average_quality_score: float
    
    # Dates
    created_date: datetime
    last_updated: datetime

@dataclass
class KnowledgeHierarchy:
    """Structure hiérarchique complète des connaissances"""
    hierarchy_id: str
    name: str
    description: str
    version: str
    
    # Structure
    nodes: Dict[str, KnowledgeNode]
    root_nodes: List[str]
    
    # Index
    documents_index: Dict[str, str]  # document_id -> node_id
    keywords_index: Dict[str, List[str]]  # keyword -> [node_ids]
    medical_terms_index: Dict[str, List[str]]  # term -> [node_ids]
    
    # Métadonnées
    total_documents: int
    total_nodes: int
    max_depth: int
    
    # Dates
    created_date: datetime
    last_updated: datetime

class KnowledgeOrganizer:
    """Organisateur principal des connaissances médicales"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.organizer_version = "1.0.0"
        
        # Configuration de l'organisation
        self.max_depth = config.get('max_hierarchy_depth', 4)
        self.min_documents_per_node = config.get('min_documents_per_node', 3)
        self.max_documents_per_node = config.get('max_documents_per_node', 50)
        
        # Taxonomie médicale de base
        self.medical_taxonomy = self._initialize_medical_taxonomy()
        
        # Règles de classification
        self.classification_rules = self._initialize_classification_rules()
        
        # Hiérarchie actuelle
        self.current_hierarchy: Optional[KnowledgeHierarchy] = None
        
        # Statistiques
        self.organization_stats = {
            'total_organized': 0,
            'nodes_created': 0,
            'documents_classified': 0,
            'hierarchy_depth': 0,
            'classification_accuracy': 0.0
        }
    
    def _initialize_medical_taxonomy(self) -> Dict[str, Any]:
        """Initialise la taxonomie médicale de base"""
        return {
            'maladies': {
                'description': 'Pathologies et conditions médicales',
                'priority': 1,
                'subcategories': {
                    'maladies_infectieuses': {
                        'description': 'Infections virales, bactériennes, parasitaires',
                        'keywords': ['infection', 'virus', 'bactérie', 'parasite', 'contagieux'],
                        'diseases': ['paludisme', 'tuberculose', 'hépatite', 'pneumonie', 'méningite'],
                        'priority': 1
                    },
                    'maladies_chroniques': {
                        'description': 'Pathologies de longue durée',
                        'keywords': ['chronique', 'permanent', 'long terme', 'gestion'],
                        'diseases': ['hypertension', 'diabète', 'asthme', 'arthrite', 'insuffisance'],
                        'priority': 1
                    },
                    'maladies_cardiovasculaires': {
                        'description': 'Pathologies du cœur et des vaisseaux',
                        'keywords': ['cœur', 'cardiaque', 'vasculaire', 'circulation', 'tension'],
                        'diseases': ['infarctus', 'angine', 'arythmie', 'insuffisance cardiaque'],
                        'priority': 1
                    },
                    'cancers': {
                        'description': 'Tumeurs malignes et bénignes',
                        'keywords': ['cancer', 'tumeur', 'oncologie', 'métastase', 'chimiothérapie'],
                        'diseases': ['cancer du sein', 'cancer du poumon', 'leucémie'],
                        'priority': 1
                    },
                    'maladies_mentales': {
                        'description': 'Troubles psychiatriques et psychologiques',
                        'keywords': ['mental', 'psychiatrie', 'psychologie', 'dépression', 'anxiété'],
                        'diseases': ['dépression', 'anxiété', 'schizophrénie', 'bipolarité'],
                        'priority': 2
                    }
                }
            },
            
            'traitements': {
                'description': 'Thérapies et interventions médicales',
                'priority': 1,
                'subcategories': {
                    'medicaments': {
                        'description': 'Pharmacothérapie et médicaments',
                        'keywords': ['médicament', 'pharmacie', 'posologie', 'effet secondaire'],
                        'types': ['antibiotiques', 'antihypertenseurs', 'antidiabétiques', 'analgésiques'],
                        'priority': 1
                    },
                    'chirurgie': {
                        'description': 'Interventions chirurgicales',
                        'keywords': ['chirurgie', 'opération', 'intervention', 'anesthésie'],
                        'types': ['chirurgie cardiaque', 'neurochirurgie', 'chirurgie digestive'],
                        'priority': 2
                    },
                    'therapies_alternatives': {
                        'description': 'Médecines complémentaires et alternatives',
                        'keywords': ['alternatif', 'traditionnel', 'naturel', 'herbes'],
                        'types': ['phytothérapie', 'acupuncture', 'médecine traditionnelle'],
                        'priority': 3
                    },
                    'rehabilitation': {
                        'description': 'Rééducation et réadaptation',
                        'keywords': ['rééducation', 'kinésithérapie', 'réadaptation'],
                        'types': ['physiothérapie', 'ergothérapie', 'orthophonie'],
                        'priority': 2
                    }
                }
            },
            
            'diagnostic': {
                'description': 'Méthodes et outils diagnostiques',
                'priority': 1,
                'subcategories': {
                    'examens_cliniques': {
                        'description': 'Examens physiques et anamnèse',
                        'keywords': ['examen', 'clinique', 'anamnèse', 'palpation'],
                        'types': ['examen physique', 'interrogatoire', 'observation'],
                        'priority': 1
                    },
                    'examens_biologiques': {
                        'description': 'Analyses de laboratoire',
                        'keywords': ['analyse', 'laboratoire', 'sang', 'urine', 'biopsie'],
                        'types': ['hémogramme', 'biochimie', 'sérologie', 'microbiologie'],
                        'priority': 1
                    },
                    'imagerie_medicale': {
                        'description': 'Techniques d\'imagerie diagnostique',
                        'keywords': ['imagerie', 'radiographie', 'scanner', 'IRM', 'échographie'],
                        'types': ['radiologie', 'tomodensitométrie', 'résonance magnétique'],
                        'priority': 2
                    }
                }
            },
            
            'prevention': {
                'description': 'Mesures préventives et promotion de la santé',
                'priority': 1,
                'subcategories': {
                    'vaccination': {
                        'description': 'Immunisation et vaccins',
                        'keywords': ['vaccin', 'vaccination', 'immunisation', 'prévention'],
                        'types': ['vaccins obligatoires', 'vaccins recommandés', 'rappels'],
                        'priority': 1
                    },
                    'hygiene': {
                        'description': 'Mesures d\'hygiène et d\'assainissement',
                        'keywords': ['hygiène', 'propreté', 'assainissement', 'lavage'],
                        'types': ['hygiène corporelle', 'hygiène alimentaire', 'hygiène environnementale'],
                        'priority': 1
                    },
                    'nutrition': {
                        'description': 'Alimentation et nutrition',
                        'keywords': ['nutrition', 'alimentation', 'régime', 'diététique'],
                        'types': ['équilibre alimentaire', 'régimes thérapeutiques', 'suppléments'],
                        'priority': 2
                    },
                    'activite_physique': {
                        'description': 'Exercice et activité physique',
                        'keywords': ['exercice', 'sport', 'activité physique', 'mouvement'],
                        'types': ['exercice thérapeutique', 'sport santé', 'activité adaptée'],
                        'priority': 2
                    }
                }
            },
            
            'urgences': {
                'description': 'Situations d\'urgence médicale',
                'priority': 1,
                'subcategories': {
                    'premiers_secours': {
                        'description': 'Gestes de premiers secours',
                        'keywords': ['urgence', 'premiers secours', 'réanimation', 'sauvetage'],
                        'types': ['RCP', 'hémorragie', 'fractures', 'brûlures'],
                        'priority': 1
                    },
                    'urgences_vitales': {
                        'description': 'Urgences engageant le pronostic vital',
                        'keywords': ['vital', 'critique', 'réanimation', 'choc'],
                        'types': ['arrêt cardiaque', 'choc anaphylactique', 'coma'],
                        'priority': 1
                    }
                }
            },
            
            'specialites': {
                'description': 'Spécialités médicales',
                'priority': 2,
                'subcategories': {
                    'pediatrie': {
                        'description': 'Médecine de l\'enfant',
                        'keywords': ['enfant', 'pédiatrie', 'nourrisson', 'adolescent'],
                        'age_groups': ['nouveau-né', 'nourrisson', 'enfant', 'adolescent'],
                        'priority': 1
                    },
                    'geriatrie': {
                        'description': 'Médecine de la personne âgée',
                        'keywords': ['âgé', 'gériatrie', 'vieillissement', 'senior'],
                        'conditions': ['démence', 'fragilité', 'polypathologie'],
                        'priority': 2
                    },
                    'gynecologie': {
                        'description': 'Santé de la femme',
                        'keywords': ['femme', 'gynécologie', 'grossesse', 'accouchement'],
                        'areas': ['contraception', 'grossesse', 'ménopause'],
                        'priority': 1
                    }
                }
            }
        }
    
    def _initialize_classification_rules(self) -> List[Dict[str, Any]]:
        """Initialise les règles de classification automatique"""
        return [
            {
                'name': 'disease_classification',
                'description': 'Classification par type de maladie',
                'patterns': {
                    'maladies_infectieuses': [
                        r'\b(?:infection|virus|bactérie|parasite|contagieux|épidémie)\b',
                        r'\b(?:paludisme|tuberculose|hépatite|pneumonie|méningite)\b'
                    ],
                    'maladies_chroniques': [
                        r'\b(?:chronique|permanent|long terme|gestion|suivi)\b',
                        r'\b(?:hypertension|diabète|asthme|arthrite)\b'
                    ],
                    'maladies_cardiovasculaires': [
                        r'\b(?:cœur|cardiaque|vasculaire|circulation|tension)\b',
                        r'\b(?:infarctus|angine|arythmie)\b'
                    ]
                },
                'priority': 1
            },
            {
                'name': 'treatment_classification',
                'description': 'Classification par type de traitement',
                'patterns': {
                    'medicaments': [
                        r'\b(?:médicament|pharmacie|posologie|effet secondaire)\b',
                        r'\b(?:antibiotique|antihypertenseur|antidiabétique)\b'
                    ],
                    'chirurgie': [
                        r'\b(?:chirurgie|opération|intervention|anesthésie)\b'
                    ],
                    'prevention': [
                        r'\b(?:prévention|vaccin|hygiène|dépistage)\b'
                    ]
                },
                'priority': 1
            },
            {
                'name': 'audience_classification',
                'description': 'Classification par audience cible',
                'patterns': {
                    'general_public': [
                        r'\b(?:conseils|que faire|comment|simple|facile)\b'
                    ],
                    'healthcare_professionals': [
                        r'\b(?:diagnostic|thérapeutique|clinique|protocole)\b',
                        r'\b(?:physiopathologie|étiologie|nosologie)\b'
                    ],
                    'patients': [
                        r'\b(?:patient|malade|famille|proche)\b'
                    ]
                },
                'priority': 2
            }
        ]
    
    def organize_documents(self, documents: List[Dict[str, Any]]) -> KnowledgeHierarchy:
        """Organise les documents en hiérarchie de connaissances"""
        logger.info(f"🗂️ Organisation de {len(documents)} documents en hiérarchie...")
        
        # Créer une nouvelle hiérarchie
        hierarchy_id = hashlib.md5(f"hierarchy_{datetime.now().isoformat()}".encode()).hexdigest()[:8]
        
        hierarchy = KnowledgeHierarchy(
            hierarchy_id=hierarchy_id,
            name="Hiérarchie des Connaissances Médicales",
            description="Organisation thématique des documents médicaux collectés",
            version=self.organizer_version,
            nodes={},
            root_nodes=[],
            documents_index={},
            keywords_index=defaultdict(list),
            medical_terms_index=defaultdict(list),
            total_documents=len(documents),
            total_nodes=0,
            max_depth=0,
            created_date=datetime.now(),
            last_updated=datetime.now()
        )
        
        # Étape 1: Créer les nœuds racines basés sur la taxonomie
        self._create_root_nodes(hierarchy)
        
        # Étape 2: Classifier et organiser les documents
        self._classify_documents(hierarchy, documents)
        
        # Étape 3: Créer des sous-catégories automatiques si nécessaire
        self._create_subcategories(hierarchy)
        
        # Étape 4: Optimiser la hiérarchie
        self._optimize_hierarchy(hierarchy)
        
        # Étape 5: Calculer les statistiques
        self._calculate_hierarchy_statistics(hierarchy)
        
        # Étape 6: Créer les index
        self._build_indexes(hierarchy)
        
        self.current_hierarchy = hierarchy
        
        logger.info(f"✅ Hiérarchie créée: {hierarchy.total_nodes} nœuds, profondeur max: {hierarchy.max_depth}")
        
        return hierarchy
    
    def _create_root_nodes(self, hierarchy: KnowledgeHierarchy):
        """Crée les nœuds racines basés sur la taxonomie médicale"""
        logger.info("🌳 Création des nœuds racines...")
        
        for category_name, category_data in self.medical_taxonomy.items():
            node_id = f"root_{category_name}"
            
            node = KnowledgeNode(
                node_id=node_id,
                name=category_name.replace('_', ' ').title(),
                description=category_data['description'],
                level=0,
                parent_id=None,
                children_ids=[],
                document_ids=[],
                keywords=[],
                medical_terms=[],
                complexity_level='intermediate',
                target_audience='general_public',
                priority=category_data['priority'],
                document_count=0,
                total_content_length=0,
                average_quality_score=0.0,
                created_date=datetime.now(),
                last_updated=datetime.now()
            )
            
            hierarchy.nodes[node_id] = node
            hierarchy.root_nodes.append(node_id)
            
            # Créer les sous-catégories
            self._create_subcategory_nodes(hierarchy, node, category_data.get('subcategories', {}))
        
        hierarchy.total_nodes = len(hierarchy.nodes)
        logger.info(f"✅ {len(hierarchy.root_nodes)} nœuds racines créés")
    
    def _create_subcategory_nodes(self, hierarchy: KnowledgeHierarchy, parent_node: KnowledgeNode, subcategories: Dict[str, Any]):
        """Crée les nœuds de sous-catégories"""
        for subcat_name, subcat_data in subcategories.items():
            node_id = f"{parent_node.node_id}_{subcat_name}"
            
            node = KnowledgeNode(
                node_id=node_id,
                name=subcat_name.replace('_', ' ').title(),
                description=subcat_data['description'],
                level=parent_node.level + 1,
                parent_id=parent_node.node_id,
                children_ids=[],
                document_ids=[],
                keywords=subcat_data.get('keywords', []),
                medical_terms=subcat_data.get('diseases', []) + subcat_data.get('types', []),
                complexity_level='intermediate',
                target_audience='general_public',
                priority=subcat_data.get('priority', 2),
                document_count=0,
                total_content_length=0,
                average_quality_score=0.0,
                created_date=datetime.now(),
                last_updated=datetime.now()
            )
            
            hierarchy.nodes[node_id] = node
            parent_node.children_ids.append(node_id)
            
            # Mettre à jour la profondeur maximale
            hierarchy.max_depth = max(hierarchy.max_depth, node.level)
    
    def _classify_documents(self, hierarchy: KnowledgeHierarchy, documents: List[Dict[str, Any]]):
        """Classifie les documents dans la hiérarchie"""
        logger.info(f"📋 Classification de {len(documents)} documents...")
        
        classified_count = 0
        
        for doc in documents:
            doc_id = doc.get('file_hash', f"doc_{classified_count}")
            
            # Analyser le document pour déterminer sa classification
            classification_scores = self._analyze_document_for_classification(doc)
            
            # Trouver le meilleur nœud pour ce document
            best_node_id = self._find_best_node(hierarchy, classification_scores)
            
            if best_node_id:
                # Ajouter le document au nœud
                node = hierarchy.nodes[best_node_id]
                node.document_ids.append(doc_id)
                node.document_count += 1
                node.total_content_length += len(doc.get('cleaned_content', ''))
                
                # Mettre à jour la qualité moyenne
                quality_score = doc.get('quality_score', 0.5)
                if node.document_count == 1:
                    node.average_quality_score = quality_score
                else:
                    node.average_quality_score = (
                        (node.average_quality_score * (node.document_count - 1) + quality_score) / 
                        node.document_count
                    )
                
                # Ajouter aux index
                hierarchy.documents_index[doc_id] = best_node_id
                
                # Mettre à jour les mots-clés et termes médicaux du nœud
                doc_keywords = doc.get('keywords', [])
                doc_medical_terms = doc.get('medical_terms', [])
                
                node.keywords.extend([kw for kw in doc_keywords if kw not in node.keywords])
                node.medical_terms.extend([term for term in doc_medical_terms if term not in node.medical_terms])
                
                node.last_updated = datetime.now()
                classified_count += 1
            
            else:
                logger.warning(f"⚠️ Document non classifié: {doc.get('title', 'Sans titre')[:50]}")
        
        self.organization_stats['documents_classified'] = classified_count
        logger.info(f"✅ {classified_count}/{len(documents)} documents classifiés")
    
    def _analyze_document_for_classification(self, document: Dict[str, Any]) -> Dict[str, float]:
        """Analyse un document pour déterminer sa classification"""
        scores = defaultdict(float)
        
        # Contenu à analyser
        title = document.get('title', '').lower()
        content = document.get('cleaned_content', '').lower()
        keywords = [kw.lower() for kw in document.get('keywords', [])]
        medical_terms = [term.lower() for term in document.get('medical_terms', [])]
        category = document.get('category', '').lower()
        specialty = document.get('specialty', '').lower()
        
        # Texte combiné pour l'analyse
        combined_text = f"{title} {content} {' '.join(keywords)} {' '.join(medical_terms)} {category} {specialty}"
        
        # Appliquer les règles de classification
        for rule in self.classification_rules:
            for category_name, patterns in rule['patterns'].items():
                category_score = 0.0
                
                for pattern in patterns:
                    matches = len(re.findall(pattern, combined_text, re.IGNORECASE))
                    category_score += matches * rule['priority']
                
                scores[category_name] += category_score
        
        # Bonus pour correspondance directe avec catégorie/spécialité
        if category:
            for node_id, node in self.current_hierarchy.nodes.items() if self.current_hierarchy else []:
                if category in node.name.lower() or any(kw in category for kw in node.keywords):
                    scores[node_id] += 5.0
        
        return dict(scores)
    
    def _find_best_node(self, hierarchy: KnowledgeHierarchy, classification_scores: Dict[str, float]) -> Optional[str]:
        """Trouve le meilleur nœud pour un document"""
        best_node_id = None
        best_score = 0.0
        
        # Chercher parmi tous les nœuds
        for node_id, node in hierarchy.nodes.items():
            node_score = 0.0
            
            # Score basé sur les mots-clés du nœud
            for keyword in node.keywords:
                if keyword.lower() in classification_scores:
                    node_score += classification_scores[keyword.lower()]
            
            # Score basé sur les termes médicaux du nœud
            for term in node.medical_terms:
                if term.lower() in classification_scores:
                    node_score += classification_scores[term.lower()]
            
            # Score basé sur le nom du nœud
            node_name_lower = node.name.lower().replace(' ', '_')
            if node_name_lower in classification_scores:
                node_score += classification_scores[node_name_lower] * 2  # Bonus pour correspondance directe
            
            # Préférer les nœuds feuilles (plus spécifiques)
            if not node.children_ids:
                node_score *= 1.2
            
            # Éviter les nœuds surchargés
            if node.document_count > self.max_documents_per_node:
                node_score *= 0.5
            
            if node_score > best_score:
                best_score = node_score
                best_node_id = node_id
        
        return best_node_id if best_score > 0 else None
    
    def _create_subcategories(self, hierarchy: KnowledgeHierarchy):
        """Crée des sous-catégories automatiques pour les nœuds surchargés"""
        logger.info("🔄 Création de sous-catégories automatiques...")
        
        nodes_to_subdivide = []
        
        # Identifier les nœuds à subdiviser
        for node_id, node in hierarchy.nodes.items():
            if (node.document_count > self.max_documents_per_node and 
                node.level < self.max_depth - 1 and 
                not node.children_ids):
                nodes_to_subdivide.append(node_id)
        
        for node_id in nodes_to_subdivide:
            self._subdivide_node(hierarchy, node_id)
        
        logger.info(f"✅ {len(nodes_to_subdivide)} nœuds subdivisés")
    
    def _subdivide_node(self, hierarchy: KnowledgeHierarchy, node_id: str):
        """Subdivise un nœud en sous-catégories"""
        node = hierarchy.nodes[node_id]
        
        # Analyser les documents du nœud pour créer des groupes
        document_groups = self._group_documents_by_similarity(hierarchy, node.document_ids)
        
        # Créer des sous-nœuds pour chaque groupe
        for i, (group_name, doc_ids) in enumerate(document_groups.items()):
            if len(doc_ids) >= self.min_documents_per_node:
                subnode_id = f"{node_id}_sub_{i+1}"
                
                subnode = KnowledgeNode(
                    node_id=subnode_id,
                    name=f"{node.name} - {group_name}",
                    description=f"Sous-catégorie de {node.name}: {group_name}",
                    level=node.level + 1,
                    parent_id=node_id,
                    children_ids=[],
                    document_ids=doc_ids,
                    keywords=[],
                    medical_terms=[],
                    complexity_level=node.complexity_level,
                    target_audience=node.target_audience,
                    priority=node.priority,
                    document_count=len(doc_ids),
                    total_content_length=0,
                    average_quality_score=0.0,
                    created_date=datetime.now(),
                    last_updated=datetime.now()
                )
                
                hierarchy.nodes[subnode_id] = subnode
                node.children_ids.append(subnode_id)
                
                # Mettre à jour l'index des documents
                for doc_id in doc_ids:
                    hierarchy.documents_index[doc_id] = subnode_id
        
        # Vider le nœud parent des documents (maintenant dans les sous-nœuds)
        node.document_ids = []
        node.document_count = 0
        
        # Mettre à jour la profondeur maximale
        hierarchy.max_depth = max(hierarchy.max_depth, node.level + 1)
    
    def _group_documents_by_similarity(self, hierarchy: KnowledgeHierarchy, document_ids: List[str]) -> Dict[str, List[str]]:
        """Groupe les documents par similarité"""
        # Implémentation simplifiée - pourrait être améliorée avec du clustering
        groups = defaultdict(list)
        
        # Pour l'instant, grouper par première lettre du titre ou par mots-clés communs
        # Dans une implémentation plus avancée, on utiliserait des embeddings
        
        for doc_id in document_ids:
            # Trouver le document (simulation)
            group_key = f"Groupe {len(groups) % 3 + 1}"  # Groupes arbitraires pour la démo
            groups[group_key].append(doc_id)
        
        return dict(groups)
    
    def _optimize_hierarchy(self, hierarchy: KnowledgeHierarchy):
        """Optimise la hiérarchie en fusionnant ou réorganisant les nœuds"""
        logger.info("⚡ Optimisation de la hiérarchie...")
        
        # Fusionner les nœuds avec trop peu de documents
        self._merge_small_nodes(hierarchy)
        
        # Équilibrer la hiérarchie
        self._balance_hierarchy(hierarchy)
        
        logger.info("✅ Hiérarchie optimisée")
    
    def _merge_small_nodes(self, hierarchy: KnowledgeHierarchy):
        """Fusionne les nœuds avec trop peu de documents"""
        nodes_to_remove = []
        
        for node_id, node in hierarchy.nodes.items():
            if (node.document_count < self.min_documents_per_node and 
                node.parent_id and 
                not node.children_ids):
                
                # Fusionner avec le parent
                parent_node = hierarchy.nodes[node.parent_id]
                parent_node.document_ids.extend(node.document_ids)
                parent_node.document_count += node.document_count
                parent_node.children_ids.remove(node_id)
                
                # Mettre à jour l'index
                for doc_id in node.document_ids:
                    hierarchy.documents_index[doc_id] = node.parent_id
                
                nodes_to_remove.append(node_id)
        
        # Supprimer les nœuds fusionnés
        for node_id in nodes_to_remove:
            del hierarchy.nodes[node_id]
        
        hierarchy.total_nodes = len(hierarchy.nodes)
    
    def _balance_hierarchy(self, hierarchy: KnowledgeHierarchy):
        """Équilibre la hiérarchie"""
        # Implémentation simplifiée
        # Dans une version complète, on pourrait réorganiser les nœuds
        # pour équilibrer la charge et la profondeur
        pass
    
    def _calculate_hierarchy_statistics(self, hierarchy: KnowledgeHierarchy):
        """Calcule les statistiques de la hiérarchie"""
        logger.info("📊 Calcul des statistiques...")
        
        # Statistiques par niveau
        level_stats = defaultdict(int)
        total_documents = 0
        
        for node in hierarchy.nodes.values():
            level_stats[node.level] += 1
            total_documents += node.document_count
        
        # Mettre à jour les statistiques globales
        self.organization_stats.update({
            'total_organized': hierarchy.total_documents,
            'nodes_created': hierarchy.total_nodes,
            'documents_classified': total_documents,
            'hierarchy_depth': hierarchy.max_depth,
            'classification_accuracy': total_documents / hierarchy.total_documents if hierarchy.total_documents > 0 else 0
        })
        
        logger.info(f"📈 Statistiques: {hierarchy.total_nodes} nœuds, {total_documents} documents classifiés")
    
    def _build_indexes(self, hierarchy: KnowledgeHierarchy):
        """Construit les index de recherche"""
        logger.info("🔍 Construction des index...")
        
        # Index des mots-clés
        for node_id, node in hierarchy.nodes.items():
            for keyword in node.keywords:
                hierarchy.keywords_index[keyword.lower()].append(node_id)
        
        # Index des termes médicaux
        for node_id, node in hierarchy.nodes.items():
            for term in node.medical_terms:
                hierarchy.medical_terms_index[term.lower()].append(node_id)
        
        logger.info(f"✅ Index créés: {len(hierarchy.keywords_index)} mots-clés, {len(hierarchy.medical_terms_index)} termes médicaux")
    
    def search_hierarchy(self, hierarchy: KnowledgeHierarchy, query: str, search_type: str = 'all') -> List[Dict[str, Any]]:
        """Recherche dans la hiérarchie"""
        results = []
        query_lower = query.lower()
        
        for node_id, node in hierarchy.nodes.items():
            score = 0.0
            
            # Recherche dans le nom
            if query_lower in node.name.lower():
                score += 3.0
            
            # Recherche dans la description
            if query_lower in node.description.lower():
                score += 2.0
            
            # Recherche dans les mots-clés
            for keyword in node.keywords:
                if query_lower in keyword.lower():
                    score += 1.5
            
            # Recherche dans les termes médicaux
            for term in node.medical_terms:
                if query_lower in term.lower():
                    score += 2.0
            
            if score > 0:
                results.append({
                    'node_id': node_id,
                    'node': node,
                    'score': score,
                    'relevance': min(score / 5.0, 1.0)
                })
        
        # Trier par score
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results[:20]  # Limiter à 20 résultats
    
    def get_node_path(self, hierarchy: KnowledgeHierarchy, node_id: str) -> List[str]:
        """Obtient le chemin complet vers un nœud"""
        path = []
        current_id = node_id
        
        while current_id:
            node = hierarchy.nodes.get(current_id)
            if node:
                path.insert(0, node.name)
                current_id = node.parent_id
            else:
                break
        
        return path
    
    def export_hierarchy(self, hierarchy: KnowledgeHierarchy, output_path: Path, format_type: str = 'json') -> bool:
        """Exporte la hiérarchie"""
        try:
            output_path.mkdir(parents=True, exist_ok=True)
            
            if format_type == 'json':
                # Export JSON complet
                hierarchy_dict = asdict(hierarchy)
                
                # Convertir les dates
                hierarchy_dict['created_date'] = hierarchy.created_date.isoformat()
                hierarchy_dict['last_updated'] = hierarchy.last_updated.isoformat()
                
                for node_id, node_dict in hierarchy_dict['nodes'].items():
                    node_dict['created_date'] = hierarchy.nodes[node_id].created_date.isoformat()
                    node_dict['last_updated'] = hierarchy.nodes[node_id].last_updated.isoformat()
                
                filepath = output_path / f"knowledge_hierarchy_{hierarchy.hierarchy_id}.json"
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(hierarchy_dict, f, ensure_ascii=False, indent=2)
            
            elif format_type == 'tree':
                # Export format arbre lisible
                self._export_tree_format(hierarchy, output_path)
            
            elif format_type == 'csv':
                # Export CSV pour analyse
                self._export_csv_format(hierarchy, output_path)
            
            logger.info(f"💾 Hiérarchie exportée vers {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'export: {e}")
            return False
    
    def _export_tree_format(self, hierarchy: KnowledgeHierarchy, output_path: Path):
        """Exporte la hiérarchie en format arbre lisible"""
        filepath = output_path / f"hierarchy_tree_{hierarchy.hierarchy_id}.txt"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Hiérarchie des Connaissances Médicales\n")
            f.write(f"{'='*50}\n\n")
            
            for root_id in hierarchy.root_nodes:
                self._write_node_tree(f, hierarchy, root_id, 0)
    
    def _write_node_tree(self, file, hierarchy: KnowledgeHierarchy, node_id: str, level: int):
        """Écrit un nœud et ses enfants en format arbre"""
        node = hierarchy.nodes[node_id]
        indent = "  " * level
        
        file.write(f"{indent}├─ {node.name} ({node.document_count} docs)\n")
        file.write(f"{indent}   {node.description}\n")
        
        if node.keywords:
            file.write(f"{indent}   Mots-clés: {', '.join(node.keywords[:5])}\n")
        
        file.write("\n")
        
        for child_id in node.children_ids:
            self._write_node_tree(file, hierarchy, child_id, level + 1)
    
    def _export_csv_format(self, hierarchy: KnowledgeHierarchy, output_path: Path):
        """Exporte la hiérarchie en format CSV"""
        import csv
        
        filepath = output_path / f"hierarchy_data_{hierarchy.hierarchy_id}.csv"
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # En-têtes
            writer.writerow([
                'node_id', 'name', 'description', 'level', 'parent_id',
                'document_count', 'keywords', 'medical_terms', 'priority'
            ])
            
            # Données
            for node_id, node in hierarchy.nodes.items():
                writer.writerow([
                    node_id,
                    node.name,
                    node.description,
                    node.level,
                    node.parent_id or '',
                    node.document_count,
                    '; '.join(node.keywords),
                    '; '.join(node.medical_terms),
                    node.priority
                ])
    
    def get_organization_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques d'organisation"""
        return self.organization_stats.copy()

def main():
    """Fonction principale pour tester l'organisateur"""
    # Configuration de test
    config = {
        'max_hierarchy_depth': 4,
        'min_documents_per_node': 3,
        'max_documents_per_node': 20
    }
    
    organizer = KnowledgeOrganizer(config)
    
    # Documents de test
    test_documents = [
        {
            'title': 'Hypertension artérielle: diagnostic et traitement',
            'cleaned_content': 'L\'hypertension artérielle est une maladie chronique...',
            'keywords': ['hypertension', 'tension', 'cardiologie'],
            'medical_terms': ['hypertension', 'antihypertenseur'],
            'category': 'maladies_chroniques',
            'specialty': 'Cardiologie',
            'quality_score': 0.85,
            'file_hash': 'doc1'
        },
        {
            'title': 'Paludisme: prévention et traitement',
            'cleaned_content': 'Le paludisme est une maladie infectieuse...',
            'keywords': ['paludisme', 'moustique', 'prévention'],
            'medical_terms': ['paludisme', 'plasmodium'],
            'category': 'maladies_infectieuses',
            'specialty': 'Infectiologie',
            'quality_score': 0.90,
            'file_hash': 'doc2'
        },
        {
            'title': 'Vaccination: calendrier et recommandations',
            'cleaned_content': 'La vaccination est un moyen de prévention...',
            'keywords': ['vaccination', 'vaccin', 'prévention'],
            'medical_terms': ['vaccination', 'immunisation'],
            'category': 'prevention',
            'specialty': 'Médecine préventive',
            'quality_score': 0.88,
            'file_hash': 'doc3'
        }
    ]
    
    logger.info("🧪 Test de l'organisateur de connaissances...")
    
    # Organiser les documents
    hierarchy = organizer.organize_documents(test_documents)
    
    logger.info(f"✅ Hiérarchie créée")
    logger.info(f"📊 Nœuds: {hierarchy.total_nodes}")
    logger.info(f"📚 Documents: {hierarchy.total_documents}")
    logger.info(f"🌳 Profondeur: {hierarchy.max_depth}")
    
    # Test de recherche
    search_results = organizer.search_hierarchy(hierarchy, "hypertension")
    logger.info(f"🔍 Résultats de recherche pour 'hypertension': {len(search_results)}")
    
    # Export
    output_path = Path("../data/knowledge_hierarchy/test")
    organizer.export_hierarchy(hierarchy, output_path, 'json')
    organizer.export_hierarchy(hierarchy, output_path, 'tree')
    
    # Statistiques
    stats = organizer.get_organization_statistics()
    logger.info(f"📈 Statistiques: {stats}")

if __name__ == "__main__":
    main()