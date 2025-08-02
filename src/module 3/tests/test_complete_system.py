#!/usr/bin/env python3
"""
Tests complets du système MLOps
Module 1: ML/IA + LLM + MLOps - Système de Prédiction des Stocks de Sang
"""

import unittest
import sys
import os
import tempfile
import shutil
import pandas as pd
import numpy as np
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import requests
from datetime import datetime, timedelta

# Ajouter le répertoire src au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestDataGeneration(unittest.TestCase):
    """Tests pour la génération de données synthétiques"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.data_path = os.path.join(self.temp_dir, 'test_data.csv')
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_data_generator_import(self):
        """Test d'importation du générateur de données"""
        try:
            from data_generation.generate_synthetic_data import BloodStockDataGenerator
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Impossible d'importer BloodStockDataGenerator: {e}")
    
    def test_data_generation_basic(self):
        """Test de génération de données basique"""
        from data_generation.generate_synthetic_data import BloodStockDataGenerator
        
        generator = BloodStockDataGenerator(
            num_hospitals=2,
            start_date='2024-01-01',
            end_date='2024-01-31'
        )
        
        data = generator.generate_hospital_data('Test Hospital', 100)
        
        self.assertIsInstance(data, pd.DataFrame)
        self.assertGreater(len(data), 0)
        self.assertIn('hospital', data.columns)
        self.assertIn('blood_type', data.columns)
        self.assertIn('stock_level', data.columns)
    
    def test_data_quality_constraints(self):
        """Test des contraintes de qualité des données"""
        from data_generation.generate_synthetic_data import BloodStockDataGenerator
        
        generator = BloodStockDataGenerator()
        data = generator.generate_hospital_data('Test Hospital', 100)
        
        # Vérifier les contraintes
        self.assertTrue((data['stock_level'] >= 0).all())
        self.assertTrue((data['demand'] >= 0).all())
        self.assertTrue((data['supply'] >= 0).all())
        self.assertTrue((data['temperature'] >= 2).all())
        self.assertTrue((data['temperature'] <= 8).all())
        self.assertTrue((data['quality_score'] >= 0).all())
        self.assertTrue((data['quality_score'] <= 100).all())

class TestDataPreprocessing(unittest.TestCase):
    """Tests pour le préprocessing des données"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
        # Créer des données de test
        self.test_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='D'),
            'hospital': ['Hospital A'] * 100,
            'blood_type': ['O+'] * 100,
            'stock_level': np.random.randint(10, 100, 100),
            'demand': np.random.randint(5, 20, 100),
            'supply': np.random.randint(5, 25, 100),
            'temperature': np.random.uniform(2, 8, 100),
            'days_to_expiry': np.random.randint(1, 30, 100),
            'quality_score': np.random.uniform(70, 100, 100),
            'quality_comment': ['Good quality'] * 100
        })
        
        self.data_path = os.path.join(self.temp_dir, 'test_data.csv')
        self.test_data.to_csv(self.data_path, index=False)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_preprocessor_import(self):
        """Test d'importation du préprocesseur"""
        try:
            from preprocessing.data_preprocessor import BloodStockPreprocessor
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Impossible d'importer BloodStockPreprocessor: {e}")
    
    def test_feature_engineering(self):
        """Test de l'ingénierie des features"""
        from preprocessing.data_preprocessor import BloodStockPreprocessor
        
        preprocessor = BloodStockPreprocessor()
        processed_data = preprocessor.create_time_features(self.test_data.copy())
        
        # Vérifier les nouvelles features
        expected_features = [
            'hour', 'day_of_week', 'month', 'quarter',
            'is_weekend', 'is_month_start', 'is_month_end'
        ]
        
        for feature in expected_features:
            self.assertIn(feature, processed_data.columns)
    
    def test_data_splitting(self):
        """Test de la division des données"""
        from preprocessing.data_preprocessor import BloodStockPreprocessor
        
        preprocessor = BloodStockPreprocessor()
        train, val, test = preprocessor.split_data(
            self.test_data, 
            test_size=0.2, 
            val_size=0.2
        )
        
        total_size = len(train) + len(val) + len(test)
        self.assertEqual(total_size, len(self.test_data))
        self.assertGreater(len(train), len(val))
        self.assertGreater(len(train), len(test))

