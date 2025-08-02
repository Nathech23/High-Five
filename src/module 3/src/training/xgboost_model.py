import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
import optuna
import joblib
import os
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple, Optional
import mlflow
import mlflow.xgboost
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class XGBoostPredictor:
    """Modèle XGBoost pour la prédiction multi-variable des stocks de sang"""
    
    def __init__(self, experiment_name: str = "blood_stock_xgboost"):
        self.model = None
        self.feature_importance = None
        self.best_params = None
        self.is_fitted = False
        self.experiment_name = experiment_name
        
        # Configuration MLflow
        mlflow.set_experiment(experiment_name)
    
    def prepare_features(self, df: pd.DataFrame, feature_columns: List[str]) -> Tuple[np.ndarray, np.ndarray]:
        """Prépare les features pour XGBoost"""
        
        # Sélectionner les features disponibles
        available_features = [col for col in feature_columns if col in df.columns]
        
        if len(available_features) == 0:
            raise ValueError("Aucune feature disponible dans le DataFrame")
        
        X = df[available_features].fillna(0).values
        y = df['stock_final'].values
        
        print(f"Features utilisées: {len(available_features)}")
        print(f"Échantillons: {len(X)}")
        
        return X, y, available_features
    
    def optimize_hyperparameters(self, X_train: np.ndarray, y_train: np.ndarray, 
                                X_val: np.ndarray, y_val: np.ndarray, n_trials: int = 100) -> Dict:
        """Optimise les hyperparamètres avec Optuna"""
        
        def objective(trial):
            params = {
                'objective': 'reg:squarederror',
                'eval_metric': 'rmse',
                'booster': 'gbtree',
                'verbosity': 0,
                'seed': 42,
                
                # Paramètres à optimiser
                'n_estimators': trial.suggest_int('n_estimators', 100, 1000),
                'max_depth': trial.suggest_int('max_depth', 3, 10),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
                'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
                'gamma': trial.suggest_float('gamma', 0, 0.5),
                'reg_alpha': trial.suggest_float('reg_alpha', 0, 1),
                'reg_lambda': trial.suggest_float('reg_lambda', 0, 1)
            }
            
            model = xgb.XGBRegressor(**params)
            model.fit(X_train, y_train, 
                     eval_set=[(X_val, y_val)], 
                     early_stopping_rounds=50, 
                     verbose=False)
            
            y_pred = model.predict(X_val)
            rmse = np.sqrt(mean_squared_error(y_val, y_pred))
            
            return rmse
        
        print("Optimisation des hyperparamètres avec Optuna...")
        study = optuna.create_study(direction='minimize')
        study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
        
        best_params = study.best_params
        best_params.update({
            'objective': 'reg:squarederror',
            'eval_metric': 'rmse',
            'booster': 'gbtree',
            'verbosity': 0,
            'seed': 42
        })
        
        print(f"Meilleur RMSE: {study.best_value:.4f}")
        print(f"Meilleurs paramètres: {best_params}")
        
        return best_params
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray, 
             X_val: np.ndarray, y_val: np.ndarray, 
             feature_names: List[str], optimize: bool = True) -> Dict:
        """Entraîne le modèle XGBoost"""
        
        with mlflow.start_run(run_name=f"xgboost_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
            
            # Optimisation des hyperparamètres
            if optimize:
                self.best_params = self.optimize_hyperparameters(X_train, y_train, X_val, y_val)
            else:
                self.best_params = {
                    'objective': 'reg:squarederror',
                    'eval_metric': 'rmse',
                    'n_estimators': 500,
                    'max_depth': 6,
                    'learning_rate': 0.1,
                    'subsample': 0.8,
                    'colsample_bytree': 0.8,
                    'min_child_weight': 1,
                    'gamma': 0,
                    'reg_alpha': 0,
                    'reg_lambda': 1,
                    'seed': 42
                }
            
            # Entraînement du modèle final
            print("\nEntraînement du modèle final...")
            self.model = xgb.XGBRegressor(**self.best_params)
            
            self.model.fit(
                X_train, y_train,
                eval_set=[(X_train, y_train), (X_val, y_val)],
                eval_names=['train', 'val'],
                early_stopping_rounds=50,
                verbose=False
            )
            
            self.is_fitted = True
            
            # Prédictions
            y_train_pred = self.model.predict(X_train)
            y_val_pred = self.model.predict(X_val)
            
            # Métriques d'entraînement
            train_metrics = self.calculate_metrics(y_train, y_train_pred, "Train")
            val_metrics = self.calculate_metrics(y_val, y_val_pred, "Validation")
            
            # Feature importance
            self.feature_importance = pd.DataFrame({
                'feature': feature_names,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            # Log dans MLflow
            mlflow.log_params(self.best_params)
            mlflow.log_metrics({
                'train_mae': train_metrics['mae'],
                'train_rmse': train_metrics['rmse'],
                'train_r2': train_metrics['r2'],
                'val_mae': val_metrics['mae'],
                'val_rmse': val_metrics['rmse'],
                'val_r2': val_metrics['r2']
            })
            
            mlflow.xgboost.log_model(self.model, "model")
            
            # Résultats
            results = {
                'train_metrics': train_metrics,
                'val_metrics': val_metrics,
                'feature_importance': self.feature_importance,
                'best_params': self.best_params
            }
            
            self.print_results(results)
            
            return results
    
    def calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, dataset_name: str) -> Dict:
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
        
        print("\n=== RÉSULTATS XGBOOST ===")
        
        train_metrics = results['train_metrics']
        val_metrics = results['val_metrics']
        
        print(f"\nMétriques d'entraînement:")
        print(f"  MAE: {train_metrics['mae']:.4f}")
        print(f"  RMSE: {train_metrics['rmse']:.4f}")
        print(f"  MAPE: {train_metrics['mape']:.2f}%")
        print(f"  R²: {train_metrics['r2']:.4f}")
        
        print(f"\nMétriques de validation:")
        print(f"  MAE: {val_metrics['mae']:.4f}")
        print(f"  RMSE: {val_metrics['rmse']:.4f}")
        print(f"  MAPE: {val_metrics['mape']:.2f}%")
        print(f"  R²: {val_metrics['r2']:.4f}")
        
        print(f"\nTop 10 features importantes:")
        for i, row in results['feature_importance'].head(10).iterrows():
            print(f"  {row['feature']}: {row['importance']:.4f}")
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Fait des prédictions"""
        
        if not self.is_fitted:
            raise ValueError("Le modèle doit être entraîné avant de faire des prédictions")
        
        return self.model.predict(X)
    
    def predict_with_uncertainty(self, X: np.ndarray, n_estimators: int = None) -> Tuple[np.ndarray, np.ndarray]:
        """Prédictions avec estimation d'incertitude"""
        
        if not self.is_fitted:
            raise ValueError("Le modèle doit être entraîné avant de faire des prédictions")
        
        # Prédictions de base
        predictions = self.model.predict(X)
        
        # Estimation d'incertitude basée sur les arbres individuels
        if n_estimators is None:
            n_estimators = min(100, self.model.n_estimators)
        
        # Prédictions de sous-ensembles d'arbres
        tree_predictions = []
        step = max(1, self.model.n_estimators // n_estimators)
        
        for i in range(0, self.model.n_estimators, step):
            temp_model = xgb.XGBRegressor(**self.best_params)
            temp_model._Booster = self.model._Booster
            temp_model.n_estimators = min(i + step, self.model.n_estimators)
            
            pred = temp_model.predict(X, iteration_range=(0, temp_model.n_estimators))
            tree_predictions.append(pred)
        
        tree_predictions = np.array(tree_predictions)
        uncertainty = np.std(tree_predictions, axis=0)
        
        return predictions, uncertainty
    
    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict:
        """Évalue le modèle sur des données de test"""
        
        if not self.is_fitted:
            raise ValueError("Le modèle doit être entraîné avant l'évaluation")
        
        y_pred = self.predict(X_test)
        test_metrics = self.calculate_metrics(y_test, y_pred, "Test")
        
        print("\n=== ÉVALUATION SUR DONNÉES DE TEST ===")
        print(f"MAE: {test_metrics['mae']:.4f}")
        print(f"RMSE: {test_metrics['rmse']:.4f}")
        print(f"MAPE: {test_metrics['mape']:.2f}%")
        print(f"R²: {test_metrics['r2']:.4f}")
        
        return test_metrics
    
    def plot_feature_importance(self, top_n: int = 20):
        """Visualise l'importance des features"""
        
        if self.feature_importance is None:
            raise ValueError("Le modèle doit être entraîné pour afficher l'importance des features")
        
        plt.figure(figsize=(12, 8))
        
        top_features = self.feature_importance.head(top_n)
        
        sns.barplot(data=top_features, x='importance', y='feature')
        plt.title(f'Top {top_n} Features Importantes - XGBoost')
        plt.xlabel('Importance')
        plt.ylabel('Features')
        plt.tight_layout()
        plt.show()
    
    def plot_predictions(self, y_true: np.ndarray, y_pred: np.ndarray, title: str = "Prédictions XGBoost"):
        """Visualise les prédictions vs valeurs réelles"""
        
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        
        # Scatter plot
        axes[0].scatter(y_true, y_pred, alpha=0.6)
        axes[0].plot([y_true.min(), y_true.max()], [y_true.min(), y_true.max()], 'r--', lw=2)
        axes[0].set_xlabel('Valeurs Réelles')
        axes[0].set_ylabel('Prédictions')
        axes[0].set_title(f'{title} - Scatter Plot')
        axes[0].grid(True, alpha=0.3)
        
        # Résidus
        residuals = y_true - y_pred
        axes[1].scatter(y_pred, residuals, alpha=0.6)
        axes[1].axhline(y=0, color='r', linestyle='--')
        axes[1].set_xlabel('Prédictions')
        axes[1].set_ylabel('Résidus')
        axes[1].set_title(f'{title} - Résidus')
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    def plot_learning_curves(self):
        """Visualise les courbes d'apprentissage"""
        
        if not self.is_fitted:
            raise ValueError("Le modèle doit être entraîné pour afficher les courbes d'apprentissage")
        
        results = self.model.evals_result()
        
        plt.figure(figsize=(12, 5))
        
        # RMSE
        plt.subplot(1, 2, 1)
        plt.plot(results['train']['rmse'], label='Train')
        plt.plot(results['val']['rmse'], label='Validation')
        plt.xlabel('Iterations')
        plt.ylabel('RMSE')
        plt.title('Courbes d\'apprentissage - RMSE')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # Feature importance (top 15)
        plt.subplot(1, 2, 2)
        top_features = self.feature_importance.head(15)
        plt.barh(range(len(top_features)), top_features['importance'])
        plt.yticks(range(len(top_features)), top_features['feature'])
        plt.xlabel('Importance')
        plt.title('Top 15 Features Importantes')
        plt.gca().invert_yaxis()
        
        plt.tight_layout()
        plt.show()
    
    def save_model(self, output_dir: str = 'models/xgboost'):
        """Sauvegarde le modèle"""
        
        if not self.is_fitted:
            raise ValueError("Le modèle doit être entraîné avant la sauvegarde")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Sauvegarder le modèle
        joblib.dump(self.model, f'{output_dir}/xgboost_model.pkl')
        
        # Sauvegarder les métadonnées
        metadata = {
            'best_params': self.best_params,
            'feature_importance': self.feature_importance.to_dict('records')
        }
        joblib.dump(metadata, f'{output_dir}/xgboost_metadata.pkl')
        
        print(f"Modèle XGBoost sauvegardé dans {output_dir}")
    
    def load_model(self, input_dir: str = 'models/xgboost'):
        """Charge le modèle"""
        
        # Charger le modèle
        self.model = joblib.load(f'{input_dir}/xgboost_model.pkl')
        
        # Charger les métadonnées
        metadata = joblib.load(f'{input_dir}/xgboost_metadata.pkl')
        self.best_params = metadata['best_params']
        self.feature_importance = pd.DataFrame(metadata['feature_importance'])
        
        self.is_fitted = True
        print(f"Modèle XGBoost chargé depuis {input_dir}")

def main():
    """Fonction principale pour tester le modèle XGBoost"""
    
    # Charger les données préprocessées
    print("Chargement des données...")
    train_df = pd.read_csv('data/processed/train.csv')
    val_df = pd.read_csv('data/processed/val.csv')
    test_df = pd.read_csv('data/processed/test.csv')
    
    # Charger les noms des features
    feature_columns = joblib.load('models/preprocessor/feature_columns.pkl')
    
    # Créer le modèle
    xgb_predictor = XGBoostPredictor()
    
    # Préparer les données
    print("Préparation des features...")
    X_train, y_train, feature_names = xgb_predictor.prepare_features(train_df, feature_columns)
    X_val, y_val, _ = xgb_predictor.prepare_features(val_df, feature_columns)
    X_test, y_test, _ = xgb_predictor.prepare_features(test_df, feature_columns)
    
    # Entraînement
    print("\nEntraînement du modèle XGBoost...")
    results = xgb_predictor.train(X_train, y_train, X_val, y_val, feature_names, optimize=True)
    
    # Évaluation sur les données de test
    print("\nÉvaluation sur les données de test...")
    test_metrics = xgb_predictor.evaluate(X_test, y_test)
    
    # Visualisations
    print("\nGénération des visualisations...")
    y_test_pred = xgb_predictor.predict(X_test)
    xgb_predictor.plot_predictions(y_test, y_test_pred, "Test Set")
    xgb_predictor.plot_feature_importance()
    xgb_predictor.plot_learning_curves()
    
    # Sauvegarde
    print("\nSauvegarde du modèle...")
    xgb_predictor.save_model()
    
    print("\nEntraînement XGBoost terminé avec succès!")

if __name__ == "__main__":
    main()