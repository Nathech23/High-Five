import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential, Model
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization, Input
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
from tensorflow.keras.regularizers import l1_l2
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import os
from typing import Dict, List, Tuple, Optional
import mlflow
import mlflow.tensorflow
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Configuration TensorFlow
tf.random.set_seed(42)
np.random.seed(42)

class LSTMPredictor:
    """Modèle LSTM pour la prédiction de séquences temporelles des stocks de sang"""
    
    def __init__(self, sequence_length: int = 30, experiment_name: str = "blood_stock_lstm"):
        self.sequence_length = sequence_length
        self.model = None
        self.scaler = MinMaxScaler()
        self.is_fitted = False
        self.history = None
        self.experiment_name = experiment_name
        
        # Configuration MLflow
        mlflow.set_experiment(experiment_name)
    
    def create_sequences(self, data: np.ndarray, target: np.ndarray = None) -> Tuple[np.ndarray, np.ndarray]:
        """Crée des séquences pour l'entraînement LSTM"""
        
        X, y = [], []
        
        for i in range(self.sequence_length, len(data)):
            X.append(data[i-self.sequence_length:i])
            if target is not None:
                y.append(target[i])
            else:
                y.append(data[i, 0])  # Première colonne comme target par défaut
        
        return np.array(X), np.array(y)
    
    def prepare_data_by_series(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """Prépare les données par série temporelle (hôpital + type de sang)"""
        
        df = df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        series_data = {}
        
        # Features numériques pour les séquences
        numeric_features = [
            'stock_initial', 'demand', 'supply', 'temperature', 'days_to_expiry', 
            'quality_score', 'hour', 'day_of_week', 'month', 'is_weekend'
        ]
        
        # Filtrer les features disponibles
        available_features = [col for col in numeric_features if col in df.columns]
        
        for hospital in df['hospital'].unique():
            for blood_type in df['blood_type'].unique():
                key = f"{hospital}_{blood_type}".replace(' ', '_').replace('\'', '')
                
                subset = df[
                    (df['hospital'] == hospital) & 
                    (df['blood_type'] == blood_type)
                ].copy()
                
                if len(subset) >= self.sequence_length + 10:  # Minimum de données
                    # Préparer les features et target
                    features = subset[available_features].values
                    target = subset['stock_final'].values
                    
                    # Normalisation
                    scaler_features = MinMaxScaler()
                    scaler_target = MinMaxScaler()
                    
                    features_scaled = scaler_features.fit_transform(features)
                    target_scaled = scaler_target.fit_transform(target.reshape(-1, 1)).flatten()
                    
                    # Créer les séquences
                    X, y = self.create_sequences(features_scaled, target_scaled)
                    
                    if len(X) > 0:
                        series_data[key] = {
                            'X': X,
                            'y': y,
                            'scaler_features': scaler_features,
                            'scaler_target': scaler_target,
                            'feature_names': available_features,
                            'original_data': subset
                        }
        
        print(f"Séries temporelles préparées: {len(series_data)}")
        return series_data
    
    def combine_series_data(self, series_data: Dict) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """Combine toutes les séries en un dataset unique"""
        
        all_X = []
        all_y = []
        series_keys = []
        
        for key, data in series_data.items():
            all_X.append(data['X'])
            all_y.append(data['y'])
            series_keys.extend([key] * len(data['X']))
        
        if all_X:
            X_combined = np.vstack(all_X)
            y_combined = np.hstack(all_y)
        else:
            X_combined = np.array([])
            y_combined = np.array([])
        
        return X_combined, y_combined, series_keys
    
    def build_model(self, input_shape: Tuple[int, int], architecture: str = 'standard') -> Model:
        """Construit l'architecture LSTM"""
        
        model = Sequential()
        
        if architecture == 'standard':
            # Architecture standard
            model.add(LSTM(128, return_sequences=True, input_shape=input_shape,
                          kernel_regularizer=l1_l2(l1=0.01, l2=0.01)))
            model.add(Dropout(0.2))
            model.add(BatchNormalization())
            
            model.add(LSTM(64, return_sequences=True,
                          kernel_regularizer=l1_l2(l1=0.01, l2=0.01)))
            model.add(Dropout(0.2))
            model.add(BatchNormalization())
            
            model.add(LSTM(32, return_sequences=False,
                          kernel_regularizer=l1_l2(l1=0.01, l2=0.01)))
            model.add(Dropout(0.2))
            
            model.add(Dense(16, activation='relu'))
            model.add(Dropout(0.1))
            model.add(Dense(1, activation='linear'))
            
        elif architecture == 'deep':
            # Architecture plus profonde
            model.add(LSTM(256, return_sequences=True, input_shape=input_shape))
            model.add(Dropout(0.3))
            model.add(BatchNormalization())
            
            model.add(LSTM(128, return_sequences=True))
            model.add(Dropout(0.3))
            model.add(BatchNormalization())
            
            model.add(LSTM(64, return_sequences=True))
            model.add(Dropout(0.2))
            model.add(BatchNormalization())
            
            model.add(LSTM(32, return_sequences=False))
            model.add(Dropout(0.2))
            
            model.add(Dense(32, activation='relu'))
            model.add(Dropout(0.1))
            model.add(Dense(16, activation='relu'))
            model.add(Dense(1, activation='linear'))
            
        elif architecture == 'lightweight':
            # Architecture légère
            model.add(LSTM(64, return_sequences=True, input_shape=input_shape))
            model.add(Dropout(0.2))
            
            model.add(LSTM(32, return_sequences=False))
            model.add(Dropout(0.2))
            
            model.add(Dense(16, activation='relu'))
            model.add(Dense(1, activation='linear'))
        
        return model
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray,
             X_val: np.ndarray, y_val: np.ndarray,
             architecture: str = 'standard',
             epochs: int = 100,
             batch_size: int = 32,
             learning_rate: float = 0.001) -> Dict:
        """Entraîne le modèle LSTM"""
        
        with mlflow.start_run(run_name=f"lstm_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
            
            print(f"\n=== ENTRAÎNEMENT LSTM ===")
            print(f"Architecture: {architecture}")
            print(f"Forme des données d'entraînement: {X_train.shape}")
            print(f"Forme des données de validation: {X_val.shape}")
            
            # Construire le modèle
            input_shape = (X_train.shape[1], X_train.shape[2])
            self.model = self.build_model(input_shape, architecture)
            
            # Compiler le modèle
            optimizer = Adam(learning_rate=learning_rate)
            self.model.compile(
                optimizer=optimizer,
                loss='mse',
                metrics=['mae']
            )
            
            print(f"\nArchitecture du modèle:")
            self.model.summary()
            
            # Callbacks
            callbacks = [
                EarlyStopping(
                    monitor='val_loss',
                    patience=15,
                    restore_best_weights=True,
                    verbose=1
                ),
                ReduceLROnPlateau(
                    monitor='val_loss',
                    factor=0.5,
                    patience=8,
                    min_lr=1e-7,
                    verbose=1
                ),
                ModelCheckpoint(
                    'models/lstm/best_model.h5',
                    monitor='val_loss',
                    save_best_only=True,
                    verbose=1
                )
            ]
            
            # Créer le dossier pour les modèles
            os.makedirs('models/lstm', exist_ok=True)
            
            # Entraînement
            print("\nDébut de l'entraînement...")
            self.history = self.model.fit(
                X_train, y_train,
                validation_data=(X_val, y_val),
                epochs=epochs,
                batch_size=batch_size,
                callbacks=callbacks,
                verbose=1
            )
            
            self.is_fitted = True
            
            # Prédictions
            y_train_pred = self.model.predict(X_train)
            y_val_pred = self.model.predict(X_val)
            
            # Métriques
            train_metrics = self.calculate_metrics(y_train, y_train_pred, "Train")
            val_metrics = self.calculate_metrics(y_val, y_val_pred, "Validation")
            
            # Log dans MLflow
            mlflow.log_params({
                'architecture': architecture,
                'sequence_length': self.sequence_length,
                'epochs': epochs,
                'batch_size': batch_size,
                'learning_rate': learning_rate
            })
            
            mlflow.log_metrics({
                'train_mae': train_metrics['mae'],
                'train_rmse': train_metrics['rmse'],
                'val_mae': val_metrics['mae'],
                'val_rmse': val_metrics['rmse']
            })
            
            mlflow.tensorflow.log_model(self.model, "model")
            
            # Résultats
            results = {
                'train_metrics': train_metrics,
                'val_metrics': val_metrics,
                'history': self.history.history,
                'architecture': architecture
            }
            
            self.print_results(results)
            
            return results
    
    def calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, dataset_name: str) -> Dict:
        """Calcule les métriques de performance"""
        
        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mape = np.mean(np.abs((y_true - y_pred) / (y_true + 1e-8))) * 100
        
        metrics = {
            'mae': mae,
            'rmse': rmse,
            'mape': mape
        }
        
        return metrics
    
    def print_results(self, results: Dict):
        """Affiche les résultats d'entraînement"""
        
        print("\n=== RÉSULTATS LSTM ===")
        
        train_metrics = results['train_metrics']
        val_metrics = results['val_metrics']
        
        print(f"\nMétriques d'entraînement:")
        print(f"  MAE: {train_metrics['mae']:.4f}")
        print(f"  RMSE: {train_metrics['rmse']:.4f}")
        print(f"  MAPE: {train_metrics['mape']:.2f}%")
        
        print(f"\nMétriques de validation:")
        print(f"  MAE: {val_metrics['mae']:.4f}")
        print(f"  RMSE: {val_metrics['rmse']:.4f}")
        print(f"  MAPE: {val_metrics['mape']:.2f}%")
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Fait des prédictions"""
        
        if not self.is_fitted:
            raise ValueError("Le modèle doit être entraîné avant de faire des prédictions")
        
        return self.model.predict(X)
    
    def predict_sequence(self, initial_sequence: np.ndarray, steps: int = 7) -> np.ndarray:
        """Prédit une séquence future"""
        
        if not self.is_fitted:
            raise ValueError("Le modèle doit être entraîné avant de faire des prédictions")
        
        predictions = []
        current_sequence = initial_sequence.copy()
        
        for _ in range(steps):
            # Prédire le prochain point
            next_pred = self.model.predict(current_sequence.reshape(1, *current_sequence.shape))[0, 0]
            predictions.append(next_pred)
            
            # Mettre à jour la séquence (faire glisser la fenêtre)
            new_row = current_sequence[-1].copy()
            new_row[0] = next_pred  # Remplacer la première feature (stock) par la prédiction
            
            current_sequence = np.vstack([current_sequence[1:], new_row])
        
        return np.array(predictions)
    
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
        
        return test_metrics
    
    def plot_training_history(self):
        """Visualise l'historique d'entraînement"""
        
        if self.history is None:
            raise ValueError("Le modèle doit être entraîné pour afficher l'historique")
        
        fig, axes = plt.subplots(1, 2, figsize=(15, 5))
        
        # Loss
        axes[0].plot(self.history.history['loss'], label='Train Loss')
        axes[0].plot(self.history.history['val_loss'], label='Validation Loss')
        axes[0].set_title('Évolution de la Loss')
        axes[0].set_xlabel('Epochs')
        axes[0].set_ylabel('Loss')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # MAE
        axes[1].plot(self.history.history['mae'], label='Train MAE')
        axes[1].plot(self.history.history['val_mae'], label='Validation MAE')
        axes[1].set_title('Évolution du MAE')
        axes[1].set_xlabel('Epochs')
        axes[1].set_ylabel('MAE')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    def plot_predictions(self, y_true: np.ndarray, y_pred: np.ndarray, title: str = "Prédictions LSTM"):
        """Visualise les prédictions vs valeurs réelles"""
        
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        
        # Scatter plot
        axes[0].scatter(y_true, y_pred, alpha=0.6)
        axes[0].plot([y_true.min(), y_true.max()], [y_true.min(), y_true.max()], 'r--', lw=2)
        axes[0].set_xlabel('Valeurs Réelles')
        axes[0].set_ylabel('Prédictions')
        axes[0].set_title(f'{title} - Scatter Plot')
        axes[0].grid(True, alpha=0.3)
        
        # Time series (échantillon)
        sample_size = min(200, len(y_true))
        indices = np.random.choice(len(y_true), sample_size, replace=False)
        indices = np.sort(indices)
        
        axes[1].plot(indices, y_true[indices], label='Réel', alpha=0.7)
        axes[1].plot(indices, y_pred[indices], label='Prédit', alpha=0.7)
        axes[1].set_xlabel('Index')
        axes[1].set_ylabel('Valeur')
        axes[1].set_title(f'{title} - Série Temporelle (échantillon)')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    def save_model(self, output_dir: str = 'models/lstm'):
        """Sauvegarde le modèle"""
        
        if not self.is_fitted:
            raise ValueError("Le modèle doit être entraîné avant la sauvegarde")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Sauvegarder le modèle TensorFlow
        self.model.save(f'{output_dir}/lstm_model.h5')
        
        # Sauvegarder les métadonnées
        metadata = {
            'sequence_length': self.sequence_length,
            'history': self.history.history if self.history else None
        }
        joblib.dump(metadata, f'{output_dir}/lstm_metadata.pkl')
        
        print(f"Modèle LSTM sauvegardé dans {output_dir}")
    
    def load_model(self, input_dir: str = 'models/lstm'):
        """Charge le modèle"""
        
        # Charger le modèle TensorFlow
        self.model = tf.keras.models.load_model(f'{input_dir}/lstm_model.h5')
        
        # Charger les métadonnées
        metadata = joblib.load(f'{input_dir}/lstm_metadata.pkl')
        self.sequence_length = metadata['sequence_length']
        
        self.is_fitted = True
        print(f"Modèle LSTM chargé depuis {input_dir}")

def main():
    """Fonction principale pour tester le modèle LSTM"""
    
    # Charger les données
    print("Chargement des données...")
    train_df = pd.read_csv('data/processed/train.csv')
    val_df = pd.read_csv('data/processed/val.csv')
    test_df = pd.read_csv('data/processed/test.csv')
    
    # Créer le modèle
    lstm_predictor = LSTMPredictor(sequence_length=30)
    
    # Préparer les données par série
    print("Préparation des données par série...")
    train_series = lstm_predictor.prepare_data_by_series(train_df)
    val_series = lstm_predictor.prepare_data_by_series(val_df)
    test_series = lstm_predictor.prepare_data_by_series(test_df)
    
    # Combiner toutes les séries
    print("Combinaison des séries...")
    X_train, y_train, _ = lstm_predictor.combine_series_data(train_series)
    X_val, y_val, _ = lstm_predictor.combine_series_data(val_series)
    X_test, y_test, _ = lstm_predictor.combine_series_data(test_series)
    
    if len(X_train) == 0:
        print("Pas assez de données pour l'entraînement LSTM")
        return
    
    # Entraînement
    print("\nEntraînement du modèle LSTM...")
    results = lstm_predictor.train(
        X_train, y_train, X_val, y_val,
        architecture='standard',
        epochs=50,
        batch_size=32
    )
    
    # Évaluation sur les données de test
    if len(X_test) > 0:
        print("\nÉvaluation sur les données de test...")
        test_metrics = lstm_predictor.evaluate(X_test, y_test)
        
        # Visualisations
        print("\nGénération des visualisations...")
        y_test_pred = lstm_predictor.predict(X_test)
        lstm_predictor.plot_predictions(y_test, y_test_pred, "Test Set")
    
    lstm_predictor.plot_training_history()
    
    # Sauvegarde
    print("\nSauvegarde du modèle...")
    lstm_predictor.save_model()
    
    print("\nEntraînement LSTM terminé avec succès!")

if __name__ == "__main__":
    main()