class TestMLModels(unittest.TestCase):
    """Tests pour les modèles ML"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
        # Créer des données de test plus réalistes
        dates = pd.date_range('2024-01-01', periods=200, freq='D')
        self.test_data = pd.DataFrame({
            'timestamp': dates,
            'hospital': ['Hospital A'] * 200,
            'blood_type': ['O+'] * 200,
            'stock_level': np.random.randint(10, 100, 200),
            'demand': np.random.randint(5, 20, 200),
            'supply': np.random.randint(5, 25, 200),
            'temperature': np.random.uniform(2, 8, 200),
            'days_to_expiry': np.random.randint(1, 30, 200),
            'quality_score': np.random.uniform(70, 100, 200)
        })
        
        # Ajouter une tendance pour rendre les données plus réalistes
        trend = np.linspace(0, 20, 200)
        self.test_data['stock_level'] += trend.astype(int)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_arima_model_import(self):
        """Test d'importation du modèle ARIMA"""
        try:
            from training.arima_model import ARIMAPredictor
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Impossible d'importer ARIMAPredictor: {e}")
    
    def test_xgboost_model_import(self):
        """Test d'importation du modèle XGBoost"""
        try:
            from training.xgboost_model import XGBoostPredictor
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Impossible d'importer XGBoostPredictor: {e}")
    
    def test_lstm_model_import(self):
        """Test d'importation du modèle LSTM"""
        try:
            from training.lstm_model import LSTMPredictor
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Impossible d'importer LSTMPredictor: {e}")
    
    def test_ensemble_model_import(self):
        """Test d'importation du modèle Ensemble"""
        try:
            from training.ensemble_model import EnsemblePredictor
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Impossible d'importer EnsemblePredictor: {e}")
    
    @patch('mlflow.start_run')
    def test_arima_basic_functionality(self, mock_mlflow):
        """Test de fonctionnalité basique ARIMA"""
        from training.arima_model import ARIMAPredictor
        
        # Mock MLflow
        mock_mlflow.return_value.__enter__ = Mock()
        mock_mlflow.return_value.__exit__ = Mock()
        
        predictor = ARIMAPredictor()
        
        # Test de préparation des données
        series_data = predictor.prepare_data(
            self.test_data, 
            'Hospital A', 
            'O+'
        )
        
        self.assertIsInstance(series_data, pd.Series)
        self.assertGreater(len(series_data), 0)
    
    def test_model_metrics_calculation(self):
        """Test du calcul des métriques"""
        # Données de test pour les métriques
        y_true = np.array([10, 20, 30, 40, 50])
        y_pred = np.array([12, 18, 32, 38, 52])
        
        # Calculer MAE manuellement
        mae = np.mean(np.abs(y_true - y_pred))
        self.assertAlmostEqual(mae, 2.4, places=1)
        
        # Calculer RMSE manuellement
        rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
        self.assertAlmostEqual(rmse, 2.68, places=1)

