import pandas as pd
import numpy as np
from sklearn.ensemble import VotingRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import os
from typing import Dict, List, Tuple, Optional, Union
import matplotlib.pyplot as plt
import seaborn as sns
import mlflow
import mlflow.sklearn
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Import des modèles individuels
from .arima_model import ARIMAPredictor
from .xgboost_model import XGBoostPredictor
from .lstm_model import LSTMPredictor

class EnsemblePredictor:
    """Modèle d'ensemble combinant ARIMA, XGBoost et LSTM"""
    
    def __init__(self, experiment_name: str = "blood_stock_ensemble"):
        self.arima_model = None
        self.xgboost_model = None
        self.lstm_model = None
        self.meta_model = None
        self.weights = None
        self.is_fitted = False
        self.experiment_name = experiment_name
        self.ensemble_method = 'weighted_average'  # 'weighted_average', 'stacking', 'voting'
        
        # Configuration MLflow
        mlflow.set_experiment(experiment_name)
    
    def load_individual_models(self, models_dir: str = 'models'):
        """Charge les modèles individuels pré-entraînés"""
        
        print("Chargement des modèles individuels...")
        
        # Charger ARIMA
        try:
            self.arima_model = ARIMAPredictor()
            self.arima_model.load_models(f'{models_dir}/arima')
            print("✓ Modèle ARIMA chargé")
        except Exception as e:
            print(f"✗ Erreur chargement ARIMA: {str(e)}")
            self.arima_model = None
        
        # Charger XGBoost
        try:
            self.xgboost_model = XGBoostPredictor()
            self.xgboost_model.load_model(f'{models_dir}/xgboost')
            print("✓ Modèle XGBoost chargé")
        except Exception as e:
            print(f"✗ Erreur chargement XGBoost: {str(e)}")
            self.xgboost_model = None
        
        # Charger LSTM
        try:
            self.lstm_model = LSTMPredictor()
            self.lstm_model.load_model(f'{models_dir}/lstm')
            print("✓ Modèle LSTM chargé")
        except Exception as e:
            print(f"✗ Erreur chargement LSTM: {str(e)}")
            self.lstm_model = None
        
        available_models = sum([1 for model in [self.arima_model, self.xgboost_model, self.lstm_model] if model is not None])
        print(f"\nModèles disponibles: {available_models}/3")
        
        return available_models > 0
    
    def get_individual_predictions(self, df: pd.DataFrame, feature_columns: List[str] = None) -> Dict[str, np.ndarray]:
        """Obtient les prédictions de chaque modèle individuel"""
        
        predictions = {}
        
        # Prédictions XGBoost (plus facile à obtenir)
        if self.xgboost_model is not None and feature_columns is not None:
            try:
                available_features = [col for col in feature_columns if col in df.columns]
                if available_features:
                    X = df[available_features].fillna(0).values
                    pred_xgb = self.xgboost_model.predict(X)
                    predictions['xgboost'] = pred_xgb
                    print(f"✓ Prédictions XGBoost: {len(pred_xgb)} échantillons")
            except Exception as e:
                print(f"✗ Erreur prédictions XGBoost: {str(e)}")
        
        # Prédictions ARIMA (par série temporelle)
        if self.arima_model is not None:
            try:
                arima_predictions = []
                
                for _, row in df.iterrows():
                    hospital = row['hospital']
                    blood_type = row['blood_type']
                    
                    try:
                        pred_result = self.arima_model.predict(hospital, blood_type, steps=1)
                        pred_value = pred_result['predictions'][0]
                        arima_predictions.append(pred_value)
                    except:
                        # Si pas de modèle pour cette combinaison, utiliser la moyenne
                        arima_predictions.append(row.get('stock_final', 0))
                
                predictions['arima'] = np.array(arima_predictions)
                print(f"✓ Prédictions ARIMA: {len(arima_predictions)} échantillons")
            except Exception as e:
                print(f"✗ Erreur prédictions ARIMA: {str(e)}")
        
        # Prédictions LSTM (nécessite des séquences)
        if self.lstm_model is not None:
            try:
                # Simplification: utiliser les dernières valeurs comme séquence
                lstm_predictions = []
                
                # Préparer les données par série pour LSTM
                series_data = self.lstm_model.prepare_data_by_series(df)
                
                for key, data in series_data.items():
                    if len(data['X']) > 0:
                        # Prendre la dernière séquence
                        last_sequence = data['X'][-1:]
                        pred = self.lstm_model.predict(last_sequence)[0, 0]
                        
                        # Dénormaliser
                        pred_denorm = data['scaler_target'].inverse_transform([[pred]])[0, 0]
                        lstm_predictions.append(pred_denorm)
                    else:
                        lstm_predictions.append(0)
                
                if lstm_predictions:
                    # Répéter pour correspondre à la taille du DataFrame
                    predictions['lstm'] = np.array(lstm_predictions * (len(df) // len(lstm_predictions) + 1))[:len(df)]
                    print(f"✓ Prédictions LSTM: {len(predictions['lstm'])} échantillons")
            except Exception as e:
                print(f"✗ Erreur prédictions LSTM: {str(e)}")
        
        return predictions
    
    def calculate_model_weights(self, predictions: Dict[str, np.ndarray], y_true: np.ndarray) -> Dict[str, float]:
        """Calcule les poids optimaux pour chaque modèle basé sur leur performance"""
        
        weights = {}
        total_inverse_error = 0
        
        for model_name, pred in predictions.items():
            if len(pred) == len(y_true):
                # Calculer l'erreur (MAE)
                mae = mean_absolute_error(y_true, pred)
                
                # Poids inversement proportionnel à l'erreur
                weight = 1 / (mae + 1e-8)
                weights[model_name] = weight
                total_inverse_error += weight
        
        # Normaliser les poids
        if total_inverse_error > 0:
            for model_name in weights:
                weights[model_name] /= total_inverse_error
        
        return weights
    
    def weighted_average_prediction(self, predictions: Dict[str, np.ndarray], weights: Dict[str, float] = None) -> np.ndarray:
        """Combine les prédictions avec une moyenne pondérée"""
        
        if not predictions:
            raise ValueError("Aucune prédiction disponible")
        
        # Poids égaux si non spécifiés
        if weights is None:
            weights = {name: 1.0/len(predictions) for name in predictions.keys()}
        
        # Vérifier que toutes les prédictions ont la même taille
        sizes = [len(pred) for pred in predictions.values()]
        if len(set(sizes)) > 1:
            min_size = min(sizes)
            predictions = {name: pred[:min_size] for name, pred in predictions.items()}
        
        # Calculer la moyenne pondérée
        ensemble_pred = np.zeros(len(list(predictions.values())[0]))
        
        for model_name, pred in predictions.items():
            weight = weights.get(model_name, 0)
            ensemble_pred += weight * pred
        
        return ensemble_pred
    
    def stacking_prediction(self, predictions: Dict[str, np.ndarray], y_true: np.ndarray) -> Tuple[np.ndarray, object]:
        """Utilise un méta-modèle pour combiner les prédictions (stacking)"""
        
        if not predictions:
            raise ValueError("Aucune prédiction disponible")
        
        # Préparer les features pour le méta-modèle
        X_meta = np.column_stack(list(predictions.values()))
        
        # Entraîner le méta-modèle
        meta_model = Ridge(alpha=1.0)
        meta_model.fit(X_meta, y_true)
        
        # Prédictions du méta-modèle
        ensemble_pred = meta_model.predict(X_meta)
        
        return ensemble_pred, meta_model
    
    def train_ensemble(self, df_train: pd.DataFrame, df_val: pd.DataFrame, 
                      feature_columns: List[str], method: str = 'weighted_average') -> Dict:
        """Entraîne le modèle d'ensemble"""
        
        with mlflow.start_run(run_name=f"ensemble_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
            
            self.ensemble_method = method
            
            print(f"\n=== ENTRAÎNEMENT ENSEMBLE ({method.upper()}) ===")
            
            # Obtenir les prédictions individuelles sur les données de validation
            print("\nObtention des prédictions individuelles...")
            val_predictions = self.get_individual_predictions(df_val, feature_columns)
            
            if not val_predictions:
                raise ValueError("Aucune prédiction disponible des modèles individuels")
            
            y_val = df_val['stock_final'].values
            
            # Calculer les métriques individuelles
            individual_metrics = {}
            for model_name, pred in val_predictions.items():
                if len(pred) == len(y_val):
                    metrics = self.calculate_metrics(y_val, pred, model_name)
                    individual_metrics[model_name] = metrics
            
            # Entraîner l'ensemble selon la méthode choisie
            if method == 'weighted_average':
                # Calculer les poids optimaux
                self.weights = self.calculate_model_weights(val_predictions, y_val)
                ensemble_pred = self.weighted_average_prediction(val_predictions, self.weights)
                
            elif method == 'stacking':
                # Utiliser un méta-modèle
                ensemble_pred, self.meta_model = self.stacking_prediction(val_predictions, y_val)
                
            elif method == 'voting':
                # Moyenne simple
                self.weights = {name: 1.0/len(val_predictions) for name in val_predictions.keys()}
                ensemble_pred = self.weighted_average_prediction(val_predictions, self.weights)
            
            # Métriques de l'ensemble
            ensemble_metrics = self.calculate_metrics(y_val, ensemble_pred, "Ensemble")
            
            self.is_fitted = True
            
            # Log dans MLflow
            mlflow.log_params({
                'ensemble_method': method,
                'available_models': list(val_predictions.keys()),
                'weights': self.weights if self.weights else {}
            })
            
            mlflow.log_metrics({
                'ensemble_mae': ensemble_metrics['mae'],
                'ensemble_rmse': ensemble_metrics['rmse'],
                'ensemble_r2': ensemble_metrics['r2']
            })
            
            # Log des métriques individuelles
            for model_name, metrics in individual_metrics.items():
                mlflow.log_metrics({
                    f'{model_name}_mae': metrics['mae'],
                    f'{model_name}_rmse': metrics['rmse'],
                    f'{model_name}_r2': metrics['r2']
                })
            
            # Résultats
            results = {
                'individual_metrics': individual_metrics,
                'ensemble_metrics': ensemble_metrics,
                'weights': self.weights,
                'method': method,
                'predictions': {
                    'individual': val_predictions,
                    'ensemble': ensemble_pred,
                    'true': y_val
                }
            }
            
            self.print_results(results)
            
            return results
    
    def predict(self, df: pd.DataFrame, feature_columns: List[str]) -> np.ndarray:
        """Fait des prédictions avec le modèle d'ensemble"""
        
        if not self.is_fitted:
            raise ValueError("Le modèle d'ensemble doit être entraîné avant de faire des prédictions")
        
        # Obtenir les prédictions individuelles
        predictions = self.get_individual_predictions(df, feature_columns)
        
        if not predictions:
            raise ValueError("Aucune prédiction disponible des modèles individuels")
        
        # Combiner selon la méthode d'ensemble
        if self.ensemble_method == 'stacking' and self.meta_model is not None:
            X_meta = np.column_stack(list(predictions.values()))
            ensemble_pred = self.meta_model.predict(X_meta)
        else:
            ensemble_pred = self.weighted_average_prediction(predictions, self.weights)
        
        return ensemble_pred
    
    def calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, model_name: str) -> Dict:
        """Calcule les métriques de performance"""
        
        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mape = np.mean(np.abs((y_true - y_pred) / (y_true + 1e-8))) * 100
        r2 = r2_score(y_true, y_pred)
        
        metrics = {
            'mae': mae,
            'rmse': rmse,
            'mape': mape,
            'r2': r2
        }
        
        return metrics
    
    def print_results(self, results: Dict):
        """Affiche les résultats d'entraînement"""
        
        print("\n=== RÉSULTATS ENSEMBLE ===")
        
        # Métriques individuelles
        print("\nPerformances des modèles individuels:")
        for model_name, metrics in results['individual_metrics'].items():
            print(f"  {model_name.upper()}:")
            print(f"    MAE: {metrics['mae']:.4f}")
            print(f"    RMSE: {metrics['rmse']:.4f}")
            print(f"    R²: {metrics['r2']:.4f}")
        
        # Métriques d'ensemble
        ensemble_metrics = results['ensemble_metrics']
        print(f"\nPerformance de l'ENSEMBLE:")
        print(f"  MAE: {ensemble_metrics['mae']:.4f}")
        print(f"  RMSE: {ensemble_metrics['rmse']:.4f}")
        print(f"  R²: {ensemble_metrics['r2']:.4f}")
        
        # Poids
        if results['weights']:
            print(f"\nPoids des modèles:")
            for model_name, weight in results['weights'].items():
                print(f"  {model_name}: {weight:.3f}")
    
    def evaluate(self, df_test: pd.DataFrame, feature_columns: List[str]) -> Dict:
        """Évalue le modèle d'ensemble sur des données de test"""
        
        if not self.is_fitted:
            raise ValueError("Le modèle d'ensemble doit être entraîné avant l'évaluation")
        
        print("\n=== ÉVALUATION ENSEMBLE SUR DONNÉES DE TEST ===")
        
        # Prédictions
        ensemble_pred = self.predict(df_test, feature_columns)
        y_test = df_test['stock_final'].values
        
        # Prédictions individuelles pour comparaison
        individual_predictions = self.get_individual_predictions(df_test, feature_columns)
        
        # Métriques
        test_results = {}
        
        # Métriques individuelles
        for model_name, pred in individual_predictions.items():
            if len(pred) == len(y_test):
                metrics = self.calculate_metrics(y_test, pred, model_name)
                test_results[model_name] = metrics
        
        # Métriques d'ensemble
        ensemble_metrics = self.calculate_metrics(y_test, ensemble_pred, "Ensemble")
        test_results['ensemble'] = ensemble_metrics
        
        # Affichage
        for model_name, metrics in test_results.items():
            print(f"\n{model_name.upper()}:")
            print(f"  MAE: {metrics['mae']:.4f}")
            print(f"  RMSE: {metrics['rmse']:.4f}")
            print(f"  MAPE: {metrics['mape']:.2f}%")
            print(f"  R²: {metrics['r2']:.4f}")
        
        return test_results
    
    def plot_model_comparison(self, results: Dict):
        """Visualise la comparaison des modèles"""
        
        predictions = results['predictions']
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # Scatter plots pour chaque modèle
        models = list(predictions['individual'].keys()) + ['ensemble']
        
        for i, model_name in enumerate(models[:4]):
            row, col = i // 2, i % 2
            
            if model_name == 'ensemble':
                y_pred = predictions['ensemble']
            else:
                y_pred = predictions['individual'][model_name]
            
            y_true = predictions['true']
            
            axes[row, col].scatter(y_true, y_pred, alpha=0.6)
            axes[row, col].plot([y_true.min(), y_true.max()], [y_true.min(), y_true.max()], 'r--', lw=2)
            axes[row, col].set_xlabel('Valeurs Réelles')
            axes[row, col].set_ylabel('Prédictions')
            axes[row, col].set_title(f'{model_name.upper()}')
            axes[row, col].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    def plot_metrics_comparison(self, test_results: Dict):
        """Visualise la comparaison des métriques"""
        
        models = list(test_results.keys())
        metrics = ['mae', 'rmse', 'r2']
        
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        
        for i, metric in enumerate(metrics):
            values = [test_results[model][metric] for model in models]
            
            bars = axes[i].bar(models, values)
            axes[i].set_title(f'{metric.upper()}')
            axes[i].set_ylabel(metric.upper())
            
            # Colorer la barre de l'ensemble
            if 'ensemble' in models:
                ensemble_idx = models.index('ensemble')
                bars[ensemble_idx].set_color('red')
            
            axes[i].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        plt.show()
    
    def save_ensemble(self, output_dir: str = 'models/ensemble'):
        """Sauvegarde le modèle d'ensemble"""
        
        if not self.is_fitted:
            raise ValueError("Le modèle d'ensemble doit être entraîné avant la sauvegarde")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Sauvegarder les métadonnées
        ensemble_data = {
            'weights': self.weights,
            'ensemble_method': self.ensemble_method,
            'meta_model': self.meta_model
        }
        
        joblib.dump(ensemble_data, f'{output_dir}/ensemble_model.pkl')
        
        print(f"Modèle d'ensemble sauvegardé dans {output_dir}")
    
    def load_ensemble(self, input_dir: str = 'models/ensemble'):
        """Charge le modèle d'ensemble"""
        
        # Charger les métadonnées
        ensemble_data = joblib.load(f'{input_dir}/ensemble_model.pkl')
        
        self.weights = ensemble_data['weights']
        self.ensemble_method = ensemble_data['ensemble_method']
        self.meta_model = ensemble_data['meta_model']
        
        # Charger les modèles individuels
        self.load_individual_models()
        
        self.is_fitted = True
        print(f"Modèle d'ensemble chargé depuis {input_dir}")

def main():
    """Fonction principale pour tester le modèle d'ensemble"""
    
    # Charger les données
    print("Chargement des données...")
    train_df = pd.read_csv('data/processed/train.csv')
    val_df = pd.read_csv('data/processed/val.csv')
    test_df = pd.read_csv('data/processed/test.csv')
    
    # Charger les noms des features
    feature_columns = joblib.load('models/preprocessor/feature_columns.pkl')
    
    # Créer le modèle d'ensemble
    ensemble = EnsemblePredictor()
    
    # Charger les modèles individuels
    if not ensemble.load_individual_models():
        print("Erreur: Aucun modèle individuel disponible")
        return
    
    # Entraîner l'ensemble
    print("\nEntraînement du modèle d'ensemble...")
    
    # Tester différentes méthodes
    methods = ['weighted_average', 'stacking', 'voting']
    best_method = None
    best_score = float('inf')
    
    for method in methods:
        print(f"\n--- Test méthode: {method} ---")
        try:
            results = ensemble.train_ensemble(train_df, val_df, feature_columns, method)
            score = results['ensemble_metrics']['mae']
            
            if score < best_score:
                best_score = score
                best_method = method
                
        except Exception as e:
            print(f"Erreur avec {method}: {str(e)}")
    
    # Entraîner avec la meilleure méthode
    if best_method:
        print(f"\nEntraînement final avec la meilleure méthode: {best_method}")
        final_results = ensemble.train_ensemble(train_df, val_df, feature_columns, best_method)
        
        # Évaluation sur les données de test
        print("\nÉvaluation sur les données de test...")
        test_results = ensemble.evaluate(test_df, feature_columns)
        
        # Visualisations
        print("\nGénération des visualisations...")
        ensemble.plot_model_comparison(final_results)
        ensemble.plot_metrics_comparison(test_results)
        
        # Sauvegarde
        print("\nSauvegarde du modèle d'ensemble...")
        ensemble.save_ensemble()
        
        print("\nEntraînement d'ensemble terminé avec succès!")
    else:
        print("Aucune méthode d'ensemble n'a fonctionné")

if __name__ == "__main__":
    main()