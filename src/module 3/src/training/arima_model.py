import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
import joblib
import os
from typing import Dict, List, Tuple, Optional
from sklearn.metrics import mean_absolute_error, mean_squared_error
import mlflow
import mlflow.sklearn
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')

class ARIMAPredictor:
    """Modèle ARIMA pour la prédiction des stocks de sang"""
    
    def __init__(self, experiment_name: str = "blood_stock_arima"):
        self.models = {}  # Un modèle par combinaison hôpital/type_sang
        self.model_params = {}
        self.experiment_name = experiment_name
        self.is_fitted = False
        
        # Configuration MLflow
        mlflow.set_experiment(experiment_name)
    
    def check_stationarity(self, timeseries: pd.Series, title: str = "Series") -> bool:
        """Vérifie la stationnarité d'une série temporelle"""
        
        # Test de Dickey-Fuller
        result = adfuller(timeseries.dropna())
        
        print(f'\n=== Test de Stationnarité pour {title} ===')
        print(f'ADF Statistic: {result[0]:.6f}')
        print(f'p-value: {result[1]:.6f}')
        print('Critical Values:')
        for key, value in result[4].items():
            print(f'\t{key}: {value:.3f}')
        
        is_stationary = result[1] <= 0.05
        print(f'Série stationnaire: {"Oui" if is_stationary else "Non"}')
        
        return is_stationary
    
    def make_stationary(self, timeseries: pd.Series, max_diff: int = 2) -> Tuple[pd.Series, int]:
        """Rend une série stationnaire par différenciation"""
        
        original_series = timeseries.copy()
        diff_order = 0
        
        for d in range(max_diff + 1):
            if self.check_stationarity(timeseries, f"Différence d={d}"):
                diff_order = d
                break
            
            if d < max_diff:
                timeseries = timeseries.diff().dropna()
        
        return timeseries, diff_order
    
    def find_optimal_params(self, timeseries: pd.Series, max_p: int = 5, max_q: int = 5) -> Tuple[int, int, int]:
        """Trouve les paramètres optimaux (p,d,q) pour ARIMA"""
        
        # Rendre la série stationnaire
        stationary_series, d = self.make_stationary(timeseries)
        
        best_aic = float('inf')
        best_params = (0, d, 0)
        
        print(f"\nRecherche des paramètres optimaux (max_p={max_p}, d={d}, max_q={max_q})...")
        
        for p in range(max_p + 1):
            for q in range(max_q + 1):
                try:
                    model = ARIMA(timeseries, order=(p, d, q))
                    fitted_model = model.fit()
                    
                    if fitted_model.aic < best_aic:
                        best_aic = fitted_model.aic
                        best_params = (p, d, q)
                        
                except Exception as e:
                    continue
        
        print(f"Meilleurs paramètres: ARIMA{best_params} avec AIC={best_aic:.2f}")
        return best_params
    
    def prepare_time_series_data(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """Prépare les données en séries temporelles par hôpital/type de sang"""
        
        df = df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        time_series_data = {}
        
        for hospital in df['hospital'].unique():
            for blood_type in df['blood_type'].unique():
                key = f"{hospital}_{blood_type}".replace(' ', '_').replace('\'', '')
                
                subset = df[(df['hospital'] == hospital) & (df['blood_type'] == blood_type)].copy()
                
                if len(subset) >= 30:  # Minimum de données pour ARIMA
                    # Créer une série temporelle avec index datetime
                    subset = subset.set_index('timestamp')
                    
                    # Rééchantillonnage quotidien avec moyenne
                    daily_series = subset['stock_final'].resample('D').mean().fillna(method='ffill')
                    
                    time_series_data[key] = daily_series
        
        print(f"Séries temporelles créées: {len(time_series_data)}")
        return time_series_data
    
    def train_single_model(self, timeseries: pd.Series, key: str) -> Dict:
        """Entraîne un modèle ARIMA pour une série temporelle"""
        
        print(f"\n=== Entraînement ARIMA pour {key} ===")
        print(f"Longueur de la série: {len(timeseries)}")
        
        # Vérifier qu'il y a assez de données
        if len(timeseries) < 30:
            print(f"Pas assez de données pour {key}")
            return None
        
        # Trouver les paramètres optimaux
        try:
            p, d, q = self.find_optimal_params(timeseries)
            
            # Entraîner le modèle
            model = ARIMA(timeseries, order=(p, d, q))
            fitted_model = model.fit()
            
            # Métriques sur les données d'entraînement
            predictions = fitted_model.fittedvalues
            mae = mean_absolute_error(timeseries[1:], predictions[1:])  # Skip first value
            rmse = np.sqrt(mean_squared_error(timeseries[1:], predictions[1:]))
            mape = np.mean(np.abs((timeseries[1:] - predictions[1:]) / timeseries[1:])) * 100
            
            model_info = {
                'model': fitted_model,
                'params': (p, d, q),
                'aic': fitted_model.aic,
                'bic': fitted_model.bic,
                'mae': mae,
                'rmse': rmse,
                'mape': mape,
                'series_length': len(timeseries)
            }
            
            print(f"Paramètres: ARIMA({p},{d},{q})")
            print(f"AIC: {fitted_model.aic:.2f}")
            print(f"MAE: {mae:.2f}")
            print(f"RMSE: {rmse:.2f}")
            print(f"MAPE: {mape:.2f}%")
            
            return model_info
            
        except Exception as e:
            print(f"Erreur lors de l'entraînement pour {key}: {str(e)}")
            return None
    
    def train(self, df: pd.DataFrame) -> Dict:
        """Entraîne tous les modèles ARIMA"""
        
        with mlflow.start_run(run_name=f"arima_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
            
            # Préparer les données
            time_series_data = self.prepare_time_series_data(df)
            
            training_results = {}
            successful_models = 0
            
            for key, timeseries in time_series_data.items():
                model_info = self.train_single_model(timeseries, key)
                
                if model_info is not None:
                    self.models[key] = model_info['model']
                    self.model_params[key] = model_info
                    training_results[key] = model_info
                    successful_models += 1
            
            self.is_fitted = True
            
            # Métriques globales
            if training_results:
                avg_mae = np.mean([info['mae'] for info in training_results.values()])
                avg_rmse = np.mean([info['rmse'] for info in training_results.values()])
                avg_mape = np.mean([info['mape'] for info in training_results.values()])
                
                # Log des métriques dans MLflow
                mlflow.log_metric("avg_mae", avg_mae)
                mlflow.log_metric("avg_rmse", avg_rmse)
                mlflow.log_metric("avg_mape", avg_mape)
                mlflow.log_metric("successful_models", successful_models)
                mlflow.log_metric("total_series", len(time_series_data))
                
                print(f"\n=== RÉSULTATS GLOBAUX ===")
                print(f"Modèles entraînés avec succès: {successful_models}/{len(time_series_data)}")
                print(f"MAE moyenne: {avg_mae:.2f}")
                print(f"RMSE moyenne: {avg_rmse:.2f}")
                print(f"MAPE moyenne: {avg_mape:.2f}%")
            
            return training_results
    
    def predict(self, hospital: str, blood_type: str, steps: int = 7) -> Dict:
        """Fait des prédictions pour un hôpital et type de sang spécifique"""
        
        if not self.is_fitted:
            raise ValueError("Le modèle doit être entraîné avant de faire des prédictions")
        
        key = f"{hospital}_{blood_type}".replace(' ', '_').replace('\'', '')
        
        if key not in self.models:
            raise ValueError(f"Aucun modèle trouvé pour {hospital} - {blood_type}")
        
        model = self.models[key]
        
        # Prédictions
        forecast = model.forecast(steps=steps)
        conf_int = model.get_forecast(steps=steps).conf_int()
        
        # Créer les dates futures
        last_date = model.data.dates[-1]
        future_dates = pd.date_range(start=last_date + timedelta(days=1), periods=steps, freq='D')
        
        predictions = {
            'dates': future_dates,
            'predictions': forecast.values,
            'lower_bound': conf_int.iloc[:, 0].values,
            'upper_bound': conf_int.iloc[:, 1].values,
            'model_params': self.model_params[key]['params']
        }
        
        return predictions
    
    def predict_all(self, steps: int = 7) -> Dict:
        """Fait des prédictions pour tous les modèles"""
        
        all_predictions = {}
        
        for key in self.models.keys():
            try:
                # Extraire hospital et blood_type du key
                parts = key.split('_')
                if len(parts) >= 2:
                    hospital = ' '.join(parts[:-1]).replace('_', ' ')
                    blood_type = parts[-1]
                    
                    predictions = self.predict(hospital, blood_type, steps)
                    all_predictions[key] = predictions
                    
            except Exception as e:
                print(f"Erreur de prédiction pour {key}: {str(e)}")
        
        return all_predictions
    
    def evaluate_model(self, df_test: pd.DataFrame) -> Dict:
        """Évalue les modèles sur des données de test"""
        
        test_series_data = self.prepare_time_series_data(df_test)
        evaluation_results = {}
        
        for key, test_series in test_series_data.items():
            if key in self.models:
                model = self.models[key]
                
                # Prédictions sur la période de test
                n_test = len(test_series)
                if n_test > 0:
                    try:
                        forecast = model.forecast(steps=n_test)
                        
                        mae = mean_absolute_error(test_series, forecast)
                        rmse = np.sqrt(mean_squared_error(test_series, forecast))
                        mape = np.mean(np.abs((test_series - forecast) / test_series)) * 100
                        
                        evaluation_results[key] = {
                            'mae': mae,
                            'rmse': rmse,
                            'mape': mape,
                            'test_length': n_test
                        }
                        
                    except Exception as e:
                        print(f"Erreur d'évaluation pour {key}: {str(e)}")
        
        return evaluation_results
    
    def save_models(self, output_dir: str = 'models/arima'):
        """Sauvegarde tous les modèles"""
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Sauvegarder chaque modèle
        for key, model in self.models.items():
            model_path = f'{output_dir}/arima_{key}.pkl'
            joblib.dump(model, model_path)
        
        # Sauvegarder les paramètres
        joblib.dump(self.model_params, f'{output_dir}/model_params.pkl')
        
        print(f"Modèles ARIMA sauvegardés dans {output_dir}")
    
    def load_models(self, input_dir: str = 'models/arima'):
        """Charge tous les modèles"""
        
        # Charger les paramètres
        self.model_params = joblib.load(f'{input_dir}/model_params.pkl')
        
        # Charger chaque modèle
        for key in self.model_params.keys():
            model_path = f'{input_dir}/arima_{key}.pkl'
            if os.path.exists(model_path):
                self.models[key] = joblib.load(model_path)
        
        self.is_fitted = True
        print(f"Modèles ARIMA chargés depuis {input_dir}")
    
    def plot_predictions(self, hospital: str, blood_type: str, df_historical: pd.DataFrame, steps: int = 30):
        """Visualise les prédictions"""
        
        # Préparer les données historiques
        historical_data = df_historical[
            (df_historical['hospital'] == hospital) & 
            (df_historical['blood_type'] == blood_type)
        ].copy()
        
        historical_data['timestamp'] = pd.to_datetime(historical_data['timestamp'])
        historical_data = historical_data.set_index('timestamp').sort_index()
        daily_historical = historical_data['stock_final'].resample('D').mean()
        
        # Faire les prédictions
        predictions = self.predict(hospital, blood_type, steps)
        
        # Créer le graphique
        plt.figure(figsize=(15, 8))
        
        # Données historiques
        plt.plot(daily_historical.index[-60:], daily_historical.values[-60:], 
                label='Données historiques', color='blue', linewidth=2)
        
        # Prédictions
        plt.plot(predictions['dates'], predictions['predictions'], 
                label='Prédictions ARIMA', color='red', linewidth=2)
        
        # Intervalle de confiance
        plt.fill_between(predictions['dates'], 
                        predictions['lower_bound'], 
                        predictions['upper_bound'], 
                        alpha=0.3, color='red', label='Intervalle de confiance')
        
        plt.title(f'Prédictions ARIMA - {hospital} - {blood_type}')
        plt.xlabel('Date')
        plt.ylabel('Stock de sang')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show()

def main():
    """Fonction principale pour tester le modèle ARIMA"""
    
    # Charger les données
    print("Chargement des données...")
    df = pd.read_csv('data/processed/train.csv')
    
    # Créer et entraîner le modèle
    arima_predictor = ARIMAPredictor()
    
    print("Entraînement des modèles ARIMA...")
    training_results = arima_predictor.train(df)
    
    # Sauvegarder les modèles
    print("\nSauvegarde des modèles...")
    arima_predictor.save_models()
    
    # Faire des prédictions
    print("\nPrédictions pour les 7 prochains jours...")
    all_predictions = arima_predictor.predict_all(steps=7)
    
    # Afficher quelques prédictions
    for key, pred in list(all_predictions.items())[:3]:
        print(f"\n{key}:")
        for i, (date, value) in enumerate(zip(pred['dates'], pred['predictions'])):
            print(f"  {date.strftime('%Y-%m-%d')}: {value:.1f} unités")
    
    print("\nEntraînement ARIMA terminé avec succès!")

if __name__ == "__main__":
    main()