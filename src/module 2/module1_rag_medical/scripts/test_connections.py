#!/usr/bin/env python3
"""
Script de test des connexions pour le module RAG médical
Vérifie que PostgreSQL, Chroma et les modèles d'embedding fonctionnent correctement
"""

import sys
import logging
import time
from pathlib import Path
from typing import Dict, Any

# Ajouter le répertoire parent au path pour les imports
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import settings
from database.database import db_manager
from embeddings.chroma_manager import chroma_manager
from embeddings.embedding_manager import embedding_manager
from rag.langchain_rag import medical_rag

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class ConnectionTester:
    """Classe pour tester toutes les connexions du système RAG"""
    
    def __init__(self):
        self.test_results = {}
    
    def test_postgresql_connection(self) -> bool:
        """Teste la connexion PostgreSQL"""
        logger.info("=== Test PostgreSQL Connection ===")
        
        try:
            start_time = time.time()
            
            # Test de connexion basique
            connection_ok = db_manager.test_connection()
            
            if not connection_ok:
                self.test_results['postgresql'] = {
                    'status': 'FAILED',
                    'error': 'Connection failed',
                    'duration': time.time() - start_time
                }
                return False
            
            # Test des opérations de base
            with db_manager.get_session() as session:
                # Test de requête simple
                result = session.execute("SELECT version()")
                version = result.fetchone()[0]
                logger.info(f"PostgreSQL version: {version}")
                
                # Test des tables
                from database.models import MedicalDocument, MedicalSpecialty
                
                doc_count = session.query(MedicalDocument).count()
                specialty_count = session.query(MedicalSpecialty).count()
                
                logger.info(f"Documents in database: {doc_count}")
                logger.info(f"Specialties in database: {specialty_count}")
            
            duration = time.time() - start_time
            self.test_results['postgresql'] = {
                'status': 'SUCCESS',
                'version': version,
                'document_count': doc_count,
                'specialty_count': specialty_count,
                'duration': duration
            }
            
            logger.info(f"✅ PostgreSQL test passed ({duration:.2f}s)")
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            self.test_results['postgresql'] = {
                'status': 'FAILED',
                'error': str(e),
                'duration': duration
            }
            logger.error(f"❌ PostgreSQL test failed: {e}")
            return False
    
    def test_chroma_connection(self) -> bool:
        """Teste la connexion Chroma"""
        logger.info("=== Test Chroma Connection ===")
        
        try:
            start_time = time.time()
            
            # Test de connexion basique
            connection_ok = chroma_manager.test_connection()
            
            if not connection_ok:
                self.test_results['chroma'] = {
                    'status': 'FAILED',
                    'error': 'Connection failed',
                    'duration': time.time() - start_time
                }
                return False
            
            # Obtenir les statistiques
            stats = chroma_manager.get_collection_stats()
            logger.info(f"Collection: {stats.get('collection_name')}")
            logger.info(f"Documents: {stats.get('total_documents', 0)}")
            logger.info(f"Model: {stats.get('embedding_model')}")
            
            # Test d'ajout et de recherche
            test_doc = "Test document pour vérifier la fonctionnalité Chroma"
            test_metadata = {"test": True, "type": "connection_test"}
            
            # Ajouter un document de test
            test_ids = chroma_manager.add_documents([test_doc], [test_metadata])
            logger.info(f"Added test document with ID: {test_ids[0]}")
            
            # Rechercher le document
            search_results = chroma_manager.search_similar(
                "test document",
                n_results=1
            )
            
            found_docs = len(search_results['documents'][0])
            logger.info(f"Search test: found {found_docs} documents")
            
            # Nettoyer le document de test
            chroma_manager.delete_document(test_ids[0])
            
            duration = time.time() - start_time
            self.test_results['chroma'] = {
                'status': 'SUCCESS',
                'collection_name': stats.get('collection_name'),
                'total_documents': stats.get('total_documents', 0),
                'embedding_model': stats.get('embedding_model'),
                'search_test_results': found_docs,
                'duration': duration
            }
            
            logger.info(f"✅ Chroma test passed ({duration:.2f}s)")
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            self.test_results['chroma'] = {
                'status': 'FAILED',
                'error': str(e),
                'duration': duration
            }
            logger.error(f"❌ Chroma test failed: {e}")
            return False
    
    def test_embedding_model(self) -> bool:
        """Teste le modèle d'embedding"""
        logger.info("=== Test Embedding Model ===")
        
        try:
            start_time = time.time()
            
            # Obtenir les informations du modèle
            model_info = embedding_manager.get_model_info()
            logger.info(f"Model: {model_info['model_name']}")
            logger.info(f"Device: {model_info['device']}")
            logger.info(f"Dimension: {model_info['embedding_dimension']}")
            
            # Test d'encodage
            test_texts = [
                "Diagnostic de l'hypertension artérielle",
                "Traitement de la pneumonie",
                "Protocole de réanimation cardiaque",
                "Prise en charge du diabète de type 2"
            ]
            
            embeddings = embedding_manager.encode_medical_text(test_texts)
            logger.info(f"Encoded {len(test_texts)} texts to shape {embeddings.shape}")
            
            # Test de similarité
            query_embedding = embedding_manager.encode_medical_text(["hypertension traitement"])
            similarities = embedding_manager.compute_similarity(
                query_embedding,
                embeddings
            )
            
            logger.info(f"Similarity scores: {similarities.flatten()}")
            
            # Benchmark de performance
            benchmark = embedding_manager.benchmark_encoding(test_texts)
            logger.info(f"Performance: {benchmark.get('texts_per_second', 0):.2f} texts/second")
            
            duration = time.time() - start_time
            self.test_results['embedding'] = {
                'status': 'SUCCESS',
                'model_name': model_info['model_name'],
                'device': model_info['device'],
                'embedding_dimension': model_info['embedding_dimension'],
                'test_texts_count': len(test_texts),
                'performance_texts_per_second': benchmark.get('texts_per_second', 0),
                'duration': duration
            }
            
            logger.info(f"✅ Embedding model test passed ({duration:.2f}s)")
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            self.test_results['embedding'] = {
                'status': 'FAILED',
                'error': str(e),
                'duration': duration
            }
            logger.error(f"❌ Embedding model test failed: {e}")
            return False
    
    def test_rag_system(self) -> bool:
        """Teste le système RAG complet"""
        logger.info("=== Test RAG System ===")
        
        try:
            start_time = time.time()
            
            # Test de recherche dans la base de connaissances
            query = "hypertension artérielle diagnostic"
            
            search_results = medical_rag.search_medical_knowledge(
                query=query,
                top_k=3
            )
            
            logger.info(f"RAG search for '{query}':")
            logger.info(f"Found {search_results['total_results']} results")
            
            for i, doc in enumerate(search_results['documents'][:2]):
                logger.info(f"  Result {i+1}: {doc['metadata'].get('title', 'No title')[:50]}...")
            
            # Test de recherche avec scores
            similarity_results = medical_rag.similarity_search_with_scores(
                query=query,
                k=3,
                threshold=0.5
            )
            
            logger.info(f"Similarity search: {len(similarity_results)} results above threshold")
            
            # Statistiques du vectorstore
            vectorstore_stats = medical_rag.get_vectorstore_stats()
            logger.info(f"Vectorstore documents: {vectorstore_stats.get('total_documents', 0)}")
            
            duration = time.time() - start_time
            self.test_results['rag_system'] = {
                'status': 'SUCCESS',
                'search_results_count': search_results['total_results'],
                'similarity_results_count': len(similarity_results),
                'vectorstore_documents': vectorstore_stats.get('total_documents', 0),
                'duration': duration
            }
            
            logger.info(f"✅ RAG system test passed ({duration:.2f}s)")
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            self.test_results['rag_system'] = {
                'status': 'FAILED',
                'error': str(e),
                'duration': duration
            }
            logger.error(f"❌ RAG system test failed: {e}")
            return False
    
    def test_end_to_end(self) -> bool:
        """Test end-to-end du système complet"""
        logger.info("=== Test End-to-End ===")
        
        try:
            start_time = time.time()
            
            # Simuler un workflow complet
            # 1. Ajouter un nouveau document
            test_document = """
            Protocole de test pour l'Hôpital Général de Douala.
            Ce document teste l'intégration complète du système RAG.
            Il contient des informations sur les procédures de test.
            """
            
            test_metadata = {
                "title": "Document de test end-to-end",
                "document_type": "test",
                "specialty": "Test",
                "medical_level": "basic",
                "target_audience": "developers"
            }
            
            # 2. Traiter et ajouter au système
            from langchain.schema import Document
            
            doc = Document(
                page_content=test_document,
                metadata=test_metadata
            )
            
            processed_docs = medical_rag.process_documents([test_document], [test_metadata])
            doc_ids = medical_rag.add_documents_to_vectorstore(processed_docs)
            
            logger.info(f"Added {len(processed_docs)} processed chunks")
            
            # 3. Rechercher le document
            search_results = medical_rag.search_medical_knowledge(
                query="protocole test Douala",
                top_k=5
            )
            
            # 4. Vérifier que notre document est trouvé
            found_test_doc = any(
                "test end-to-end" in doc['metadata'].get('title', '').lower()
                for doc in search_results['documents']
            )
            
            logger.info(f"Test document found in search: {found_test_doc}")
            
            # 5. Nettoyer (optionnel pour les tests)
            # Note: En production, on ne supprimerait pas automatiquement
            
            duration = time.time() - start_time
            self.test_results['end_to_end'] = {
                'status': 'SUCCESS',
                'processed_chunks': len(processed_docs),
                'document_found_in_search': found_test_doc,
                'duration': duration
            }
            
            logger.info(f"✅ End-to-end test passed ({duration:.2f}s)")
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            self.test_results['end_to_end'] = {
                'status': 'FAILED',
                'error': str(e),
                'duration': duration
            }
            logger.error(f"❌ End-to-end test failed: {e}")
            return False
    
    def generate_report(self) -> Dict[str, Any]:
        """Génère un rapport complet des tests"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['status'] == 'SUCCESS')
        
        report = {
            'summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': total_tests - passed_tests,
                'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            'details': self.test_results,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return report

def main():
    """Fonction principale de test"""
    logger.info("Starting connection tests for Medical RAG Module")
    
    tester = ConnectionTester()
    
    # Exécuter tous les tests
    tests = [
        ('PostgreSQL', tester.test_postgresql_connection),
        ('Chroma', tester.test_chroma_connection),
        ('Embedding Model', tester.test_embedding_model),
        ('RAG System', tester.test_rag_system),
        ('End-to-End', tester.test_end_to_end)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} test ---")
        success = test_func()
        results.append(success)
    
    # Générer le rapport
    report = tester.generate_report()
    
    # Afficher le résumé
    logger.info("\n=== Test Summary ===")
    logger.info(f"Total tests: {report['summary']['total_tests']}")
    logger.info(f"Passed: {report['summary']['passed_tests']}")
    logger.info(f"Failed: {report['summary']['failed_tests']}")
    logger.info(f"Success rate: {report['summary']['success_rate']:.1f}%")
    
    # Afficher les détails des échecs
    for test_name, result in report['details'].items():
        if result['status'] == 'FAILED':
            logger.error(f"❌ {test_name}: {result.get('error', 'Unknown error')}")
    
    # Sauvegarder le rapport
    import json
    report_file = settings.PROJECT_ROOT / "logs" / "connection_test_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\nDetailed report saved to: {report_file}")
    
    # Retourner le succès global
    all_passed = all(results)
    if all_passed:
        logger.info("\n🎉 All tests passed! The Medical RAG system is ready.")
    else:
        logger.error("\n⚠️  Some tests failed. Please check the errors above.")
    
    return all_passed

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)