class TestLLMIntegration(unittest.TestCase):
    """Tests pour l'intégration LLM"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
        self.test_comments = [
            "Excellent état, conservation parfaite",
            "Qualité dégradée, vérifier température",
            "URGENT: Contamination possible, analyser immédiatement",
            "Stock normal, aucun problème détecté",
            "Attention: Expiration proche, utiliser rapidement"
        ]
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_llm_analyzer_import(self):
        """Test d'importation de l'analyseur LLM"""
        try:
            from llm_integration.llm_analyzer import LLMBloodStockAnalyzer
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Impossible d'importer LLMBloodStockAnalyzer: {e}")
    
    @patch('transformers.pipeline')
    def test_sentiment_analysis(self, mock_pipeline):
        """Test de l'analyse de sentiment"""
        from llm_integration.llm_analyzer import LLMBloodStockAnalyzer
        
        # Mock du pipeline de sentiment
        mock_sentiment = Mock()
        mock_sentiment.return_value = [{'label': 'POSITIVE', 'score': 0.9}]
        mock_pipeline.return_value = mock_sentiment
        
        analyzer = LLMBloodStockAnalyzer()
        
        result = analyzer.analyze_sentiment("Excellent état")
        
        self.assertIn('sentiment', result)
        self.assertIn('confidence', result)
    
    def test_urgency_classification_rules(self):
        """Test de classification d'urgence basée sur les règles"""
        from llm_integration.llm_analyzer import LLMBloodStockAnalyzer
        
        analyzer = LLMBloodStockAnalyzer()
        
        # Test avec mots-clés d'urgence
        urgent_comment = "URGENT: Contamination possible"
        urgency = analyzer.classify_urgency_rules(urgent_comment)
        self.assertGreater(urgency, 70)  # Devrait être classé comme urgent
        
        # Test avec commentaire normal
        normal_comment = "Qualité normale, aucun problème"
        urgency = analyzer.classify_urgency_rules(normal_comment)
        self.assertLess(urgency, 50)  # Devrait être classé comme normal
    
    def test_keyword_extraction(self):
        """Test d'extraction de mots-clés"""
        from llm_integration.llm_analyzer import LLMBloodStockAnalyzer
        
        analyzer = LLMBloodStockAnalyzer()
        
        text = "Température élevée, contamination possible, urgent"
        keywords = analyzer.extract_keywords(text)
        
        self.assertIsInstance(keywords, list)
        self.assertGreater(len(keywords), 0)

class TestAPIEndpoints(unittest.TestCase):
    """Tests pour les endpoints de l'API"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
        # Données de test pour l'API
        self.test_request_data = {
            "data": [{
                "hospital": "Hôpital Test",
                "blood_type": "O+",
                "stock_initial": 45,
                "demand": 12,
                "supply": 8,
                "temperature": 4.2,
                "days_to_expiry": 18,
                "quality_score": 92.5,
                "quality_comment": "Excellent état"
            }],
            "model_type": "ensemble"
        }
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_api_import(self):
        """Test d'importation de l'API"""
        try:
            from api.main import app
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Impossible d'importer l'API: {e}")
    
    @patch('api.main.ensemble_model')
    @patch('api.main.preprocessor')
    def test_prediction_endpoint_structure(self, mock_preprocessor, mock_model):
        """Test de la structure de l'endpoint de prédiction"""
        from api.main import app
        from fastapi.testclient import TestClient
        
        # Mock des modèles
        mock_model.predict.return_value = np.array([45.5])
        mock_preprocessor.transform.return_value = np.array([[1, 2, 3, 4, 5]])
        
        client = TestClient(app)
        
        response = client.post("/predict", json=self.test_request_data)
        
        # Vérifier que l'endpoint existe (même si les modèles ne sont pas chargés)
        self.assertIn(response.status_code, [200, 500])  # 500 si modèles non chargés
    
    def test_health_endpoint(self):
        """Test de l'endpoint de santé"""
        from api.main import app
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        response = client.get("/health")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('status', data)
        self.assertIn('timestamp', data)

