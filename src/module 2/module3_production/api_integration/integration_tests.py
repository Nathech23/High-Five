#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests d'Intégration Automatisés - Objectif 22
Module 3: Production Data & Knowledge - API Integration

Ce module implémente une suite complète de tests d'intégration automatisés
pour valider l'API, les intégrations HL7 FHIR, et l'ensemble du système.

Fonctionnalités:
- Tests d'intégration API REST
- Tests d'intégration HL7 FHIR
- Tests de sécurité et authentification
- Tests de performance et charge
- Tests de bout en bout (E2E)
- Rapports de tests détaillés
- Intégration CI/CD
"""

import logging
import json
import time
import asyncio
import pytest
import requests
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import statistics
import uuid

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestType(Enum):
    """Types de tests"""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PERFORMANCE = "performance"
    SECURITY = "security"
    FHIR = "fhir"

class TestStatus(Enum):
    """Statuts des tests"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"

class TestSeverity(Enum):
    """Niveaux de sévérité"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class TestCase:
    """Cas de test"""
    id: str
    name: str
    description: str
    test_type: TestType
    severity: TestSeverity
    tags: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    timeout_seconds: int = 30
    retry_count: int = 0
    expected_result: Any = None
    test_data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TestResult:
    """Résultat de test"""
    test_id: str
    test_name: str
    status: TestStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: int = 0
    error_message: Optional[str] = None
    actual_result: Any = None
    assertions: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TestSuite:
    """Suite de tests"""
    name: str
    description: str
    test_cases: List[TestCase] = field(default_factory=list)
    setup_hooks: List[callable] = field(default_factory=list)
    teardown_hooks: List[callable] = field(default_factory=list)
    parallel: bool = False
    max_workers: int = 5

@dataclass
class TestReport:
    """Rapport de tests"""
    suite_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_tests: int = 0
    success_rate: float = 0.0
    total_duration_ms: int = 0
    test_results: List[TestResult] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

class APITestClient:
    """Client de test pour l'API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.auth_token = None
        
        # Configuration par défaut
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Integration-Test-Client/1.0'
        })
        
        logger.info(f"APITestClient initialisé pour {self.base_url}")
    
    def authenticate(self, username: str, password: str) -> bool:
        """S'authentifier auprès de l'API"""
        try:
            response = self.session.post(
                f"{self.base_url}/auth/login",
                json={"username": username, "password": password},
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.auth_token = token_data.get('access_token')
                self.session.headers['Authorization'] = f"Bearer {self.auth_token}"
                logger.info(f"Authentification réussie pour {username}")
                return True
            else:
                logger.error(f"Échec d'authentification: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de l'authentification: {e}")
            return False
    
    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """Requête GET"""
        return self.session.get(f"{self.base_url}{endpoint}", **kwargs)
    
    def post(self, endpoint: str, **kwargs) -> requests.Response:
        """Requête POST"""
        return self.session.post(f"{self.base_url}{endpoint}", **kwargs)
    
    def put(self, endpoint: str, **kwargs) -> requests.Response:
        """Requête PUT"""
        return self.session.put(f"{self.base_url}{endpoint}", **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """Requête DELETE"""
        return self.session.delete(f"{self.base_url}{endpoint}", **kwargs)
    
    def health_check(self) -> bool:
        """Vérifier la santé de l'API"""
        try:
            response = self.get("/health", timeout=5)
            return response.status_code == 200
        except:
            return False

class TestAssertion:
    """Utilitaires d'assertion pour les tests"""
    
    @staticmethod
    def assert_status_code(response: requests.Response, expected: int) -> Dict[str, Any]:
        """Vérifier le code de statut"""
        success = response.status_code == expected
        return {
            'assertion': 'status_code',
            'expected': expected,
            'actual': response.status_code,
            'success': success,
            'message': f"Expected status {expected}, got {response.status_code}"
        }
    
    @staticmethod
    def assert_response_time(duration_ms: float, max_ms: float) -> Dict[str, Any]:
        """Vérifier le temps de réponse"""
        success = duration_ms <= max_ms
        return {
            'assertion': 'response_time',
            'expected': f"<= {max_ms}ms",
            'actual': f"{duration_ms:.1f}ms",
            'success': success,
            'message': f"Response time {duration_ms:.1f}ms {'within' if success else 'exceeds'} limit of {max_ms}ms"
        }
    
    @staticmethod
    def assert_json_structure(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
        """Vérifier la structure JSON"""
        missing_fields = [field for field in required_fields if field not in data]
        success = len(missing_fields) == 0
        return {
            'assertion': 'json_structure',
            'expected': required_fields,
            'actual': list(data.keys()),
            'success': success,
            'message': f"Missing fields: {missing_fields}" if missing_fields else "All required fields present"
        }
    
    @staticmethod
    def assert_contains(text: str, substring: str) -> Dict[str, Any]:
        """Vérifier qu'un texte contient une sous-chaîne"""
        success = substring in text
        return {
            'assertion': 'contains',
            'expected': f"Contains '{substring}'",
            'actual': f"Text: '{text[:100]}...'",
            'success': success,
            'message': f"Text {'contains' if success else 'does not contain'} '{substring}'"
        }
    
    @staticmethod
    def assert_equals(actual: Any, expected: Any) -> Dict[str, Any]:
        """Vérifier l'égalité"""
        success = actual == expected
        return {
            'assertion': 'equals',
            'expected': expected,
            'actual': actual,
            'success': success,
            'message': f"Values {'match' if success else 'do not match'}"
        }

class IntegrationTestRunner:
    """Exécuteur de tests d'intégration"""
    
    def __init__(self, api_client: APITestClient):
        self.api_client = api_client
        self.test_suites = {}
        self.test_results = []
        
        # Base de données pour les résultats
        self.db_path = Path("integration_tests.db")
        self._initialize_database()
        
        logger.info("IntegrationTestRunner initialisé")
    
    def _initialize_database(self):
        """Initialiser la base de données SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                suite_name TEXT NOT NULL,
                test_id TEXT NOT NULL,
                test_name TEXT NOT NULL,
                status TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                duration_ms INTEGER,
                error_message TEXT,
                assertions TEXT,
                metadata TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_test_suite(self, suite: TestSuite):
        """Ajouter une suite de tests"""
        self.test_suites[suite.name] = suite
        logger.info(f"Suite de tests ajoutée: {suite.name} ({len(suite.test_cases)} tests)")
    
    def run_test_case(self, test_case: TestCase) -> TestResult:
        """Exécuter un cas de test"""
        start_time = datetime.now()
        result = TestResult(
            test_id=test_case.id,
            test_name=test_case.name,
            status=TestStatus.RUNNING,
            start_time=start_time
        )
        
        try:
            logger.info(f"🧪 Exécution du test: {test_case.name}")
            
            # Exécuter le test selon son type
            if test_case.test_type == TestType.INTEGRATION:
                self._run_integration_test(test_case, result)
            elif test_case.test_type == TestType.FHIR:
                self._run_fhir_test(test_case, result)
            elif test_case.test_type == TestType.SECURITY:
                self._run_security_test(test_case, result)
            elif test_case.test_type == TestType.PERFORMANCE:
                self._run_performance_test(test_case, result)
            elif test_case.test_type == TestType.E2E:
                self._run_e2e_test(test_case, result)
            else:
                raise ValueError(f"Type de test non supporté: {test_case.test_type}")
            
            # Si aucune exception, le test a réussi
            if result.status == TestStatus.RUNNING:
                result.status = TestStatus.PASSED
            
        except Exception as e:
            logger.error(f"❌ Échec du test {test_case.name}: {e}")
            result.status = TestStatus.FAILED
            result.error_message = str(e)
        
        finally:
            result.end_time = datetime.now()
            result.duration_ms = int((result.end_time - result.start_time).total_seconds() * 1000)
        
        return result
    
    def _run_integration_test(self, test_case: TestCase, result: TestResult):
        """Exécuter un test d'intégration API"""
        test_data = test_case.test_data
        
        if test_case.id == "api_health_check":
            response = self.api_client.get("/health")
            
            # Assertions
            result.assertions.append(
                TestAssertion.assert_status_code(response, 200)
            )
            
            if response.status_code == 200:
                data = response.json()
                result.assertions.append(
                    TestAssertion.assert_json_structure(data, ['status', 'timestamp', 'version'])
                )
                result.assertions.append(
                    TestAssertion.assert_equals(data.get('status'), 'healthy')
                )
        
        elif test_case.id == "api_authentication":
            # Test d'authentification
            auth_success = self.api_client.authenticate(
                test_data.get('username', 'admin'),
                test_data.get('password', 'admin123')
            )
            
            result.assertions.append(
                TestAssertion.assert_equals(auth_success, True)
            )
            
            if auth_success:
                # Tester l'accès à un endpoint protégé
                response = self.api_client.get("/auth/me")
                result.assertions.append(
                    TestAssertion.assert_status_code(response, 200)
                )
        
        elif test_case.id == "api_search":
            # Test de recherche
            search_data = {
                "query": test_data.get('query', 'cardiologie'),
                "limit": test_data.get('limit', 10)
            }
            
            start_time = time.time()
            response = self.api_client.post("/search", json=search_data)
            duration_ms = (time.time() - start_time) * 1000
            
            result.assertions.append(
                TestAssertion.assert_status_code(response, 200)
            )
            result.assertions.append(
                TestAssertion.assert_response_time(duration_ms, 1000)  # Max 1s
            )
            
            if response.status_code == 200:
                data = response.json()
                result.assertions.append(
                    TestAssertion.assert_json_structure(data, ['success', 'data', 'message'])
                )
        
        elif test_case.id == "api_document_crud":
            # Test CRUD des documents
            doc_id = f"test_doc_{uuid.uuid4().hex[:8]}"
            
            # CREATE
            create_data = {
                "id": doc_id,
                "title": "Document de test",
                "content": "Contenu de test pour l'intégration",
                "category": "general",
                "type": "diagnostic",
                "author": "Test Author",
                "created_at": datetime.now().isoformat(),
                "tags": ["test", "integration"]
            }
            
            response = self.api_client.post("/documents", json=create_data)
            result.assertions.append(
                TestAssertion.assert_status_code(response, 200)
            )
            
            # READ
            response = self.api_client.get(f"/documents/{doc_id}")
            result.assertions.append(
                TestAssertion.assert_status_code(response, 200)
            )
            
            if response.status_code == 200:
                data = response.json()
                result.assertions.append(
                    TestAssertion.assert_equals(data['data']['id'], doc_id)
                )
        
        # Vérifier que toutes les assertions ont réussi
        failed_assertions = [a for a in result.assertions if not a['success']]
        if failed_assertions:
            raise AssertionError(f"{len(failed_assertions)} assertion(s) failed")
    
    def _run_fhir_test(self, test_case: TestCase, result: TestResult):
        """Exécuter un test FHIR"""
        test_data = test_case.test_data
        
        if test_case.id == "fhir_patient_read":
            patient_id = test_data.get('patient_id', 'test_patient_123')
            response = self.api_client.get(f"/fhir/Patient/{patient_id}")
            
            result.assertions.append(
                TestAssertion.assert_status_code(response, 200)
            )
            
            if response.status_code == 200:
                data = response.json()
                fhir_data = data.get('data', {})
                
                # Vérifier la structure FHIR
                result.assertions.append(
                    TestAssertion.assert_json_structure(fhir_data, ['resourceType', 'id', 'meta'])
                )
                result.assertions.append(
                    TestAssertion.assert_equals(fhir_data.get('resourceType'), 'Patient')
                )
                result.assertions.append(
                    TestAssertion.assert_equals(fhir_data.get('id'), patient_id)
                )
        
        elif test_case.id == "fhir_observation_read":
            observation_id = test_data.get('observation_id', 'test_obs_123')
            response = self.api_client.get(f"/fhir/Observation/{observation_id}")
            
            result.assertions.append(
                TestAssertion.assert_status_code(response, 200)
            )
            
            if response.status_code == 200:
                data = response.json()
                fhir_data = data.get('data', {})
                
                result.assertions.append(
                    TestAssertion.assert_equals(fhir_data.get('resourceType'), 'Observation')
                )
                result.assertions.append(
                    TestAssertion.assert_json_structure(fhir_data, ['status', 'subject', 'effectiveDateTime'])
                )
        
        # Vérifier les assertions
        failed_assertions = [a for a in result.assertions if not a['success']]
        if failed_assertions:
            raise AssertionError(f"{len(failed_assertions)} FHIR assertion(s) failed")
    
    def _run_security_test(self, test_case: TestCase, result: TestResult):
        """Exécuter un test de sécurité"""
        if test_case.id == "security_unauthorized_access":
            # Tenter d'accéder sans authentification
            temp_client = APITestClient(self.api_client.base_url)
            response = temp_client.get("/auth/me")
            
            result.assertions.append(
                TestAssertion.assert_status_code(response, 401)
            )
        
        elif test_case.id == "security_invalid_token":
            # Tester avec un token invalide
            temp_client = APITestClient(self.api_client.base_url)
            temp_client.session.headers['Authorization'] = "Bearer invalid_token_123"
            response = temp_client.get("/auth/me")
            
            result.assertions.append(
                TestAssertion.assert_status_code(response, 401)
            )
        
        elif test_case.id == "security_sql_injection":
            # Test d'injection SQL
            malicious_query = "'; DROP TABLE users; --"
            response = self.api_client.post("/search", json={"query": malicious_query})
            
            # L'API doit gérer gracieusement les tentatives d'injection
            result.assertions.append(
                TestAssertion.assert_status_code(response, 200)
            )
            
            # Vérifier que la réponse ne contient pas d'erreur SQL
            if response.status_code == 200:
                response_text = response.text.lower()
                sql_errors = ['sql', 'syntax error', 'mysql', 'postgresql']
                for error in sql_errors:
                    result.assertions.append({
                        'assertion': 'no_sql_error',
                        'expected': f"No '{error}' in response",
                        'actual': f"Response contains '{error}': {error in response_text}",
                        'success': error not in response_text,
                        'message': f"SQL injection test - no '{error}' leaked"
                    })
        
        # Vérifier les assertions
        failed_assertions = [a for a in result.assertions if not a['success']]
        if failed_assertions:
            raise AssertionError(f"{len(failed_assertions)} security assertion(s) failed")
    
    def _run_performance_test(self, test_case: TestCase, result: TestResult):
        """Exécuter un test de performance"""
        test_data = test_case.test_data
        
        if test_case.id == "performance_load_test":
            # Test de charge
            num_requests = test_data.get('num_requests', 50)
            concurrent_users = test_data.get('concurrent_users', 5)
            max_response_time = test_data.get('max_response_time_ms', 1000)
            
            response_times = []
            errors = 0
            
            def make_request():
                try:
                    start = time.time()
                    response = self.api_client.get("/health")
                    duration = (time.time() - start) * 1000
                    return duration, response.status_code == 200
                except:
                    return 0, False
            
            # Exécuter les requêtes en parallèle
            with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
                futures = [executor.submit(make_request) for _ in range(num_requests)]
                
                for future in as_completed(futures):
                    duration, success = future.result()
                    response_times.append(duration)
                    if not success:
                        errors += 1
            
            # Analyser les résultats
            avg_response_time = statistics.mean(response_times)
            max_response_time_actual = max(response_times)
            success_rate = ((num_requests - errors) / num_requests) * 100
            
            result.assertions.append(
                TestAssertion.assert_response_time(avg_response_time, max_response_time)
            )
            result.assertions.append({
                'assertion': 'success_rate',
                'expected': '>= 95%',
                'actual': f"{success_rate:.1f}%",
                'success': success_rate >= 95,
                'message': f"Success rate: {success_rate:.1f}%"
            })
            
            result.metadata.update({
                'num_requests': num_requests,
                'concurrent_users': concurrent_users,
                'avg_response_time_ms': avg_response_time,
                'max_response_time_ms': max_response_time_actual,
                'success_rate_percent': success_rate,
                'errors': errors
            })
        
        # Vérifier les assertions
        failed_assertions = [a for a in result.assertions if not a['success']]
        if failed_assertions:
            raise AssertionError(f"{len(failed_assertions)} performance assertion(s) failed")
    
    def _run_e2e_test(self, test_case: TestCase, result: TestResult):
        """Exécuter un test de bout en bout"""
        if test_case.id == "e2e_medical_workflow":
            # Workflow complet: authentification -> recherche -> consultation document -> FHIR
            
            # 1. Authentification
            auth_success = self.api_client.authenticate('doctor1', 'doctor123')
            result.assertions.append(
                TestAssertion.assert_equals(auth_success, True)
            )
            
            if not auth_success:
                raise AssertionError("Échec d'authentification")
            
            # 2. Recherche médicale
            search_response = self.api_client.post("/search", json={
                "query": "cardiologie",
                "category": "cardiologie",
                "limit": 5
            })
            
            result.assertions.append(
                TestAssertion.assert_status_code(search_response, 200)
            )
            
            # 3. Consultation d'un document
            doc_response = self.api_client.get("/documents/doc_001")
            result.assertions.append(
                TestAssertion.assert_status_code(doc_response, 200)
            )
            
            # 4. Accès FHIR
            fhir_response = self.api_client.get("/fhir/Patient/test_patient")
            result.assertions.append(
                TestAssertion.assert_status_code(fhir_response, 200)
            )
            
            # 5. Vérifier les métriques
            metrics_response = self.api_client.get("/metrics")
            result.assertions.append(
                TestAssertion.assert_status_code(metrics_response, 200)
            )
        
        # Vérifier les assertions
        failed_assertions = [a for a in result.assertions if not a['success']]
        if failed_assertions:
            raise AssertionError(f"{len(failed_assertions)} E2E assertion(s) failed")
    
    def run_test_suite(self, suite_name: str) -> TestReport:
        """Exécuter une suite de tests"""
        if suite_name not in self.test_suites:
            raise ValueError(f"Suite de tests non trouvée: {suite_name}")
        
        suite = self.test_suites[suite_name]
        report = TestReport(
            suite_name=suite_name,
            start_time=datetime.now()
        )
        
        logger.info(f"🚀 Exécution de la suite: {suite_name} ({len(suite.test_cases)} tests)")
        
        try:
            # Exécuter les hooks de setup
            for setup_hook in suite.setup_hooks:
                setup_hook()
            
            # Exécuter les tests
            if suite.parallel:
                # Exécution parallèle
                with ThreadPoolExecutor(max_workers=suite.max_workers) as executor:
                    futures = {
                        executor.submit(self.run_test_case, test_case): test_case
                        for test_case in suite.test_cases
                    }
                    
                    for future in as_completed(futures):
                        result = future.result()
                        report.test_results.append(result)
                        self._save_test_result(suite_name, result)
            else:
                # Exécution séquentielle
                for test_case in suite.test_cases:
                    result = self.run_test_case(test_case)
                    report.test_results.append(result)
                    self._save_test_result(suite_name, result)
            
            # Exécuter les hooks de teardown
            for teardown_hook in suite.teardown_hooks:
                teardown_hook()
        
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de la suite {suite_name}: {e}")
        
        finally:
            report.end_time = datetime.now()
            report.total_duration_ms = int((report.end_time - report.start_time).total_seconds() * 1000)
            
            # Calculer les statistiques
            report.total_tests = len(report.test_results)
            report.passed_tests = sum(1 for r in report.test_results if r.status == TestStatus.PASSED)
            report.failed_tests = sum(1 for r in report.test_results if r.status == TestStatus.FAILED)
            report.skipped_tests = sum(1 for r in report.test_results if r.status == TestStatus.SKIPPED)
            report.error_tests = sum(1 for r in report.test_results if r.status == TestStatus.ERROR)
            
            if report.total_tests > 0:
                report.success_rate = (report.passed_tests / report.total_tests) * 100
            
            # Résumé
            report.summary = {
                'total_tests': report.total_tests,
                'passed': report.passed_tests,
                'failed': report.failed_tests,
                'skipped': report.skipped_tests,
                'errors': report.error_tests,
                'success_rate_percent': report.success_rate,
                'duration_seconds': report.total_duration_ms / 1000,
                'avg_test_duration_ms': report.total_duration_ms / report.total_tests if report.total_tests > 0 else 0
            }
        
        logger.info(f"✅ Suite terminée: {suite_name} - {report.passed_tests}/{report.total_tests} tests réussis ({report.success_rate:.1f}%)")
        return report
    
    def _save_test_result(self, suite_name: str, result: TestResult):
        """Sauvegarder un résultat de test"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO test_runs 
            (suite_name, test_id, test_name, status, start_time, end_time, 
             duration_ms, error_message, assertions, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            suite_name,
            result.test_id,
            result.test_name,
            result.status.value,
            result.start_time.isoformat(),
            result.end_time.isoformat() if result.end_time else None,
            result.duration_ms,
            result.error_message,
            json.dumps(result.assertions),
            json.dumps(result.metadata)
        ))
        
        conn.commit()
        conn.close()
    
    def create_default_test_suites(self):
        """Créer les suites de tests par défaut"""
        
        # Suite d'intégration API
        api_suite = TestSuite(
            name="api_integration",
            description="Tests d'intégration de l'API REST",
            parallel=False
        )
        
        api_suite.test_cases = [
            TestCase(
                id="api_health_check",
                name="Vérification de santé de l'API",
                description="Vérifier que l'API répond correctement au health check",
                test_type=TestType.INTEGRATION,
                severity=TestSeverity.CRITICAL,
                tags=["api", "health"]
            ),
            TestCase(
                id="api_authentication",
                name="Authentification API",
                description="Tester l'authentification JWT",
                test_type=TestType.INTEGRATION,
                severity=TestSeverity.CRITICAL,
                tags=["api", "auth"],
                test_data={"username": "admin", "password": "admin123"}
            ),
            TestCase(
                id="api_search",
                name="Recherche médicale",
                description="Tester la fonctionnalité de recherche",
                test_type=TestType.INTEGRATION,
                severity=TestSeverity.HIGH,
                tags=["api", "search"],
                test_data={"query": "cardiologie", "limit": 10}
            ),
            TestCase(
                id="api_document_crud",
                name="CRUD des documents",
                description="Tester les opérations CRUD sur les documents",
                test_type=TestType.INTEGRATION,
                severity=TestSeverity.HIGH,
                tags=["api", "crud", "documents"]
            )
        ]
        
        self.add_test_suite(api_suite)
        
        # Suite FHIR
        fhir_suite = TestSuite(
            name="fhir_integration",
            description="Tests d'intégration HL7 FHIR",
            parallel=True,
            max_workers=3
        )
        
        fhir_suite.test_cases = [
            TestCase(
                id="fhir_patient_read",
                name="Lecture Patient FHIR",
                description="Tester la lecture d'une ressource Patient FHIR",
                test_type=TestType.FHIR,
                severity=TestSeverity.HIGH,
                tags=["fhir", "patient"],
                test_data={"patient_id": "test_patient_123"}
            ),
            TestCase(
                id="fhir_observation_read",
                name="Lecture Observation FHIR",
                description="Tester la lecture d'une ressource Observation FHIR",
                test_type=TestType.FHIR,
                severity=TestSeverity.MEDIUM,
                tags=["fhir", "observation"],
                test_data={"observation_id": "test_obs_123"}
            )
        ]
        
        self.add_test_suite(fhir_suite)
        
        # Suite de sécurité
        security_suite = TestSuite(
            name="security_tests",
            description="Tests de sécurité",
            parallel=False
        )
        
        security_suite.test_cases = [
            TestCase(
                id="security_unauthorized_access",
                name="Accès non autorisé",
                description="Vérifier que l'accès non autorisé est bloqué",
                test_type=TestType.SECURITY,
                severity=TestSeverity.CRITICAL,
                tags=["security", "auth"]
            ),
            TestCase(
                id="security_invalid_token",
                name="Token invalide",
                description="Vérifier le rejet des tokens invalides",
                test_type=TestType.SECURITY,
                severity=TestSeverity.HIGH,
                tags=["security", "token"]
            ),
            TestCase(
                id="security_sql_injection",
                name="Injection SQL",
                description="Tester la protection contre l'injection SQL",
                test_type=TestType.SECURITY,
                severity=TestSeverity.CRITICAL,
                tags=["security", "injection"]
            )
        ]
        
        self.add_test_suite(security_suite)
        
        # Suite de performance
        performance_suite = TestSuite(
            name="performance_tests",
            description="Tests de performance",
            parallel=False
        )
        
        performance_suite.test_cases = [
            TestCase(
                id="performance_load_test",
                name="Test de charge",
                description="Tester les performances sous charge",
                test_type=TestType.PERFORMANCE,
                severity=TestSeverity.HIGH,
                tags=["performance", "load"],
                test_data={
                    "num_requests": 50,
                    "concurrent_users": 5,
                    "max_response_time_ms": 1000
                },
                timeout_seconds=60
            )
        ]
        
        self.add_test_suite(performance_suite)
        
        # Suite E2E
        e2e_suite = TestSuite(
            name="e2e_tests",
            description="Tests de bout en bout",
            parallel=False
        )
        
        e2e_suite.test_cases = [
            TestCase(
                id="e2e_medical_workflow",
                name="Workflow médical complet",
                description="Tester un workflow médical complet",
                test_type=TestType.E2E,
                severity=TestSeverity.CRITICAL,
                tags=["e2e", "workflow", "medical"],
                timeout_seconds=120
            )
        ]
        
        self.add_test_suite(e2e_suite)
        
        logger.info(f"Créé {len(self.test_suites)} suites de tests par défaut")
    
    def run_all_suites(self) -> Dict[str, TestReport]:
        """Exécuter toutes les suites de tests"""
        reports = {}
        
        for suite_name in self.test_suites.keys():
            try:
                report = self.run_test_suite(suite_name)
                reports[suite_name] = report
            except Exception as e:
                logger.error(f"Erreur lors de l'exécution de la suite {suite_name}: {e}")
        
        return reports
    
    def generate_html_report(self, reports: Dict[str, TestReport]) -> str:
        """Générer un rapport HTML"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Rapport de Tests d'Intégration</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f0f0f0; padding: 20px; border-radius: 5px; }
        .suite { margin: 20px 0; border: 1px solid #ddd; border-radius: 5px; }
        .suite-header { background: #e9e9e9; padding: 15px; font-weight: bold; }
        .test-result { padding: 10px; border-bottom: 1px solid #eee; }
        .passed { background: #d4edda; }
        .failed { background: #f8d7da; }
        .skipped { background: #fff3cd; }
        .assertion { margin: 5px 0; padding: 5px; font-size: 0.9em; }
        .assertion.success { background: #d1ecf1; }
        .assertion.failure { background: #f5c6cb; }
    </style>
</head>
<body>
        """
        
        # En-tête
        total_tests = sum(r.total_tests for r in reports.values())
        total_passed = sum(r.passed_tests for r in reports.values())
        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        html += f"""
    <div class="header">
        <h1>Rapport de Tests d'Intégration</h1>
        <p>Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Total: {total_tests} tests | Réussis: {total_passed} | Taux de succès: {overall_success_rate:.1f}%</p>
    </div>
        """
        
        # Suites de tests
        for suite_name, report in reports.items():
            status_class = "passed" if report.success_rate >= 100 else "failed" if report.success_rate < 80 else "skipped"
            
            html += f"""
    <div class="suite">
        <div class="suite-header {status_class}">
            {suite_name} - {report.passed_tests}/{report.total_tests} tests réussis ({report.success_rate:.1f}%)
            - Durée: {report.total_duration_ms/1000:.1f}s
        </div>
            """
            
            # Tests individuels
            for result in report.test_results:
                result_class = result.status.value
                html += f"""
        <div class="test-result {result_class}">
            <h4>{result.test_name} ({result.status.value})</h4>
            <p>Durée: {result.duration_ms}ms</p>
            """
                
                if result.error_message:
                    html += f"<p><strong>Erreur:</strong> {result.error_message}</p>"
                
                # Assertions
                if result.assertions:
                    html += "<div><strong>Assertions:</strong>"
                    for assertion in result.assertions:
                        assertion_class = "success" if assertion['success'] else "failure"
                        html += f"""
                <div class="assertion {assertion_class}">
                    {assertion['assertion']}: {assertion['message']}
                </div>
                        """
                    html += "</div>"
                
                html += "</div>"
            
            html += "</div>"
        
        html += """
</body>
</html>
        """
        
        return html

def main():
    """Fonction principale de démonstration"""
    print("🚀 Tests d'Intégration Automatisés - Objectif 22")
    print("Suite complète de tests API, FHIR, sécurité et performance")
    print("=" * 70)
    
    # Initialiser le client de test
    print("\n🔧 Initialisation du client de test...")
    api_client = APITestClient("http://localhost:8000")
    
    # Vérifier que l'API est disponible
    print("\n🏥 Vérification de la disponibilité de l'API...")
    if not api_client.health_check():
        print("❌ API non disponible. Assurez-vous que le serveur API est démarré.")
        print("💡 Démarrez le serveur avec: python api_server.py")
        return
    
    print("✅ API disponible")
    
    # Initialiser le runner de tests
    print("\n🧪 Initialisation du runner de tests...")
    test_runner = IntegrationTestRunner(api_client)
    
    # Créer les suites de tests par défaut
    test_runner.create_default_test_suites()
    
    print(f"✅ {len(test_runner.test_suites)} suites de tests créées")
    
    # Exécuter toutes les suites
    print("\n🚀 Exécution de toutes les suites de tests...")
    start_time = time.time()
    
    reports = test_runner.run_all_suites()
    
    execution_time = time.time() - start_time
    
    # Afficher les résultats
    print(f"\n📊 Résultats des tests (exécution: {execution_time:.1f}s):")
    print("=" * 70)
    
    total_tests = 0
    total_passed = 0
    total_failed = 0
    
    for suite_name, report in reports.items():
        status_icon = "✅" if report.success_rate >= 100 else "⚠️" if report.success_rate >= 80 else "❌"
        
        print(f"\n{status_icon} {suite_name}:")
        print(f"  Tests: {report.passed_tests}/{report.total_tests} réussis ({report.success_rate:.1f}%)")
        print(f"  Durée: {report.total_duration_ms/1000:.1f}s")
        
        if report.failed_tests > 0:
            print(f"  ❌ Échecs: {report.failed_tests}")
            
            # Afficher les tests échoués
            failed_tests = [r for r in report.test_results if r.status == TestStatus.FAILED]
            for failed_test in failed_tests[:3]:  # Limiter à 3
                print(f"    - {failed_test.test_name}: {failed_test.error_message}")
        
        total_tests += report.total_tests
        total_passed += report.passed_tests
        total_failed += report.failed_tests
    
    # Résumé global
    overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\n📈 Résumé global:")
    print(f"  Total des tests: {total_tests}")
    print(f"  Tests réussis: {total_passed}")
    print(f"  Tests échoués: {total_failed}")
    print(f"  Taux de succès: {overall_success_rate:.1f}%")
    
    # Générer le rapport HTML
    print("\n📄 Génération du rapport HTML...")
    html_report = test_runner.generate_html_report(reports)
    
    report_file = Path("integration_test_report.html")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(html_report)
    
    print(f"✅ Rapport HTML généré: {report_file}")
    
    # Évaluation de l'objectif
    print("\n🎯 Évaluation de l'objectif 22:")
    
    success_criteria = {
        'api_tests_implemented': 'api_integration' in reports,
        'fhir_tests_implemented': 'fhir_integration' in reports,
        'security_tests_implemented': 'security_tests' in reports,
        'performance_tests_implemented': 'performance_tests' in reports,
        'e2e_tests_implemented': 'e2e_tests' in reports,
        'overall_success_rate_acceptable': overall_success_rate >= 80,
        'test_report_generated': report_file.exists(),
        'multiple_test_types': len(reports) >= 4
    }
    
    all_success = all(success_criteria.values())
    
    print(f"\n✅ Critères d'évaluation:")
    for criterion, met in success_criteria.items():
        status_icon = "✅" if met else "❌"
        print(f"  {status_icon} {criterion.replace('_', ' ').title()}")
    
    objective_score = sum(success_criteria.values()) / len(success_criteria) * 100
    print(f"\n📊 Score de l'objectif 22: {objective_score:.1f}%")
    
    if all_success:
        print("🎉 OBJECTIF 22 ATTEINT: Tests d'intégration automatisés opérationnels!")
        readiness_level = "PRODUCTION"
    elif objective_score >= 75:
        print("⚠️ OBJECTIF 22 PARTIELLEMENT ATTEINT: Quelques améliorations nécessaires")
        readiness_level = "STAGING"
    else:
        print("❌ OBJECTIF 22 NON ATTEINT: Tests d'intégration incomplets")
        readiness_level = "DEVELOPMENT"
    
    final_report = {
        'objective_22_status': 'ATTEINT' if all_success else 'PARTIEL' if objective_score >= 75 else 'NON_ATTEINT',
        'score_percent': objective_score,
        'readiness_level': readiness_level,
        'total_tests_executed': total_tests,
        'success_rate_percent': overall_success_rate,
        'test_suites': {
            suite_name: {
                'tests': report.total_tests,
                'passed': report.passed_tests,
                'success_rate': report.success_rate
            }
            for suite_name, report in reports.items()
        },
        'execution_time_seconds': execution_time,
        'report_file': str(report_file)
    }
    
    print(f"\n📋 Niveau de préparation: {readiness_level}")
    print(f"Prêt pour la production: {'✅' if readiness_level == 'PRODUCTION' else '❌'}")
    
    return final_report

if __name__ == "__main__":
    main()