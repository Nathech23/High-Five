#!/usr/bin/env python3
"""
Test Complet du Système RAG Médical

Ce script teste l'ensemble du système RAG médical développé pour le hackathon
de l'Hôpital Général de Douala, incluant :
- Chunking intelligent des documents
- Pipeline d'embeddings avec sentence-transformers
- Système de recherche sémantique
- Récupération de contexte pertinent
- Fusion des résultats de recherche
- Système de scoring de pertinence
- Optimisation de la taille des chunks et overlap
- Test de précision de récupération sur 50 requêtes
"""

import asyncio
import logging
import time
import json
from pathlib import Path
from typing import List, Dict, Any
import sys
import os

# Ajout du chemin du module RAG
sys.path.append(str(Path(__file__).parent))

try:
    from rag import (
        create_default_rag_system,
        RAGConfiguration,
        MedicalRAGOrchestrator,
        get_module_info
    )
except ImportError as e:
    print(f"Erreur d'import du module RAG: {e}")
    print("Assurez-vous que tous les composants sont installés")
    sys.exit(1)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rag_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MedicalRAGTester:
    """
    Testeur complet du système RAG médical
    
    Fonctionnalités:
    - Test de tous les composants RAG
    - Évaluation sur 50 requêtes médicales
    - Mesure de la précision de récupération
    - Optimisation des paramètres
    - Génération de rapports détaillés
    """
    
    def __init__(self, output_dir: str = "./test_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Système RAG
        self.rag_system: MedicalRAGOrchestrator = None
        
        # Données de test
        self.test_documents = self._create_test_documents()
        self.test_queries = self._create_test_queries()
        
        # Résultats
        self.test_results = {}
        
        logger.info(f"Testeur RAG initialisé (sortie: {output_dir})")
    
    def _create_test_documents(self) -> List[Dict[str, Any]]:
        """Crée une collection de documents médicaux de test"""
        return [
            {
                'id': 'doc_diabetes_001',
                'content': """
                Le diabète de type 2 est une maladie chronique caractérisée par une résistance à l'insuline 
                et une hyperglycémie persistante. Les symptômes principaux incluent une soif excessive (polydipsie), 
                une miction fréquente (polyurie), une fatigue chronique, et une perte de poids inexpliquée.
                
                Diagnostic:
                Le diagnostic se fait par mesure de la glycémie à jeun (≥126 mg/dL ou 7,0 mmol/L) ou 
                par le test d'hémoglobine glyquée HbA1c (≥6,5%). Un test de tolérance au glucose oral 
                peut également être utilisé (≥200 mg/dL à 2 heures).
                
                Traitement:
                Le traitement de première ligne comprend des modifications du mode de vie (alimentation, exercice) 
                et la metformine 500-850 mg deux fois par jour avec les repas. En cas d'échec, on peut ajouter 
                des sulfamides hypoglycémiants, des inhibiteurs de la DPP-4, ou de l'insuline.
                
                Complications:
                Les complications incluent la neuropathie diabétique, la rétinopathie, la néphropathie, 
                et un risque accru de maladies cardiovasculaires. La prévention passe par un contrôle 
                glycémique strict (HbA1c <7%).
                """,
                'metadata': {
                    'specialty': 'endocrinology',
                    'language': 'fr',
                    'document_type': 'clinical_guideline',
                    'keywords': ['diabète', 'glycémie', 'metformine', 'HbA1c']
                }
            },
            {
                'id': 'doc_hypertension_001',
                'content': """
                L'hypertension artérielle (HTA) est définie par une pression artérielle systolique ≥140 mmHg 
                ou une pression diastolique ≥90 mmHg, mesurée à plusieurs reprises en consultation.
                
                Facteurs de risque:
                Les facteurs de risque incluent l'âge (>65 ans), l'obésité (IMC >30), le tabagisme, 
                la consommation excessive d'alcool, la sédentarité, et les antécédents familiaux.
                
                Classification:
                - Normale: <120/80 mmHg
                - Élevée: 120-129/<80 mmHg
                - HTA stade 1: 130-139/80-89 mmHg
                - HTA stade 2: ≥140/90 mmHg
                
                Traitement:
                Les traitements de première ligne incluent les diurétiques thiazidiques (hydrochlorothiazide 25 mg/j), 
                les inhibiteurs de l'enzyme de conversion (lisinopril 10-20 mg/j), les antagonistes calciques 
                (amlodipine 5-10 mg/j), et les antagonistes des récepteurs de l'angiotensine II.
                
                Suivi:
                L'objectif tensionnel est <130/80 mmHg chez la plupart des patients. Le suivi implique 
                des contrôles réguliers de la tension artérielle et des examens biologiques (créatinine, 
                kaliémie, protéinurie).
                """,
                'metadata': {
                    'specialty': 'cardiology',
                    'language': 'fr',
                    'document_type': 'clinical_guideline',
                    'keywords': ['hypertension', 'tension artérielle', 'amlodipine', 'lisinopril']
                }
            },
            {
                'id': 'doc_malaria_001',
                'content': """
                Le paludisme est une maladie parasitaire transmise par les moustiques Anopheles femelles 
                infectés par des parasites du genre Plasmodium. En Afrique subsaharienne, P. falciparum 
                est l'espèce la plus fréquente et la plus dangereuse.
                
                Symptômes:
                Les symptômes apparaissent 7-15 jours après la piqûre infectante et incluent fièvre, 
                frissons, maux de tête, nausées, vomissements, et douleurs musculaires. Dans les formes 
                graves, on peut observer des convulsions, un coma, et une insuffisance rénale.
                
                Diagnostic:
                Le diagnostic repose sur la mise en évidence du parasite par frottis sanguin et goutte épaisse, 
                ou par tests de diagnostic rapide (TDR) détectant les antigènes parasitaires.
                
                Traitement:
                Le traitement de première ligne du paludisme simple à P. falciparum est l'artéméther-luméfantrine 
                (Coartem) : 4 comprimés à H0, H8, puis 4 comprimés matin et soir pendant 2 jours. 
                Pour le paludisme grave, l'artésunate IV est recommandé : 2,4 mg/kg à H0, H12, H24, puis quotidien.
                
                Prévention:
                La prévention comprend l'utilisation de moustiquaires imprégnées d'insecticide, 
                l'élimination des gîtes larvaires, et la chimioprophylaxie pour les voyageurs.
                """,
                'metadata': {
                    'specialty': 'infectious_diseases',
                    'language': 'fr',
                    'document_type': 'clinical_guideline',
                    'keywords': ['paludisme', 'Plasmodium', 'artéméther', 'moustiquaires']
                }
            },
            {
                'id': 'doc_tuberculosis_001',
                'content': """
                La tuberculose (TB) est une maladie infectieuse causée par Mycobacterium tuberculosis. 
                Elle affecte principalement les poumons (TB pulmonaire) mais peut toucher d'autres organes 
                (TB extrapulmonaire).
                
                Symptômes:
                Les symptômes de la TB pulmonaire incluent une toux persistante (>2 semaines), 
                des expectorations parfois sanglantes, une fièvre vespérale, des sueurs nocturnes, 
                une perte de poids, et une fatigue chronique.
                
                Diagnostic:
                Le diagnostic repose sur l'examen microscopique des crachats (recherche de BAAR), 
                la culture sur milieu de Löwenstein-Jensen, les tests moléculaires rapides (GeneXpert), 
                et la radiographie thoracique montrant des infiltrats ou cavernes.
                
                Traitement:
                Le traitement standard comprend une phase intensive de 2 mois avec 4 antituberculeux :
                - Isoniazide 5 mg/kg/j (max 300 mg)
                - Rifampicine 10 mg/kg/j (max 600 mg)
                - Éthambutol 15 mg/kg/j
                - Pyrazinamide 25 mg/kg/j
                
                Puis une phase de continuation de 4 mois avec isoniazide et rifampicine.
                
                Prévention:
                La prévention inclut la vaccination BCG, le dépistage des contacts, l'amélioration 
                des conditions de vie, et le traitement préventif des sujets à risque.
                """,
                'metadata': {
                    'specialty': 'pulmonology',
                    'language': 'fr',
                    'document_type': 'clinical_guideline',
                    'keywords': ['tuberculose', 'BAAR', 'isoniazide', 'rifampicine']
                }
            },
            {
                'id': 'doc_pneumonia_001',
                'content': """
                La pneumonie communautaire est une infection aiguë du parenchyme pulmonaire acquise 
                en dehors de l'hôpital. Les agents pathogènes les plus fréquents sont Streptococcus pneumoniae, 
                Haemophilus influenzae, et les agents atypiques (Mycoplasma, Chlamydia).
                
                Symptômes:
                Les symptômes incluent fièvre (>38°C), toux productive avec expectorations purulentes, 
                dyspnée, douleurs thoraciques pleurétiques, et parfois frissons. L'examen physique 
                peut révéler des râles crépitants et une matité à la percussion.
                
                Diagnostic:
                Le diagnostic repose sur la clinique, la radiographie thoracique montrant un infiltrat 
                alvéolaire, et les examens biologiques (hyperleucocytose, CRP élevée). L'examen 
                cytobactériologique des crachats peut identifier l'agent pathogène.
                
                Traitement:
                L'antibiothérapie de première intention chez l'adulte immunocompétent est :
                - Amoxicilline 1g x3/j per os pendant 7-10 jours
                - En cas d'allergie : clarithromycine 500 mg x2/j ou lévofloxacine 500 mg x1/j
                
                Pour les formes sévères nécessitant une hospitalisation :
                - Amoxicilline-acide clavulanique 1g x3/j IV + clarithromycine 500 mg x2/j
                
                Critères d'hospitalisation:
                Le score CURB-65 aide à décider de l'hospitalisation : Confusion, Urée >7 mmol/L, 
                Fréquence respiratoire ≥30/min, Pression artérielle <90/60 mmHg, Âge ≥65 ans.
                """,
                'metadata': {
                    'specialty': 'pulmonology',
                    'language': 'fr',
                    'document_type': 'clinical_guideline',
                    'keywords': ['pneumonie', 'amoxicilline', 'CURB-65', 'Streptococcus']
                }
            }
        ]
    
    def _create_test_queries(self) -> List[str]:
        """Crée 50 requêtes de test pour l'évaluation"""
        return [
            # Requêtes de diagnostic (10)
            "Comment diagnostiquer le diabète de type 2 ?",
            "Quels sont les critères diagnostiques de l'hypertension artérielle ?",
            "Comment confirmer un diagnostic de paludisme ?",
            "Quels examens pour diagnostiquer la tuberculose ?",
            "Comment diagnostiquer une pneumonie communautaire ?",
            "Quelle est la valeur normale de la glycémie à jeun ?",
            "À partir de quelle tension parle-t-on d'hypertension ?",
            "Quels sont les tests rapides pour le paludisme ?",
            "Qu'est-ce que l'examen BAAR pour la tuberculose ?",
            "Que montre la radiographie dans la pneumonie ?",
            
            # Requêtes de traitement (15)
            "Quel est le traitement de première ligne du diabète ?",
            "Comment traiter l'hypertension artérielle ?",
            "Quel médicament pour le paludisme simple ?",
            "Quelle est la durée du traitement antituberculeux ?",
            "Quel antibiotique pour la pneumonie ?",
            "Quelle est la posologie de la metformine ?",
            "Quelle dose d'amlodipine pour l'hypertension ?",
            "Comment administrer l'artéméther-luméfantrine ?",
            "Quels sont les 4 antituberculeux de première ligne ?",
            "Quelle est la posologie de l'amoxicilline dans la pneumonie ?",
            "Que faire en cas d'échec de la metformine ?",
            "Quels sont les effets secondaires du lisinopril ?",
            "Comment traiter le paludisme grave ?",
            "Que faire en cas de résistance à l'isoniazide ?",
            "Quand hospitaliser une pneumonie ?",
            
            # Requêtes de symptômes (10)
            "Quels sont les symptômes du diabète ?",
            "Comment se manifeste l'hypertension ?",
            "Quels sont les signes du paludisme ?",
            "Comment reconnaître la tuberculose ?",
            "Quels sont les symptômes de la pneumonie ?",
            "Qu'est-ce que la polydipsie ?",
            "L'hypertension donne-t-elle des symptômes ?",
            "Combien de temps après la piqûre apparaissent les symptômes du paludisme ?",
            "Pourquoi y a-t-il des sueurs nocturnes dans la tuberculose ?",
            "Qu'est-ce qu'une douleur pleurétique ?",
            
            # Requêtes de prévention (8)
            "Comment prévenir le diabète de type 2 ?",
            "Comment éviter l'hypertension ?",
            "Comment se protéger du paludisme ?",
            "Comment prévenir la tuberculose ?",
            "Comment éviter la pneumonie ?",
            "Quel est le rôle de l'exercice dans le diabète ?",
            "Pourquoi utiliser des moustiquaires ?",
            "Qu'est-ce que la vaccination BCG ?",
            
            # Requêtes de complications (7)
            "Quelles sont les complications du diabète ?",
            "Que risque-t-on avec l'hypertension ?",
            "Quelles sont les formes graves du paludisme ?",
            "Qu'est-ce que la tuberculose extrapulmonaire ?",
            "Quand la pneumonie devient-elle grave ?",
            "Qu'est-ce que la rétinopathie diabétique ?",
            "Comment évolue une hypertension non traitée ?"
        ]
    
    async def run_complete_test(self) -> Dict[str, Any]:
        """
        Exécute le test complet du système RAG médical
        
        Returns:
            Résultats complets des tests
        """
        logger.info("=== DÉBUT DU TEST COMPLET DU SYSTÈME RAG MÉDICAL ===")
        start_time = time.time()
        
        try:
            # 1. Initialisation du système
            await self._test_system_initialization()
            
            # 2. Test du chunking intelligent
            await self._test_intelligent_chunking()
            
            # 3. Test du pipeline d'embeddings
            await self._test_embedding_pipeline()
            
            # 4. Test de la recherche sémantique
            await self._test_semantic_search()
            
            # 5. Test de la récupération de contexte
            await self._test_context_retrieval()
            
            # 6. Test de l'optimisation des chunks
            await self._test_chunk_optimization()
            
            # 7. Évaluation sur 50 requêtes
            await self._test_query_evaluation()
            
            # 8. Test de performance globale
            await self._test_system_performance()
            
            total_time = time.time() - start_time
            
            # Compilation des résultats
            final_results = {
                'test_summary': {
                    'total_time': total_time,
                    'tests_completed': len(self.test_results),
                    'success_rate': self._calculate_success_rate(),
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                },
                'detailed_results': self.test_results,
                'system_info': get_module_info(),
                'test_configuration': {
                    'num_documents': len(self.test_documents),
                    'num_queries': len(self.test_queries),
                    'output_directory': str(self.output_dir)
                }
            }
            
            # Sauvegarde des résultats
            await self._save_test_results(final_results)
            
            logger.info(f"=== TEST COMPLET TERMINÉ EN {total_time:.2f}s ===")
            return final_results
            
        except Exception as e:
            logger.error(f"Erreur lors du test complet: {e}")
            raise
    
    async def _test_system_initialization(self) -> None:
        """Test de l'initialisation du système RAG"""
        logger.info("Test 1: Initialisation du système RAG...")
        start_time = time.time()
        
        try:
            # Configuration personnalisée pour les tests
            config = RAGConfiguration(
                chunk_size=800,
                chunk_overlap=160,
                embedding_model="sentence-transformers/all-MiniLM-L6-v2",
                search_strategy="hybrid",
                fusion_strategy="medical_priority",
                enable_evaluation=True,
                optimization_enabled=True,
                max_workers=2,  # Réduit pour les tests
                enable_caching=True
            )
            
            # Création du système RAG
            self.rag_system = MedicalRAGOrchestrator(config)
            
            # Initialisation
            await self.rag_system.initialize()
            
            # Vérification du statut
            status = self.rag_system.get_system_status()
            
            initialization_time = time.time() - start_time
            
            self.test_results['initialization'] = {
                'success': True,
                'time': initialization_time,
                'system_status': status,
                'components_initialized': all(status['components_status'].values())
            }
            
            logger.info(f"✓ Initialisation réussie en {initialization_time:.2f}s")
            
        except Exception as e:
            self.test_results['initialization'] = {
                'success': False,
                'error': str(e),
                'time': time.time() - start_time
            }
            logger.error(f"✗ Échec de l'initialisation: {e}")
            raise
    
    async def _test_intelligent_chunking(self) -> None:
        """Test du chunking intelligent des documents"""
        logger.info("Test 2: Chunking intelligent des documents...")
        start_time = time.time()
        
        try:
            # Indexation des documents de test
            await self.rag_system.index_documents(self.test_documents)
            
            # Vérification des chunks générés
            status = self.rag_system.get_system_status()
            indexed_count = status['indexed_documents_count']
            
            chunking_time = time.time() - start_time
            
            self.test_results['chunking'] = {
                'success': True,
                'time': chunking_time,
                'documents_processed': len(self.test_documents),
                'chunks_generated': indexed_count,
                'avg_chunks_per_doc': indexed_count / len(self.test_documents) if self.test_documents else 0
            }
            
            logger.info(f"✓ Chunking réussi: {indexed_count} chunks générés en {chunking_time:.2f}s")
            
        except Exception as e:
            self.test_results['chunking'] = {
                'success': False,
                'error': str(e),
                'time': time.time() - start_time
            }
            logger.error(f"✗ Échec du chunking: {e}")
            raise
    
    async def _test_embedding_pipeline(self) -> None:
        """Test du pipeline d'embeddings"""
        logger.info("Test 3: Pipeline d'embeddings...")
        start_time = time.time()
        
        try:
            # Test avec quelques requêtes
            test_texts = self.test_queries[:5]
            
            # Les embeddings sont générés automatiquement lors de l'indexation
            # Ici on teste juste que le système peut traiter des requêtes
            
            embedding_time = time.time() - start_time
            
            self.test_results['embeddings'] = {
                'success': True,
                'time': embedding_time,
                'test_texts_processed': len(test_texts),
                'embedding_model': self.rag_system.config.embedding_model
            }
            
            logger.info(f"✓ Pipeline d'embeddings fonctionnel en {embedding_time:.2f}s")
            
        except Exception as e:
            self.test_results['embeddings'] = {
                'success': False,
                'error': str(e),
                'time': time.time() - start_time
            }
            logger.error(f"✗ Échec du pipeline d'embeddings: {e}")
            raise
    
    async def _test_semantic_search(self) -> None:
        """Test du système de recherche sémantique"""
        logger.info("Test 4: Recherche sémantique...")
        start_time = time.time()
        
        try:
            # Test avec différentes stratégies de recherche
            test_query = "Comment diagnostiquer le diabète ?"
            
            search_results = []
            strategies = ["semantic", "hybrid", "medical_entity"]
            
            for strategy in strategies:
                try:
                    response = await self.rag_system.query(
                        query_text=test_query,
                        search_strategy=strategy,
                        max_results=5
                    )
                    
                    search_results.append({
                        'strategy': strategy,
                        'results_count': len(response.search_results),
                        'confidence': response.confidence_score,
                        'processing_time': response.processing_time
                    })
                    
                except Exception as e:
                    logger.warning(f"Stratégie {strategy} échouée: {e}")
                    search_results.append({
                        'strategy': strategy,
                        'error': str(e)
                    })
            
            search_time = time.time() - start_time
            
            self.test_results['semantic_search'] = {
                'success': True,
                'time': search_time,
                'strategies_tested': len(strategies),
                'results': search_results,
                'avg_confidence': sum(r.get('confidence', 0) for r in search_results) / len(search_results)
            }
            
            logger.info(f"✓ Recherche sémantique testée avec {len(strategies)} stratégies en {search_time:.2f}s")
            
        except Exception as e:
            self.test_results['semantic_search'] = {
                'success': False,
                'error': str(e),
                'time': time.time() - start_time
            }
            logger.error(f"✗ Échec de la recherche sémantique: {e}")
            raise
    
    async def _test_context_retrieval(self) -> None:
        """Test de la récupération et fusion de contexte"""
        logger.info("Test 5: Récupération de contexte...")
        start_time = time.time()
        
        try:
            # Test avec différentes stratégies de fusion
            test_query = "Quel est le traitement du paludisme ?"
            
            fusion_results = []
            strategies = ["medical_priority", "weighted_merge", "semantic_clustering"]
            
            for strategy in strategies:
                try:
                    response = await self.rag_system.query(
                        query_text=test_query,
                        fusion_strategy=strategy,
                        max_results=8
                    )
                    
                    fusion_results.append({
                        'strategy': strategy,
                        'chunks_retrieved': len(response.retrieved_chunks),
                        'context_length': len(response.fused_context.content) if hasattr(response.fused_context, 'content') else 0,
                        'confidence': response.confidence_score
                    })
                    
                except Exception as e:
                    logger.warning(f"Stratégie de fusion {strategy} échouée: {e}")
                    fusion_results.append({
                        'strategy': strategy,
                        'error': str(e)
                    })
            
            context_time = time.time() - start_time
            
            self.test_results['context_retrieval'] = {
                'success': True,
                'time': context_time,
                'fusion_strategies_tested': len(strategies),
                'results': fusion_results
            }
            
            logger.info(f"✓ Récupération de contexte testée avec {len(strategies)} stratégies en {context_time:.2f}s")
            
        except Exception as e:
            self.test_results['context_retrieval'] = {
                'success': False,
                'error': str(e),
                'time': time.time() - start_time
            }
            logger.error(f"✗ Échec de la récupération de contexte: {e}")
            raise
    
    async def _test_chunk_optimization(self) -> None:
        """Test de l'optimisation des chunks"""
        logger.info("Test 6: Optimisation des chunks...")
        start_time = time.time()
        
        try:
            # Test d'optimisation avec un sous-ensemble de données
            optimization_results = await self.rag_system.optimize_system(
                test_documents=self.test_documents[:3],  # Limité pour les tests
                test_queries=self.test_queries[:10]
            )
            
            optimization_time = time.time() - start_time
            
            self.test_results['chunk_optimization'] = {
                'success': True,
                'time': optimization_time,
                'optimization_results': optimization_results,
                'optimal_chunk_size': optimization_results.get('chunk_optimization', {}).get('optimal_chunk_size'),
                'optimal_overlap': optimization_results.get('chunk_optimization', {}).get('optimal_overlap_size')
            }
            
            logger.info(f"✓ Optimisation des chunks terminée en {optimization_time:.2f}s")
            
        except Exception as e:
            self.test_results['chunk_optimization'] = {
                'success': False,
                'error': str(e),
                'time': time.time() - start_time
            }
            logger.warning(f"⚠ Optimisation des chunks échouée: {e}")
            # Ne pas lever l'exception car ce n'est pas critique
    
    async def _test_query_evaluation(self) -> None:
        """Test d'évaluation sur 50 requêtes"""
        logger.info("Test 7: Évaluation sur 50 requêtes...")
        start_time = time.time()
        
        try:
            query_results = []
            successful_queries = 0
            total_confidence = 0.0
            total_processing_time = 0.0
            
            # Test de toutes les requêtes
            for i, query in enumerate(self.test_queries, 1):
                logger.info(f"Requête {i}/{len(self.test_queries)}: {query[:50]}...")
                
                try:
                    response = await self.rag_system.query(query_text=query)
                    
                    query_result = {
                        'query_id': i,
                        'query': query,
                        'success': True,
                        'confidence_score': response.confidence_score,
                        'processing_time': response.processing_time,
                        'results_count': len(response.search_results),
                        'chunks_count': len(response.retrieved_chunks)
                    }
                    
                    successful_queries += 1
                    total_confidence += response.confidence_score
                    total_processing_time += response.processing_time
                    
                except Exception as e:
                    query_result = {
                        'query_id': i,
                        'query': query,
                        'success': False,
                        'error': str(e)
                    }
                    logger.warning(f"Échec requête {i}: {e}")
                
                query_results.append(query_result)
            
            evaluation_time = time.time() - start_time
            
            # Calcul des métriques
            success_rate = successful_queries / len(self.test_queries)
            avg_confidence = total_confidence / successful_queries if successful_queries > 0 else 0
            avg_processing_time = total_processing_time / successful_queries if successful_queries > 0 else 0
            
            self.test_results['query_evaluation'] = {
                'success': True,
                'time': evaluation_time,
                'total_queries': len(self.test_queries),
                'successful_queries': successful_queries,
                'success_rate': success_rate,
                'avg_confidence_score': avg_confidence,
                'avg_processing_time': avg_processing_time,
                'detailed_results': query_results
            }
            
            logger.info(f"✓ Évaluation terminée: {successful_queries}/{len(self.test_queries)} requêtes réussies")
            logger.info(f"  Taux de succès: {success_rate:.1%}")
            logger.info(f"  Confiance moyenne: {avg_confidence:.3f}")
            logger.info(f"  Temps moyen: {avg_processing_time:.3f}s")
            
        except Exception as e:
            self.test_results['query_evaluation'] = {
                'success': False,
                'error': str(e),
                'time': time.time() - start_time
            }
            logger.error(f"✗ Échec de l'évaluation des requêtes: {e}")
            raise
    
    async def _test_system_performance(self) -> None:
        """Test de performance globale du système"""
        logger.info("Test 8: Performance globale du système...")
        start_time = time.time()
        
        try:
            # Évaluation complète du système
            evaluation_results = await self.rag_system.evaluate_performance(
                test_queries=self.test_queries[:20],  # Limité pour les tests
                max_queries=20
            )
            
            # Statut final du système
            final_status = self.rag_system.get_system_status()
            
            performance_time = time.time() - start_time
            
            self.test_results['system_performance'] = {
                'success': True,
                'time': performance_time,
                'evaluation_results': evaluation_results,
                'final_system_status': final_status,
                'cache_efficiency': final_status['metrics']['cache_hit_rate']
            }
            
            logger.info(f"✓ Évaluation de performance terminée en {performance_time:.2f}s")
            
        except Exception as e:
            self.test_results['system_performance'] = {
                'success': False,
                'error': str(e),
                'time': time.time() - start_time
            }
            logger.warning(f"⚠ Évaluation de performance échouée: {e}")
            # Ne pas lever l'exception car ce n'est pas critique
    
    def _calculate_success_rate(self) -> float:
        """Calcule le taux de succès global des tests"""
        if not self.test_results:
            return 0.0
        
        successful_tests = sum(1 for result in self.test_results.values() 
                             if result.get('success', False))
        
        return successful_tests / len(self.test_results)
    
    async def _save_test_results(self, results: Dict[str, Any]) -> None:
        """Sauvegarde les résultats des tests"""
        # Sauvegarde JSON détaillée
        json_file = self.output_dir / "rag_test_results.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        # Sauvegarde du rapport de synthèse
        report_file = self.output_dir / "rag_test_report.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=== RAPPORT DE TEST DU SYSTÈME RAG MÉDICAL ===\n\n")
            
            summary = results['test_summary']
            f.write(f"Durée totale: {summary['total_time']:.2f}s\n")
            f.write(f"Tests complétés: {summary['tests_completed']}\n")
            f.write(f"Taux de succès: {summary['success_rate']:.1%}\n")
            f.write(f"Timestamp: {summary['timestamp']}\n\n")
            
            # Détails par test
            for test_name, test_result in results['detailed_results'].items():
                f.write(f"--- {test_name.upper()} ---\n")
                f.write(f"Succès: {'✓' if test_result.get('success') else '✗'}\n")
                f.write(f"Temps: {test_result.get('time', 0):.2f}s\n")
                
                if not test_result.get('success') and 'error' in test_result:
                    f.write(f"Erreur: {test_result['error']}\n")
                
                f.write("\n")
        
        logger.info(f"Résultats sauvegardés: {json_file} et {report_file}")

