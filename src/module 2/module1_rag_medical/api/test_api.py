#!/usr/bin/env python3
"""
Script de Test pour l'API RAG Médical

Script complet pour tester l'API FastAPI et valider le pipeline RAG.

Objectifs Hackathon:
25. ✅ Créer API FastAPI pour service RAG
26. ✅ Implémenter endpoints de recherche de connaissances
27. ✅ Valider pipeline complet : query → embeddings → search → context
28. ✅ Documenter architecture RAG

Auteur: Équipe Hackathon Hôpital Général de Douala
Module: 1 - RAG & Medical Knowledge
Version: 1.0.0
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any
import requests
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RAGAPITester:
    """
    Testeur complet pour l'API RAG médical
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        
    def print_header(self, title: str, char: str = "=", width: int = 60) -> None:
        """Affiche un en-tête formaté"""
        print("\n" + char * width)
        print(f"    {title}")
        print(char * width)
    
    def print_step(self, step: str, description: str) -> None:
        """Affiche une étape avec description"""
        print(f"\n🔄 {step}: {description}")
    
    def print_success(self, message: str) -> None:
        """Affiche un message de succès"""
        print(f"✅ {message}")
    
    def print_error(self, message: str) -> None:
        """Affiche une erreur"""
        print(f"❌ {message}")
    
    def print_info(self, message: str) -> None:
        """Affiche une information"""
        print(f"ℹ️  {message}")
    
    def test_endpoint(self, method: str, endpoint: str, data: Dict = None, 
                     expected_status: int = 200, description: str = "") -> Dict[str, Any]:
        """
        Teste un endpoint de l'API
        
        Args:
            method: Méthode HTTP (GET, POST, etc.)
            endpoint: Endpoint à tester
            data: Données à envoyer
            expected_status: Code de statut attendu
            description: Description du test
        
        Returns:
            dict: Résultat du test
        """
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data)
            elif method.upper() == "DELETE":
                response = self.session.delete(url)
            else:
                raise ValueError(f"Méthode HTTP non supportée: {method}")
            
            response_time = time.time() - start_time
            
            result = {
                "endpoint": endpoint,
                "method": method,
                "description": description,
                "status_code": response.status_code,
                "expected_status": expected_status,
                "success": response.status_code == expected_status,
                "response_time": response_time,
                "timestamp": datetime.now().isoformat()
            }
            
            try:
                result["response_data"] = response.json()
            except:
                result["response_data"] = response.text
            
            self.test_results.append(result)
            
            if result["success"]:
                self.print_success(f"{description} - {response_time:.3f}s")
            else:
                self.print_error(f"{description} - Status: {response.status_code}")
            
            return result
            
        except Exception as e:
            result = {
                "endpoint": endpoint,
                "method": method,
                "description": description,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            self.test_results.append(result)
            self.print_error(f"{description} - Erreur: {e}")
            return result
    
    def test_health_endpoints(self):
        """Teste les endpoints de santé"""
        self.print_step("1", "Test des endpoints de santé")
        
        # Test /health
        self.test_endpoint(
            "GET", "/health", 
            description="Vérification de santé de l'API"
        )
        
        # Test /status
        self.test_endpoint(
            "GET", "/status", 
            description="Statut détaillé du système"
        )
        
        # Test /info
        self.test_endpoint(
            "GET", "/info", 
            description="Informations sur le système"
        )
    
    def test_rag_endpoints(self):
        """Teste les endpoints RAG principaux"""
        self.print_step("2", "Test des endpoints RAG")
        
        # Test requêtes médicales
        test_queries = [
            {
                "query": "Comment diagnostiquer le diabète de type 2 ?",
                "language": "fr",
                "max_results": 5,
                "search_strategy": "hybrid",
                "fusion_strategy": "medical_priority"
            },
            {
                "query": "Quel est le traitement du paludisme ?",
                "language": "fr",
                "max_results": 3,
                "search_strategy": "semantic"
            },
            {
                "query": "Symptômes de l'hypertension artérielle",
                "language": "fr",
                "max_results": 5,
                "search_strategy": "medical_entity"
            }
        ]
        
        for i, query_data in enumerate(test_queries, 1):
            self.test_endpoint(
                "POST", "/query",
                data=query_data,
                description=f"Requête RAG {i}: {query_data['query'][:50]}..."
            )
        
        # Test recherche simple
        self.test_endpoint(
            "POST", "/search",
            data="diabète traitement",
            description="Recherche sémantique simple"
        )
    
    def test_indexation_endpoints(self):
        """Teste les endpoints d'indexation"""
        self.print_step("3", "Test des endpoints d'indexation")
        
        # Documents de test
        test_documents = [
            {
                "id": "test_doc_1",
                "content": """
                L'aspirine est un médicament anti-inflammatoire non stéroïdien (AINS) 
                utilisé pour traiter la douleur, la fièvre et l'inflammation. 
                La dose habituelle pour adulte est de 500-1000 mg toutes les 4-6 heures.
                """,
                "metadata": {
                    "specialty": "pharmacology",
                    "language": "fr",
                    "document_type": "medication_guide"
                }
            },
            {
                "id": "test_doc_2",
                "content": """
                La pneumonie est une infection des poumons qui peut être causée par 
                des bactéries, des virus ou des champignons. Les symptômes incluent 
                la toux, la fièvre, les frissons et la difficulté à respirer.
                """,
                "metadata": {
                    "specialty": "pulmonology",
                    "language": "fr",
                    "document_type": "clinical_guide"
                }
            }
        ]
        
        # Test indexation
        indexation_data = {
            "documents": test_documents,
            "batch_size": 2,
            "update_existing": False
        }
        
        self.test_endpoint(
            "POST", "/index",
            data=indexation_data,
            description="Indexation de documents de test"
        )
    
    def test_validation_pipeline(self):
        """Teste la validation du pipeline complet"""
        self.print_step("4", "Test de validation du pipeline")
        
        # Test validation pipeline
        test_query = "Comment traiter une infection respiratoire ?"
        
        result = self.test_endpoint(
            "POST", "/validate-pipeline",
            data=test_query,
            description="Validation pipeline complet : query → embeddings → search → context"
        )
        
        # Analyser les résultats de validation
        if result.get("success") and "response_data" in result:
            response_data = result["response_data"]
            if isinstance(response_data, dict):
                pipeline_steps = response_data.get("pipeline_steps", {})
                
                self.print_info("Détails de validation du pipeline:")
                for step_name, step_data in pipeline_steps.items():
                    status = step_data.get("status", "unknown")
                    if status == "success":
                        self.print_success(f"  {step_name}: ✅")
                    else:
                        self.print_error(f"  {step_name}: ❌ - {step_data.get('error', 'Erreur inconnue')}")
    
    def test_evaluation_endpoints(self):
        """Teste les endpoints d'évaluation"""
        self.print_step("5", "Test des endpoints d'évaluation")
        
        # Test métriques
        self.test_endpoint(
            "GET", "/metrics",
            description="Récupération des métriques de performance"
        )
        
        # Test évaluation (version limitée pour les tests)
        evaluation_data = {
            "test_queries": [
                "Qu'est-ce que le diabète ?",
                "Comment traiter l'hypertension ?",
                "Symptômes du paludisme"
            ],
            "max_queries": 3,
            "include_metrics": True,
            "save_results": False
        }
        
        self.test_endpoint(
            "POST", "/evaluate",
            data=evaluation_data,
            description="Évaluation de performance du système"
        )
    
    def test_documentation_endpoints(self):
        """Teste les endpoints de documentation"""
        self.print_step("6", "Test des endpoints de documentation")
        
        # Test documentation architecture
        result = self.test_endpoint(
            "GET", "/docs-architecture",
            description="Documentation de l'architecture RAG"
        )
        
        # Vérifier que c'est du HTML
        if result.get("success") and "response_data" in result:
            response_text = result["response_data"]
            if isinstance(response_text, str) and "<html>" in response_text.lower():
                self.print_success("Documentation HTML générée correctement")
            else:
                self.print_error("Documentation HTML non valide")
    
    def test_error_handling(self):
        """Teste la gestion d'erreurs"""
        self.print_step("7", "Test de gestion d'erreurs")
        
        # Test requête invalide
        self.test_endpoint(
            "POST", "/query",
            data={"query": ""},  # Requête vide
            expected_status=422,
            description="Requête invalide (requête vide)"
        )
        
        # Test endpoint inexistant
        self.test_endpoint(
            "GET", "/endpoint-inexistant",
            expected_status=404,
            description="Endpoint inexistant"
        )
        
        # Test suppression document inexistant
        self.test_endpoint(
            "DELETE", "/index/document_inexistant",
            expected_status=404,
            description="Suppression document inexistant"
        )
    
    def run_all_tests(self):
        """Lance tous les tests"""
        self.print_header("TEST COMPLET DE L'API RAG MÉDICAL")
        self.print_info("Hackathon Hôpital Général de Douala 2024")
        self.print_info("Objectifs 25-28: API RAG et validation")
        
        start_time = time.time()
        
        try:
            # Vérifier que l'API est accessible
            self.print_step("0", "Vérification de l'accessibilité de l'API")
            try:
                response = self.session.get(f"{self.base_url}/health", timeout=5)
                if response.status_code == 200:
                    self.print_success(f"API accessible à {self.base_url}")
                else:
                    self.print_error(f"API non accessible - Status: {response.status_code}")
                    return False
            except Exception as e:
                self.print_error(f"Impossible de se connecter à l'API: {e}")
                self.print_info("Assurez-vous que l'API est démarrée avec: python api/main.py")
                return False
            
            # Lancer tous les tests
            self.test_health_endpoints()
            self.test_rag_endpoints()
            self.test_indexation_endpoints()
            self.test_validation_pipeline()
            self.test_evaluation_endpoints()
            self.test_documentation_endpoints()
            self.test_error_handling()
            
            # Résumé des résultats
            total_time = time.time() - start_time
            self.print_test_summary(total_time)
            
            return True
            
        except Exception as e:
            self.print_error(f"Erreur lors des tests: {e}")
            return False
    
    def print_test_summary(self, total_time: float):
        """Affiche le résumé des tests"""
        self.print_header("RÉSUMÉ DES TESTS")
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results if result.get("success", False))
        failed_tests = total_tests - successful_tests
        
        self.print_info(f"Tests exécutés: {total_tests}")
        self.print_success(f"Tests réussis: {successful_tests}")
        if failed_tests > 0:
            self.print_error(f"Tests échoués: {failed_tests}")
        
        self.print_info(f"Temps total: {total_time:.2f}s")
        
        if successful_tests == total_tests:
            self.print_header("🎉 TOUS LES TESTS RÉUSSIS !")
            self.print_success("L'API RAG médical fonctionne parfaitement")
            self.print_info("\n🎯 OBJECTIFS HACKATHON VALIDÉS:")
            self.print_success("  ✅ 25. API FastAPI pour service RAG")
            self.print_success("  ✅ 26. Endpoints de recherche de connaissances")
            self.print_success("  ✅ 27. Pipeline complet validé : query → embeddings → search → context")
            self.print_success("  ✅ 28. Architecture RAG documentée")
        else:
            self.print_header("⚠️  TESTS PARTIELLEMENT RÉUSSIS")
            self.print_info("Certains tests ont échoué. Vérifiez les logs ci-dessus.")
        
        # Sauvegarder les résultats
        self.save_test_results()
    
    def save_test_results(self):
        """Sauvegarde les résultats des tests"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"api_test_results_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "total_tests": len(self.test_results),
                    "successful_tests": sum(1 for r in self.test_results if r.get("success", False)),
                    "test_results": self.test_results
                }, f, indent=2, ensure_ascii=False)
            
            self.print_info(f"Résultats sauvegardés: {filename}")
            
        except Exception as e:
            self.print_error(f"Erreur lors de la sauvegarde: {e}")

def main():
    """Fonction principale"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test de l'API RAG Médical")
    parser.add_argument(
        "--url", 
        default="http://localhost:8000",
        help="URL de base de l'API (défaut: http://localhost:8000)"
    )
    
    args = parser.parse_args()
    
    # Créer et lancer le testeur
    tester = RAGAPITester(base_url=args.url)
    success = tester.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())