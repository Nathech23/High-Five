#!/usr/bin/env python3
"""
Script principal pour l'entraînement de tous les modèles ML
Module 1: MLOps - Système de Prédiction des Stocks de Sang
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import logging
import argparse
import mlflow
import warnings
warnings.filterwarnings('ignore')

# Ajouter le chemin du projet
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Imports des modules
from data_generation.generate_synthetic_data import BloodStockDataGenerator
from preprocessing.data_preprocessor import BloodStockPreprocessor
from training.arima_model import ARIMAPredictor
from training.xgboost_model import XGBoostPredictor
from training.lstm_model import LSTMPredictor
from training.ensemble_model import EnsemblePredictor
from llm_integration.llm_analyzer import LLMBloodStockAnalyzer

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('training.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MLOpsPipeline:
    """Pipeline MLOps complet pour l'entraînement des modèles"""
    
    def __init__(self, config: dict = None):
        self.config = config or self.get_default_config()
        self.results = {}
        
        # Configuration MLflow
        mlflow.set_tracking_uri(self.config.get('mlflow_uri', 'file:./mlruns'))
        mlflow.set_experiment("blood_stock_mlops_pipeline")
    
    def get_default_config(self) -> dict:
        """Configuration par défaut du pipeline"""
        return {
            'data': {
                'n_records': 12000,
                'start_date': '2022-01-01',
                'end_date': '2024-01-01',
                'test_size': 0.2,
                'val_size': 0.1
            },
            'models': {
                'arima': {
                    'enabled': True,
                    'max_p': 5,
                    'max_q': 5
                },
                'xgboost': {
                    'enabled': True,
                    'optimize': True,
                    'n_trials': 50
                },
                'lstm': {
                    'enabled': True,
                    'sequence_length': 30,
                    'epochs': 50,
                    'batch_size': 32,
                    'architecture': 'standard'
                },
                'ensemble': {
                    'enabled': True,
                    'methods': ['weighted_average', 'stacking', 'voting']
                }
            },
            'llm': {
                'enabled': True,
                'use_local_models': True,
                'sample_size': 1000
            },
            'mlflow_uri': 'file:./mlruns',
            'output_dir': 'models'
        }
    
    def step_1_generate_data(self) -> pd.DataFrame:
        """Étape 1: Génération des données synthétiques"""
        logger.info("=== ÉTAPE 1: GÉNÉRATION DES DONNÉES ===")
        
        with mlflow.start_run(run_name="data_generation", nested=True):
            generator = BloodStockDataGenerator()
            
            # Génération des données
            df = generator.generate_time_series_data(
                start_date=self.config['data']['start_date'],
                end_date=self.config['data']['end_date'],
                n_records=self.config['data']['n_records']
            )
            
            # Ajout des facteurs externes
            df = generator.add_external_factors(df)
            
            # Sauvegarde
            generator.save_data(df, 'data/synthetic')
            
            # Log des métriques
            mlflow.log_metrics({
                'total_records': len(df),
                'hospitals': df['hospital'].nunique(),
                'blood_types': df['blood_type'].nunique(),
                'date_range_days': (pd.to_datetime(df['timestamp'].max()) - pd.to_datetime(df['timestamp'].min())).days
            })
            
            logger.info(f"Données générées: {len(df)} enregistrements")
            self.results['data_generation'] = {
                'records': len(df),
                'hospitals': df['hospital'].nunique(),
                'blood_types': df['blood_type'].nunique()
            }
            
            return df
    
    def step_2_preprocess_data(self, df: pd.DataFrame) -> tuple:
        """Étape 2: Préprocessing des données"""
        logger.info("=== ÉTAPE 2: PRÉPROCESSING DES DONNÉES ===")
        
        with mlflow.start_run(run_name="data_preprocessing", nested=True):
            preprocessor = BloodStockPreprocessor()
            
            # Préparation des features
            df_processed = preprocessor.prepare_features(df, fit=True)
            
            # Division des données
            train_df, val_df, test_df = preprocessor.split_data(
                df_processed,
                test_size=self.config['data']['test_size'],
                val_size=self.config['data']['val_size']
            )
            
            # Sauvegarde du préprocesseur
            preprocessor.save_preprocessor(f"{self.config['output_dir']}/preprocessor")
            
            # Sauvegarde des données préprocessées
            os.makedirs('data/processed', exist_ok=True)
            train_df.to_csv('data/processed/train.csv', index=False)
            val_df.to_csv('data/processed/val.csv', index=False)
            test_df.to_csv('data/processed/test.csv', index=False)
            
            # Log des métriques
            mlflow.log_metrics({
                'train_size': len(train_df),
                'val_size': len(val_df),
                'test_size': len(test_df),
                'feature_count': len(preprocessor.feature_columns)
            })
            
            logger.info(f"Données préprocessées - Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")
            self.results['preprocessing'] = {
                'train_size': len(train_df),
                'val_size': len(val_df),
                'test_size': len(test_df),
                'features': len(preprocessor.feature_columns)
            }
            
            return train_df, val_df, test_df, preprocessor
    
    def step_3_train_arima(self, train_df: pd.DataFrame, val_df: pd.DataFrame) -> dict:
        """Étape 3: Entraînement du modèle ARIMA"""
        if not self.config['models']['arima']['enabled']:
            logger.info("ARIMA désactivé")
            return {}
        
        logger.info("=== ÉTAPE 3: ENTRAÎNEMENT ARIMA ===")
        
        try:
            arima_predictor = ARIMAPredictor()
            training_results = arima_predictor.train(train_df)
            
            # Évaluation
            if len(val_df) > 0:
                eval_results = arima_predictor.evaluate_model(val_df)
                training_results['evaluation'] = eval_results
            
            # Sauvegarde
            arima_predictor.save_models(f"{self.config['output_dir']}/arima")
            
            logger.info("ARIMA entraîné avec succès")
            self.results['arima'] = {
                'models_trained': len(training_results),
                'status': 'success'
            }
            
            return training_results
            
        except Exception as e:
            logger.error(f"Erreur ARIMA: {str(e)}")
            self.results['arima'] = {'status': 'failed', 'error': str(e)}
            return {}
    
    def step_4_train_xgboost(self, train_df: pd.DataFrame, val_df: pd.DataFrame, 
                            test_df: pd.DataFrame, preprocessor) -> dict:
        """Étape 4: Entraînement du modèle XGBoost"""
        if not self.config['models']['xgboost']['enabled']:
            logger.info("XGBoost désactivé")
            return {}
        
        logger.info("=== ÉTAPE 4: ENTRAÎNEMENT XGBOOST ===")
        
        try:
            xgb_predictor = XGBoostPredictor()
            
            # Préparer les données
            X_train, y_train, feature_names = xgb_predictor.prepare_features(train_df, preprocessor.feature_columns)
            X_val, y_val, _ = xgb_predictor.prepare_features(val_df, preprocessor.feature_columns)
            X_test, y_test, _ = xgb_predictor.prepare_features(test_df, preprocessor.feature_columns)
            
            # Entraînement
            results = xgb_predictor.train(
                X_train, y_train, X_val, y_val, feature_names,
                optimize=self.config['models']['xgboost']['optimize']
            )
            
            # Évaluation sur test
            test_metrics = xgb_predictor.evaluate(X_test, y_test)
            results['test_metrics'] = test_metrics
            
            # Sauvegarde
            xgb_predictor.save_model(f"{self.config['output_dir']}/xgboost")
            
            logger.info("XGBoost entraîné avec succès")
            self.results['xgboost'] = {
                'train_mae': results['train_metrics']['mae'],
                'val_mae': results['val_metrics']['mae'],
                'test_mae': test_metrics['mae'],
                'status': 'success'
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Erreur XGBoost: {str(e)}")
            self.results['xgboost'] = {'status': 'failed', 'error': str(e)}
            return {}
    
    def step_5_train_lstm(self, train_df: pd.DataFrame, val_df: pd.DataFrame, test_df: pd.DataFrame) -> dict:
        """Étape 5: Entraînement du modèle LSTM"""
        if not self.config['models']['lstm']['enabled']:
            logger.info("LSTM désactivé")
            return {}
        
        logger.info("=== ÉTAPE 5: ENTRAÎNEMENT LSTM ===")
        
        try:
            lstm_config = self.config['models']['lstm']
            lstm_predictor = LSTMPredictor(sequence_length=lstm_config['sequence_length'])
            
            # Préparer les données par série
            train_series = lstm_predictor.prepare_data_by_series(train_df)
            val_series = lstm_predictor.prepare_data_by_series(val_df)
            test_series = lstm_predictor.prepare_data_by_series(test_df)
            
            # Combiner les séries
            X_train, y_train, _ = lstm_predictor.combine_series_data(train_series)
            X_val, y_val, _ = lstm_predictor.combine_series_data(val_series)
            X_test, y_test, _ = lstm_predictor.combine_series_data(test_series)
            
            if len(X_train) == 0:
                logger.warning("Pas assez de données pour LSTM")
                self.results['lstm'] = {'status': 'skipped', 'reason': 'insufficient_data'}
                return {}
            
            # Entraînement
            results = lstm_predictor.train(
                X_train, y_train, X_val, y_val,
                architecture=lstm_config['architecture'],
                epochs=lstm_config['epochs'],
                batch_size=lstm_config['batch_size']
            )
            
            # Évaluation sur test
            if len(X_test) > 0:
                test_metrics = lstm_predictor.evaluate(X_test, y_test)
                results['test_metrics'] = test_metrics
            
            # Sauvegarde
            lstm_predictor.save_model(f"{self.config['output_dir']}/lstm")
            
            logger.info("LSTM entraîné avec succès")
            self.results['lstm'] = {
                'train_mae': results['train_metrics']['mae'],
                'val_mae': results['val_metrics']['mae'],
                'status': 'success'
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Erreur LSTM: {str(e)}")
            self.results['lstm'] = {'status': 'failed', 'error': str(e)}
            return {}
    
    def step_6_train_ensemble(self, train_df: pd.DataFrame, val_df: pd.DataFrame, 
                             test_df: pd.DataFrame, preprocessor) -> dict:
        """Étape 6: Entraînement du modèle d'ensemble"""
        if not self.config['models']['ensemble']['enabled']:
            logger.info("Ensemble désactivé")
            return {}
        
        logger.info("=== ÉTAPE 6: ENTRAÎNEMENT ENSEMBLE ===")
        
        try:
            ensemble = EnsemblePredictor()
            
            # Charger les modèles individuels
            if not ensemble.load_individual_models(self.config['output_dir']):
                logger.warning("Aucun modèle individuel disponible pour l'ensemble")
                self.results['ensemble'] = {'status': 'skipped', 'reason': 'no_individual_models'}
                return {}
            
            # Tester différentes méthodes
            methods = self.config['models']['ensemble']['methods']
            best_method = None
            best_score = float('inf')
            
            for method in methods:
                try:
                    logger.info(f"Test méthode ensemble: {method}")
                    results = ensemble.train_ensemble(train_df, val_df, preprocessor.feature_columns, method)
                    score = results['ensemble_metrics']['mae']
                    
                    if score < best_score:
                        best_score = score
                        best_method = method
                        
                except Exception as e:
                    logger.warning(f"Erreur avec méthode {method}: {str(e)}")
            
            if best_method:
                # Entraîner avec la meilleure méthode
                final_results = ensemble.train_ensemble(train_df, val_df, preprocessor.feature_columns, best_method)
                
                # Évaluation sur test
                test_results = ensemble.evaluate(test_df, preprocessor.feature_columns)
                final_results['test_results'] = test_results
                
                # Sauvegarde
                ensemble.save_ensemble(f"{self.config['output_dir']}/ensemble")
                
                logger.info(f"Ensemble entraîné avec succès (méthode: {best_method})")
                self.results['ensemble'] = {
                    'method': best_method,
                    'val_mae': final_results['ensemble_metrics']['mae'],
                    'test_mae': test_results['ensemble']['mae'],
                    'status': 'success'
                }
                
                return final_results
            else:
                logger.error("Aucune méthode d'ensemble n'a fonctionné")
                self.results['ensemble'] = {'status': 'failed', 'error': 'no_working_method'}
                return {}
            
        except Exception as e:
            logger.error(f"Erreur Ensemble: {str(e)}")
            self.results['ensemble'] = {'status': 'failed', 'error': str(e)}
            return {}
    
    def step_7_llm_analysis(self, df: pd.DataFrame) -> dict:
        """Étape 7: Analyse LLM"""
        if not self.config['llm']['enabled']:
            logger.info("Analyse LLM désactivée")
            return {}
        
        logger.info("=== ÉTAPE 7: ANALYSE LLM ===")
        
        try:
            analyzer = LLMBloodStockAnalyzer(use_local_models=self.config['llm']['use_local_models'])
            
            # Prendre un échantillon
            sample_size = min(self.config['llm']['sample_size'], len(df))
            sample_df = df.sample(n=sample_size, random_state=42)
            
            # Analyse
            analyzed_df = analyzer.batch_analyze(sample_df)
            
            # Statistiques
            stats = analyzer.get_urgency_statistics(analyzed_df)
            
            # Rapport d'alerte
            alert_report = analyzer.generate_alert_report(analyzed_df)
            
            # Sauvegarde
            os.makedirs('data/llm_analysis', exist_ok=True)
            analyzed_df.to_csv('data/llm_analysis/analyzed_data.csv', index=False)
            
            with open('data/llm_analysis/alert_report.txt', 'w', encoding='utf-8') as f:
                f.write(alert_report)
            
            analyzer.save_analysis_cache()
            
            logger.info("Analyse LLM terminée avec succès")
            self.results['llm_analysis'] = {
                'analyzed_samples': len(analyzed_df),
                'critical_cases': stats.get('critical_cases', 0),
                'high_urgency_cases': stats.get('high_urgency_cases', 0),
                'status': 'success'
            }
            
            return {'stats': stats, 'report': alert_report}
            
        except Exception as e:
            logger.error(f"Erreur Analyse LLM: {str(e)}")
            self.results['llm_analysis'] = {'status': 'failed', 'error': str(e)}
            return {}
    
    def run_full_pipeline(self) -> dict:
        """Exécute le pipeline complet"""
        logger.info("🚀 DÉMARRAGE DU PIPELINE MLOPS COMPLET")
        start_time = datetime.now()
        
        with mlflow.start_run(run_name=f"full_pipeline_{start_time.strftime('%Y%m%d_%H%M%S')}"):
            
            try:
                # Étape 1: Génération des données
                df = self.step_1_generate_data()
                
                # Étape 2: Préprocessing
                train_df, val_df, test_df, preprocessor = self.step_2_preprocess_data(df)
                
                # Étape 3: ARIMA
                arima_results = self.step_3_train_arima(train_df, val_df)
                
                # Étape 4: XGBoost
                xgboost_results = self.step_4_train_xgboost(train_df, val_df, test_df, preprocessor)
                
                # Étape 5: LSTM
                lstm_results = self.step_5_train_lstm(train_df, val_df, test_df)
                
                # Étape 6: Ensemble
                ensemble_results = self.step_6_train_ensemble(train_df, val_df, test_df, preprocessor)
                
                # Étape 7: Analyse LLM
                llm_results = self.step_7_llm_analysis(df)
                
                # Résultats finaux
                total_time = (datetime.now() - start_time).total_seconds()
                
                # Log des métriques globales
                mlflow.log_metrics({
                    'total_pipeline_time': total_time,
                    'successful_models': sum(1 for r in self.results.values() if isinstance(r, dict) and r.get('status') == 'success')
                })
                
                logger.info(f"🎉 PIPELINE TERMINÉ EN {total_time:.2f} secondes")
                
                # Résumé final
                self.print_final_summary()
                
                return {
                    'status': 'completed',
                    'total_time': total_time,
                    'results': self.results,
                    'timestamp': datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Erreur dans le pipeline: {str(e)}")
                return {
                    'status': 'failed',
                    'error': str(e),
                    'results': self.results,
                    'timestamp': datetime.now().isoformat()
                }
    
    def print_final_summary(self):
        """Affiche un résumé final des résultats"""
        logger.info("\n" + "="*60)
        logger.info("📊 RÉSUMÉ FINAL DU PIPELINE MLOPS")
        logger.info("="*60)
        
        for step, result in self.results.items():
            if isinstance(result, dict):
                status = result.get('status', 'unknown')
                if status == 'success':
                    logger.info(f"✅ {step.upper()}: Succès")
                    if 'mae' in str(result):
                        mae_keys = [k for k in result.keys() if 'mae' in k]
                        for key in mae_keys:
                            logger.info(f"   {key}: {result[key]:.4f}")
                elif status == 'failed':
                    logger.info(f"❌ {step.upper()}: Échec - {result.get('error', 'Erreur inconnue')}")
                elif status == 'skipped':
                    logger.info(f"⏭️ {step.upper()}: Ignoré - {result.get('reason', 'Raison inconnue')}")
                else:
                    logger.info(f"ℹ️ {step.upper()}: {result}")
        
        logger.info("="*60)

def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description="Pipeline MLOps pour les stocks de sang")
    parser.add_argument('--config', type=str, help="Fichier de configuration JSON")
    parser.add_argument('--step', type=str, choices=['data', 'preprocess', 'arima', 'xgboost', 'lstm', 'ensemble', 'llm', 'all'], 
                       default='all', help="Étape à exécuter")
    parser.add_argument('--output-dir', type=str, default='models', help="Répertoire de sortie")
    
    args = parser.parse_args()
    
    # Charger la configuration
    config = None
    if args.config and os.path.exists(args.config):
        import json
        with open(args.config, 'r') as f:
            config = json.load(f)
    
    # Créer le pipeline
    pipeline = MLOpsPipeline(config)
    
    if args.output_dir:
        pipeline.config['output_dir'] = args.output_dir
    
    # Exécuter l'étape demandée
    if args.step == 'all':
        results = pipeline.run_full_pipeline()
    else:
        logger.info(f"Exécution de l'étape: {args.step}")
        # Ici on pourrait ajouter l'exécution d'étapes individuelles
        results = pipeline.run_full_pipeline()
    
    # Sauvegarder les résultats
    import json
    with open('pipeline_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info("Résultats sauvegardés dans pipeline_results.json")

if __name__ == "__main__":
    main()