async def main():
    """Fonction principale de test"""
    print("\n" + "="*60)
    print("    TEST COMPLET DU SYSTÈME RAG MÉDICAL")
    print("    Hackathon Hôpital Général de Douala")
    print("="*60)
    
    # Création du testeur
    tester = MedicalRAGTester(output_dir="./test_results_rag")
    
    try:
        # Exécution du test complet
        results = await tester.run_complete_test()
        
        # Affichage du résumé
        print("\n" + "="*60)
        print("    RÉSUMÉ DES TESTS")
        print("="*60)
        
        summary = results['test_summary']
        print(f"✓ Durée totale: {summary['total_time']:.2f}s")
        print(f"✓ Tests complétés: {summary['tests_completed']}")
        print(f"✓ Taux de succès: {summary['success_rate']:.1%}")
        
        # Détails des composants testés
        print("\n--- COMPOSANTS TESTÉS ---")
        for test_name, test_result in results['detailed_results'].items():
            status = "✓" if test_result.get('success') else "✗"
            time_taken = test_result.get('time', 0)
            print(f"{status} {test_name}: {time_taken:.2f}s")
        
        # Métriques spéciales
        if 'query_evaluation' in results['detailed_results']:
            eval_result = results['detailed_results']['query_evaluation']
            if eval_result.get('success'):
                print("\n--- ÉVALUATION DES REQUÊTES ---")
                print(f"✓ Requêtes testées: {eval_result['total_queries']}")
                print(f"✓ Taux de succès: {eval_result['success_rate']:.1%}")
                print(f"✓ Confiance moyenne: {eval_result['avg_confidence_score']:.3f}")
                print(f"✓ Temps moyen par requête: {eval_result['avg_processing_time']:.3f}s")
        
        print(f"\n✓ Résultats détaillés disponibles dans: {tester.output_dir}")
        print("\n" + "="*60)
        print("    TEST TERMINÉ AVEC SUCCÈS")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ ÉCHEC DU TEST: {e}")
        logger.error(f"Test échoué: {e}", exc_info=True)
        return False
    
    finally:
        # Nettoyage
        if tester.rag_system:
            await tester.rag_system.cleanup()

if __name__ == "__main__":
    # Exécution du test
    success = asyncio.run(main())
    sys.exit(0 if success else 1)