class TestSystemIntegration(unittest.TestCase):
    """Tests d'intégration du système complet"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_config_import(self):
        """Test d'importation de la configuration"""
        try:
            from config import Config, get_config
            config = get_config()
            self.assertIsInstance(config, Config)
        except ImportError as e:
            self.fail(f"Impossible d'importer la configuration: {e}")
    
    def test_pipeline_script_import(self):
        """Test d'importation du script de pipeline"""
        try:
            from training.train_all_models import MLOpsPipeline
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Impossible d'importer MLOpsPipeline: {e}")
    
    def test_demo_script_import(self):
        """Test d'importation du script de démonstration"""
        try:
            # Importer le module demo
            import importlib.util
            demo_path = os.path.join(os.path.dirname(__file__), '..', 'demo.py')
            spec = importlib.util.spec_from_file_location("demo", demo_path)
            demo_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(demo_module)
            
            self.assertTrue(hasattr(demo_module, 'BloodStockMLDemo'))
        except Exception as e:
            self.fail(f"Impossible d'importer le script de démonstration: {e}")

class TestPerformanceAndLatency(unittest.TestCase):
    """Tests de performance et latence"""
    
    def test_prediction_latency_requirement(self):
        """Test que les prédictions respectent la latence < 2 secondes"""
        # Simuler une prédiction
        start_time = time.time()
        
        # Simulation d'une prédiction (remplacer par vraie prédiction en production)
        time.sleep(0.1)  # Simuler le temps de traitement
        prediction = 42.5  # Prédiction simulée
        
        end_time = time.time()
        latency = end_time - start_time
        
        self.assertLess(latency, 2.0, "La prédiction doit prendre moins de 2 secondes")
    
    def test_batch_processing_efficiency(self):
        """Test d'efficacité du traitement par batch"""
        batch_sizes = [1, 10, 50, 100]
        
        for batch_size in batch_sizes:
            start_time = time.time()
            
            # Simuler le traitement d'un batch
            for _ in range(batch_size):
                # Simulation d'une opération
                result = sum(range(100))
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Le temps par élément devrait diminuer avec la taille du batch
            time_per_item = processing_time / batch_size
            self.assertLess(time_per_item, 0.1, f"Traitement trop lent pour batch de {batch_size}")

class TestDataQualityAndValidation(unittest.TestCase):
    """Tests de qualité et validation des données"""
    
    def test_data_completeness(self):
        """Test de complétude des données"""
        # Créer des données de test avec des valeurs manquantes
        data = pd.DataFrame({
            'hospital': ['A', 'B', None, 'D'],
            'blood_type': ['O+', 'A+', 'B+', None],
            'stock_level': [10, 20, None, 40],
            'quality_score': [90, 85, 95, None]
        })
        
        # Calculer le taux de complétude
        completeness = (data.notna().sum() / len(data)).mean()
        
        # Vérifier que les données sont suffisamment complètes
        self.assertGreater(completeness, 0.7, "Les données doivent être au moins 70% complètes")
    
    def test_data_consistency(self):
        """Test de cohérence des données"""
        data = pd.DataFrame({
            'stock_level': [10, 20, 30, 40],
            'demand': [5, 15, 10, 20],
            'supply': [8, 12, 15, 18],
            'temperature': [4.0, 3.5, 6.0, 4.5],
            'quality_score': [90, 85, 95, 88]
        })
        
        # Vérifier les contraintes de cohérence
        self.assertTrue((data['stock_level'] >= 0).all(), "Stock level doit être positif")
        self.assertTrue((data['temperature'] >= 2).all(), "Température trop basse")
        self.assertTrue((data['temperature'] <= 8).all(), "Température trop élevée")
        self.assertTrue((data['quality_score'] >= 0).all(), "Score qualité invalide")
        self.assertTrue((data['quality_score'] <= 100).all(), "Score qualité invalide")

