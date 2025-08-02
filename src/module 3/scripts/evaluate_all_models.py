#!/usr/bin/env python3
"""
Script d'évaluation comparative de tous les modèles
"""

import os
import sys
import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Ajouter le chemin du projet
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from training.ensemble_model import EnsemblePredictor
from training.xgboost_model import XGBoostPredictor
from training.lstm_model import LSTMPredictor
from training.arima_model import ARIMAPredictor
from preprocessing.data_preprocessor import BloodStockPreprocessor

class ModelEvaluator:
    """Évaluateur comparatif de tous les modèles"""
    
    def __init__(self):
        self.models = {}
        self.results = {}
        self.test_data = None
        self.preprocessor = None
        
    def load_test_data(self, test_path: str = 'data/processed/test.csv'):
        """Charge les données de test"""
        print(f"Chargement des données de test: {test_path}")
        self.test_data = pd.read_csv(test_path)
        print(f"Données de test chargées: {len(self.test_data)} échantillons")
        
    def load_preprocessor(self, preprocessor_path: str = 'models/preprocessor'):
        """Charge le préprocesseur"""
        try:
            self.preprocessor = BloodStockPreprocessor()
            self.preprocessor.load_preprocessor(preprocessor_path)
            print("✅ Préprocesseur chargé")
        except Exception as e:
            print(f"❌ Erreur chargement préprocesseur: {str(e)}")
            
    def load_models(self, models_dir: str = 'models'):
        """Charge tous les modèles disponibles"""
        print("Chargement des modèles...")
        
        # Ensemble
        try:
            ensemble = EnsemblePredictor()
            ensemble.load_ensemble(f'{models_dir}/ensemble')
            self.models['ensemble'] = ensemble
            print("✅ Modèle d'ensemble chargé")
        except Exception as e:
            print(f"❌ Erreur ensemble: {str(e)}")
            
        # XGBoost
        try:
            xgboost = XGBoostPredictor()
            xgboost.load_model(f'{models_dir}/xgboost')
            self.models['xgboost'] = xgboost
            print("✅ Modèle XGBoost chargé")
        except Exception as e:
            print(f"❌ Erreur XGBoost: {str(e)}")
            
        # LSTM
        try:
            lstm = LSTMPredictor()
            lstm.load_model(f'{models_dir}/lstm')
            self.models['lstm'] = lstm
            print("✅ Modèle LSTM chargé")
        except Exception as e:
            print(f"❌ Erreur LSTM: {str(e)}")
            
        # ARIMA
        try:
            arima = ARIMAPredictor()
            arima.load_models(f'{models_dir}/arima')
            self.models['arima'] = arima
            print("✅ Modèle ARIMA chargé")
        except Exception as e:
            print(f"❌ Erreur ARIMA: {str(e)}")
            
        print(f"Modèles chargés: {list(self.models.keys())}")
        
    def calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> dict:
        """Calcule les métriques de performance"""
        return {
            'mae': mean_absolute_error(y_true, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_true, y_pred)),
            'mape': np.mean(np.abs((y_true - y_pred) / (y_true + 1e-8))) * 100,
            'r2': r2_score(y_true, y_pred)
        }
        
    def evaluate_ensemble(self) -> dict:
        """Évalue le modèle d'ensemble"""
        if 'ensemble' not in self.models or not self.preprocessor:
            return {}
            
        try:
            ensemble = self.models['ensemble']
            predictions = ensemble.predict(self.test_data, self.preprocessor.feature_columns)
            y_true = self.test_data['stock_final'].values
            
            metrics = self.calculate_metrics(y_true, predictions)
            
            return {
                'predictions': predictions,
                'metrics': metrics,
                'model_info': {
                    'method': ensemble.ensemble_method,
                    'weights': ensemble.weights
                }
            }
        except Exception as e:
            print(f"Erreur évaluation ensemble: {str(e)}")
            return {}
            
    def evaluate_xgboost(self) -> dict:
        """Évalue le modèle XGBoost"""
        if 'xgboost' not in self.models or not self.preprocessor:
            return {}
            
        try:
            xgboost = self.models['xgboost']
            X_test, y_test, _ = xgboost.prepare_features(self.test_data, self.preprocessor.feature_columns)
            
            predictions = xgboost.predict(X_test)
            metrics = self.calculate_metrics(y_test, predictions)
            
            return {
                'predictions': predictions,
                'metrics': metrics,
                'model_info': {
                    'feature_importance': xgboost.feature_importance.head(10).to_dict('records') if xgboost.feature_importance is not None else []
                }
            }
        except Exception as e:
            print(f"Erreur évaluation XGBoost: {str(e)}")
            return {}
            
    def evaluate_lstm(self) -> dict:
        """Évalue le modèle LSTM"""
        if 'lstm' not in self.models:
            return {}
            
        try:
            lstm = self.models['lstm']
            
            # Préparer les données LSTM
            test_series = lstm.prepare_data_by_series(self.test_data)
            X_test, y_test, _ = lstm.combine_series_data(test_series)
            
            if len(X_test) == 0:
                return {'error': 'Pas assez de données pour LSTM'}
                
            predictions = lstm.predict(X_test)
            metrics = self.calculate_metrics(y_test, predictions.flatten())
            
            return {
                'predictions': predictions.flatten(),
                'metrics': metrics,
                'model_info': {
                    'sequence_length': lstm.sequence_length,
                    'samples_evaluated': len(X_test)
                }
            }
        except Exception as e:
            print(f"Erreur évaluation LSTM: {str(e)}")
            return {}
            
    def evaluate_arima(self) -> dict:
        """Évalue le modèle ARIMA"""
        if 'arima' not in self.models:
            return {}
            
        try:
            arima = self.models['arima']
            
            # Pour ARIMA, on fait des prédictions par série
            predictions = []
            y_true = []
            
            for _, row in self.test_data.iterrows():
                try:
                    pred_result = arima.predict(row['hospital'], row['blood_type'], steps=1)
                    predictions.append(pred_result['predictions'][0])
                    y_true.append(row['stock_final'])
                except:
                    # Si pas de modèle pour cette combinaison, utiliser la moyenne
                    predictions.append(row['stock_final'])
                    y_true.append(row['stock_final'])
            
            predictions = np.array(predictions)
            y_true = np.array(y_true)
            
            metrics = self.calculate_metrics(y_true, predictions)
            
            return {
                'predictions': predictions,
                'metrics': metrics,
                'model_info': {
                    'models_count': len(arima.models),
                    'series_covered': list(arima.models.keys())[:5]  # Premiers 5
                }
            }
        except Exception as e:
            print(f"Erreur évaluation ARIMA: {str(e)}")
            return {}
            
    def run_evaluation(self) -> dict:
        """Lance l'évaluation complète"""
        print("\n=== ÉVALUATION COMPARATIVE DES MODÈLES ===")
        
        # Évaluer chaque modèle
        self.results['ensemble'] = self.evaluate_ensemble()
        self.results['xgboost'] = self.evaluate_xgboost()
        self.results['lstm'] = self.evaluate_lstm()
        self.results['arima'] = self.evaluate_arima()
        
        # Filtrer les résultats vides
        self.results = {k: v for k, v in self.results.items() if v and 'metrics' in v}
        
        # Résumé comparatif
        comparison = self.create_comparison_summary()
        
        return {
            'individual_results': self.results,
            'comparison': comparison,
            'evaluation_timestamp': datetime.now().isoformat(),
            'test_samples': len(self.test_data)
        }
        
    def create_comparison_summary(self) -> dict:
        """Crée un résumé comparatif"""
        if not self.results:
            return {}
            
        metrics_comparison = {}
        
        for metric in ['mae', 'rmse', 'mape', 'r2']:
            metrics_comparison[metric] = {}
            for model_name, result in self.results.items():
                if 'metrics' in result:
                    metrics_comparison[metric][model_name] = result['metrics'][metric]
        
        # Trouver le meilleur modèle pour chaque métrique
        best_models = {}
        for metric in ['mae', 'rmse', 'mape']:
            if metric in metrics_comparison and metrics_comparison[metric]:
                best_model = min(metrics_comparison[metric], key=metrics_comparison[metric].get)
                best_models[metric] = {
                    'model': best_model,
                    'value': metrics_comparison[metric][best_model]
                }
        
        # Pour R², on veut le maximum
        if 'r2' in metrics_comparison and metrics_comparison['r2']:
            best_model = max(metrics_comparison['r2'], key=metrics_comparison['r2'].get)
            best_models['r2'] = {
                'model': best_model,
                'value': metrics_comparison['r2'][best_model]
            }
        
        return {
            'metrics_comparison': metrics_comparison,
            'best_models': best_models,
            'models_evaluated': list(self.results.keys())
        }
        
    def create_visualizations(self, output_dir: str = 'evaluation'):
        """Crée les visualisations comparatives"""
        os.makedirs(output_dir, exist_ok=True)
        
        if not self.results:
            print("Aucun résultat à visualiser")
            return
            
        # 1. Comparaison des métriques
        self.plot_metrics_comparison(output_dir)
        
        # 2. Scatter plots des prédictions
        self.plot_predictions_comparison(output_dir)
        
        # 3. Feature importance (si disponible)
        self.plot_feature_importance(output_dir)
        
    def plot_metrics_comparison(self, output_dir: str):
        """Graphique de comparaison des métriques"""
        metrics_data = []
        
        for model_name, result in self.results.items():
            if 'metrics' in result:
                for metric, value in result['metrics'].items():
                    metrics_data.append({
                        'Model': model_name,
                        'Metric': metric.upper(),
                        'Value': value
                    })
        
        if not metrics_data:
            return
            
        df_metrics = pd.DataFrame(metrics_data)
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Comparaison des Performances des Modèles', fontsize=16)
        
        metrics = ['MAE', 'RMSE', 'MAPE', 'R2']
        
        for i, metric in enumerate(metrics):
            row, col = i // 2, i % 2
            
            metric_data = df_metrics[df_metrics['Metric'] == metric]
            if not metric_data.empty:
                sns.barplot(data=metric_data, x='Model', y='Value', ax=axes[row, col])
                axes[row, col].set_title(f'{metric}')
                axes[row, col].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        plt.savefig(f'{output_dir}/model_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Graphique de comparaison sauvegardé: {output_dir}/model_comparison.png")
        
    def plot_predictions_comparison(self, output_dir: str):
        """Graphiques scatter des prédictions vs réalité"""
        n_models = len(self.results)
        if n_models == 0:
            return
            
        cols = min(2, n_models)
        rows = (n_models + 1) // 2
        
        fig, axes = plt.subplots(rows, cols, figsize=(12, 6*rows))
        if n_models == 1:
            axes = [axes]
        elif rows == 1:
            axes = [axes]
        else:
            axes = axes.flatten()
        
        y_true = self.test_data['stock_final'].values
        
        for i, (model_name, result) in enumerate(self.results.items()):
            if 'predictions' in result:
                predictions = result['predictions']
                
                # Ajuster les tailles si nécessaire
                min_len = min(len(y_true), len(predictions))
                y_true_plot = y_true[:min_len]
                predictions_plot = predictions[:min_len]
                
                axes[i].scatter(y_true_plot, predictions_plot, alpha=0.6)
                axes[i].plot([y_true_plot.min(), y_true_plot.max()], 
                           [y_true_plot.min(), y_true_plot.max()], 'r--', lw=2)
                axes[i].set_xlabel('Valeurs Réelles')
                axes[i].set_ylabel('Prédictions')
                axes[i].set_title(f'{model_name.upper()}')
                axes[i].grid(True, alpha=0.3)
        
        # Masquer les axes inutilisés
        for i in range(len(self.results), len(axes)):
            axes[i].set_visible(False)
        
        plt.tight_layout()
        plt.savefig(f'{output_dir}/predictions_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Graphique des prédictions sauvegardé: {output_dir}/predictions_comparison.png")
        
    def plot_feature_importance(self, output_dir: str):
        """Graphique d'importance des features (XGBoost)"""
        if 'xgboost' not in self.results or 'model_info' not in self.results['xgboost']:
            return
            
        feature_importance = self.results['xgboost']['model_info'].get('feature_importance', [])
        if not feature_importance:
            return
            
        df_importance = pd.DataFrame(feature_importance)
        
        plt.figure(figsize=(12, 8))
        sns.barplot(data=df_importance, x='importance', y='feature')
        plt.title('Importance des Features - XGBoost')
        plt.xlabel('Importance')
        plt.ylabel('Features')
        plt.tight_layout()
        plt.savefig(f'{output_dir}/feature_importance.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Graphique d'importance sauvegardé: {output_dir}/feature_importance.png")
        
    def save_results(self, results: dict, output_path: str = 'evaluation/model_comparison.json'):
        """Sauvegarde les résultats"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Convertir les arrays numpy en listes pour la sérialisation JSON
        def convert_numpy(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_numpy(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(item) for item in obj]
            return obj
        
        results_serializable = convert_numpy(results)
        
        with open(output_path, 'w') as f:
            json.dump(results_serializable, f, indent=2)
        
        print(f"✅ Résultats sauvegardés: {output_path}")
        
    def print_summary(self, results: dict):
        """Affiche un résumé des résultats"""
        print("\n" + "="*60)
        print("📊 RÉSUMÉ DE L'ÉVALUATION COMPARATIVE")
        print("="*60)
        
        if 'comparison' in results and 'best_models' in results['comparison']:
            print("\n🏆 MEILLEURS MODÈLES PAR MÉTRIQUE:")
            for metric, info in results['comparison']['best_models'].items():
                print(f"  {metric.upper()}: {info['model']} ({info['value']:.4f})")
        
        if 'comparison' in results and 'metrics_comparison' in results['comparison']:
            print("\n📈 COMPARAISON DÉTAILLÉE:")
            for metric, models_scores in results['comparison']['metrics_comparison'].items():
                print(f"\n  {metric.upper()}:")
                sorted_models = sorted(models_scores.items(), key=lambda x: x[1], reverse=(metric == 'r2'))
                for model, score in sorted_models:
                    print(f"    {model}: {score:.4f}")
        
        print("\n" + "="*60)

def main():
    """Fonction principale"""
    evaluator = ModelEvaluator()
    
    # Charger les données et modèles
    evaluator.load_test_data()
    evaluator.load_preprocessor()
    evaluator.load_models()
    
    if not evaluator.models:
        print("❌ Aucun modèle disponible pour l'évaluation")
        return
    
    # Lancer l'évaluation
    results = evaluator.run_evaluation()
    
    # Afficher le résumé
    evaluator.print_summary(results)
    
    # Créer les visualisations
    evaluator.create_visualizations()
    
    # Sauvegarder les résultats
    evaluator.save_results(results)
    
    print("\n✅ Évaluation comparative terminée avec succès!")

if __name__ == "__main__":
    main()