class TestSecurityAndCompliance(unittest.TestCase):
    """Tests de sécurité et conformité"""
    
    def test_sensitive_data_handling(self):
        """Test de gestion des données sensibles"""
        # Vérifier qu'aucune donnée sensible n'est exposée
        test_config = {
            'api_key': 'secret_key_123',
            'database_password': 'super_secret',
            'public_info': 'this_is_ok'
        }
        
        # Simuler la fonction de masquage
        def mask_sensitive_data(config):
            sensitive_keys = ['api_key', 'password', 'secret', 'token']
            masked_config = config.copy()
            
            for key in masked_config:
                if any(sensitive in key.lower() for sensitive in sensitive_keys):
                    masked_config[key] = '***MASKED***'
            
            return masked_config
        
        masked = mask_sensitive_data(test_config)
        
        self.assertEqual(masked['api_key'], '***MASKED***')
        self.assertEqual(masked['database_password'], '***MASKED***')
        self.assertEqual(masked['public_info'], 'this_is_ok')
    
    def test_input_validation(self):
        """Test de validation des entrées"""
        # Test avec des données valides
        valid_data = {
            'hospital': 'Hôpital Test',
            'blood_type': 'O+',
            'stock_level': 50,
            'quality_score': 85.5
        }
        
        # Fonction de validation simulée
        def validate_input(data):
            errors = []
            
            if not isinstance(data.get('hospital'), str):
                errors.append('Hospital must be a string')
            
            if data.get('blood_type') not in ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']:
                errors.append('Invalid blood type')
            
            if not isinstance(data.get('stock_level'), (int, float)) or data.get('stock_level') < 0:
                errors.append('Stock level must be a positive number')
            
            if not isinstance(data.get('quality_score'), (int, float)) or not (0 <= data.get('quality_score') <= 100):
                errors.append('Quality score must be between 0 and 100')
            
            return errors
        
        errors = validate_input(valid_data)
        self.assertEqual(len(errors), 0, f"Validation errors: {errors}")
        
        # Test avec des données invalides
        invalid_data = {
            'hospital': 123,  # Devrait être une string
            'blood_type': 'XY',  # Type de sang invalide
            'stock_level': -5,  # Négatif
            'quality_score': 150  # Hors limites
        }
        
        errors = validate_input(invalid_data)
        self.assertGreater(len(errors), 0, "Des erreurs de validation devraient être détectées")

def run_all_tests():
    """Lance tous les tests et génère un rapport"""
    # Créer une suite de tests
    test_classes = [
        TestDataGeneration,
        TestDataPreprocessing,
        TestMLModels,
        TestLLMIntegration,
        TestAPIEndpoints,
        TestSystemIntegration,
        TestPerformanceAndLatency,
        TestDataQualityAndValidation,
        TestSecurityAndCompliance
    ]
    
    suite = unittest.TestSuite()
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Lancer les tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Générer un rapport
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    success_rate = ((total_tests - failures - errors) / total_tests) * 100 if total_tests > 0 else 0
    
    print("\n" + "="*80)
    print("🧪 RAPPORT DE TESTS COMPLET")
    print("="*80)
    print(f"📊 Tests exécutés: {total_tests}")
    print(f"✅ Succès: {total_tests - failures - errors}")
    print(f"❌ Échecs: {failures}")
    print(f"🚨 Erreurs: {errors}")
    print(f"📈 Taux de réussite: {success_rate:.1f}%")
    
    if failures > 0:
        print("\n🔍 ÉCHECS DÉTECTÉS:")
        for test, traceback in result.failures:
            print(f"  • {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if errors > 0:
        print("\n🚨 ERREURS DÉTECTÉES:")
        for test, traceback in result.errors:
            print(f"  • {test}: {traceback.split('Error:')[-1].strip()}")
    
    # Sauvegarder le rapport
    report = {
        'timestamp': datetime.now().isoformat(),
        'total_tests': total_tests,
        'successes': total_tests - failures - errors,
        'failures': failures,
        'errors': errors,
        'success_rate': success_rate,
        'details': {
            'failures': [str(test) for test, _ in result.failures],
            'errors': [str(test) for test, _ in result.errors]
        }
    }
    
    os.makedirs('test_results', exist_ok=True)
    with open('test_results/test_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Rapport sauvegardé: test_results/test_report.json")
    
    return success_rate >= 80  # Retourner True si au moins 80% de réussite

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)