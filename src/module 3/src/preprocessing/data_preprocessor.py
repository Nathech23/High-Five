import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder, MinMaxScaler
from sklearn.model_selection import train_test_split
import joblib
import os
from typing import Tuple, Dict, List
import warnings
warnings.filterwarnings('ignore')

class BloodStockPreprocessor:
    """Préprocesseur pour les données de stocks de sang"""
    
    def __init__(self):
        self.scalers = {}
        self.encoders = {}
        self.feature_columns = []
        self.target_column = 'stock_final'
        
    def load_data(self, file_path: str) -> pd.DataFrame:
        """Charge les données depuis un fichier CSV"""
        df = pd.read_csv(file_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    
    def create_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Crée des features temporelles avancées"""
        df = df.copy()
        
        # Features temporelles de base
        df['year'] = df['timestamp'].dt.year
        df['month'] = df['timestamp'].dt.month
        df['day'] = df['timestamp'].dt.day
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['day_of_year'] = df['timestamp'].dt.dayofyear
        df['week_of_year'] = df['timestamp'].dt.isocalendar().week
        
        # Features cycliques (pour capturer la nature cyclique du temps)
        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
        df['day_sin'] = np.sin(2 * np.pi * df['day'] / 31)
        df['day_cos'] = np.cos(2 * np.pi * df['day'] / 31)
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        df['dow_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['dow_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        
        # Features booléennes
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
        df['is_monday'] = (df['day_of_week'] == 0).astype(int)
        df['is_friday'] = (df['day_of_week'] == 4).astype(int)
        df['is_night'] = ((df['hour'] >= 22) | (df['hour'] <= 6)).astype(int)
        df['is_business_hours'] = ((df['hour'] >= 8) & (df['hour'] <= 18)).astype(int)
        
        # Saisons
        df['season'] = df['month'].map({
            12: 'winter', 1: 'winter', 2: 'winter',
            3: 'spring', 4: 'spring', 5: 'spring',
            6: 'summer', 7: 'summer', 8: 'summer',
            9: 'autumn', 10: 'autumn', 11: 'autumn'
        })
        
        # Périodes spéciales
        df['is_holiday_season'] = df['month'].isin([12, 1, 7, 8]).astype(int)
        df['is_end_of_month'] = (df['day'] >= 25).astype(int)
        df['is_beginning_of_month'] = (df['day'] <= 5).astype(int)
        
        return df
    
    def create_lag_features(self, df: pd.DataFrame, target_col: str = 'stock_final', lags: List[int] = [1, 2, 3, 7, 14]) -> pd.DataFrame:
        """Crée des features de lag pour la prédiction temporelle"""
        df = df.copy()
        df = df.sort_values('timestamp')
        
        # Features de lag par hôpital et type de sang
        for hospital in df['hospital'].unique():
            for blood_type in df['blood_type'].unique():
                mask = (df['hospital'] == hospital) & (df['blood_type'] == blood_type)
                subset = df[mask].copy()
                
                if len(subset) > max(lags):
                    for lag in lags:
                        col_name = f'{target_col}_lag_{lag}_{hospital}_{blood_type}'.replace(' ', '_').replace('\'', '')
                        df.loc[mask, col_name] = subset[target_col].shift(lag)
        
        # Features de lag globales
        for lag in lags:
            df[f'{target_col}_lag_{lag}'] = df.groupby(['hospital', 'blood_type'])[target_col].shift(lag)
        
        # Rolling statistics
        windows = [3, 7, 14, 30]
        for window in windows:
            df[f'{target_col}_rolling_mean_{window}'] = df.groupby(['hospital', 'blood_type'])[target_col].rolling(window=window, min_periods=1).mean().reset_index(0, drop=True)
            df[f'{target_col}_rolling_std_{window}'] = df.groupby(['hospital', 'blood_type'])[target_col].rolling(window=window, min_periods=1).std().reset_index(0, drop=True)
            df[f'{target_col}_rolling_min_{window}'] = df.groupby(['hospital', 'blood_type'])[target_col].rolling(window=window, min_periods=1).min().reset_index(0, drop=True)
            df[f'{target_col}_rolling_max_{window}'] = df.groupby(['hospital', 'blood_type'])[target_col].rolling(window=window, min_periods=1).max().reset_index(0, drop=True)
        
        return df
    
    def create_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Crée des features d'interaction"""
        df = df.copy()
        
        # Interactions entre stock et demande
        df['stock_demand_ratio'] = df['stock_initial'] / (df['demand'] + 1)
        df['supply_demand_ratio'] = df['supply'] / (df['demand'] + 1)
        df['stock_supply_interaction'] = df['stock_initial'] * df['supply']
        
        # Interactions avec la température
        df['temp_quality_interaction'] = df['temperature'] * df['quality_score']
        df['temp_deviation'] = abs(df['temperature'] - 4)  # Déviation de la température optimale
        
        # Interactions avec l'expiration
        df['expiry_quality_interaction'] = df['days_to_expiry'] * df['quality_score']
        df['expiry_stock_ratio'] = df['stock_final'] / (df['days_to_expiry'] + 1)
        
        # Features de densité
        df['stock_per_day_to_expiry'] = df['stock_final'] / (df['days_to_expiry'] + 1)
        df['demand_intensity'] = df['demand'] / (df['stock_initial'] + 1)
        
        return df
    
    def encode_categorical_features(self, df: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """Encode les features catégorielles"""
        df = df.copy()
        
        categorical_columns = ['hospital', 'blood_type', 'urgency', 'special_event', 'weather', 'season']
        
        for col in categorical_columns:
            if col in df.columns:
                if fit:
                    if col not in self.encoders:
                        self.encoders[col] = LabelEncoder()
                    df[f'{col}_encoded'] = self.encoders[col].fit_transform(df[col].astype(str))
                else:
                    if col in self.encoders:
                        # Gérer les nouvelles catégories
                        unique_values = set(df[col].astype(str).unique())
                        known_values = set(self.encoders[col].classes_)
                        new_values = unique_values - known_values
                        
                        if new_values:
                            # Ajouter les nouvelles valeurs à l'encodeur
                            all_values = list(known_values) + list(new_values)
                            self.encoders[col].classes_ = np.array(all_values)
                        
                        df[f'{col}_encoded'] = self.encoders[col].transform(df[col].astype(str))
        
        # One-hot encoding pour certaines variables
        onehot_columns = ['blood_type', 'urgency', 'weather']
        for col in onehot_columns:
            if col in df.columns:
                dummies = pd.get_dummies(df[col], prefix=col)
                df = pd.concat([df, dummies], axis=1)
        
        return df
    
    def scale_numerical_features(self, df: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """Scale les features numériques"""
        df = df.copy()
        
        # Features à scaler
        numerical_columns = [
            'stock_initial', 'demand', 'supply', 'temperature', 'days_to_expiry', 'quality_score',
            'stock_demand_ratio', 'supply_demand_ratio', 'temp_deviation', 'expiry_stock_ratio'
        ]
        
        # Ajouter les features de lag et rolling
        lag_columns = [col for col in df.columns if 'lag_' in col or 'rolling_' in col]
        numerical_columns.extend(lag_columns)
        
        # Filtrer les colonnes qui existent
        numerical_columns = [col for col in numerical_columns if col in df.columns]
        
        if fit:
            self.scalers['numerical'] = StandardScaler()
            df[numerical_columns] = self.scalers['numerical'].fit_transform(df[numerical_columns].fillna(0))
        else:
            if 'numerical' in self.scalers:
                df[numerical_columns] = self.scalers['numerical'].transform(df[numerical_columns].fillna(0))
        
        return df
    
    def prepare_features(self, df: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """Pipeline complet de préparation des features"""
        print("Création des features temporelles...")
        df = self.create_time_features(df)
        
        print("Création des features de lag...")
        df = self.create_lag_features(df)
        
        print("Création des features d'interaction...")
        df = self.create_interaction_features(df)
        
        print("Encodage des features catégorielles...")
        df = self.encode_categorical_features(df, fit=fit)
        
        print("Scaling des features numériques...")
        df = self.scale_numerical_features(df, fit=fit)
        
        # Sélection des features finales
        if fit:
            # Exclure les colonnes non-features
            exclude_columns = [
                'timestamp', 'hospital', 'blood_type', 'urgency', 'special_event', 'weather', 'season',
                'quality_comment', 'stock_final'  # target
            ]
            
            self.feature_columns = [col for col in df.columns if col not in exclude_columns]
            print(f"Features sélectionnées: {len(self.feature_columns)}")
        
        return df
    
    def split_data(self, df: pd.DataFrame, test_size: float = 0.2, val_size: float = 0.1) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Divise les données en train/validation/test avec respect de l'ordre temporel"""
        df = df.sort_values('timestamp')
        
        n = len(df)
        train_end = int(n * (1 - test_size - val_size))
        val_end = int(n * (1 - test_size))
        
        train_df = df.iloc[:train_end]
        val_df = df.iloc[train_end:val_end]
        test_df = df.iloc[val_end:]
        
        print(f"Train: {len(train_df)} ({len(train_df)/n*100:.1f}%)")
        print(f"Validation: {len(val_df)} ({len(val_df)/n*100:.1f}%)")
        print(f"Test: {len(test_df)} ({len(test_df)/n*100:.1f}%)")
        
        return train_df, val_df, test_df
    
    def get_features_and_target(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """Extrait les features et le target"""
        X = df[self.feature_columns].fillna(0)
        y = df[self.target_column]
        return X, y
    
    def save_preprocessor(self, output_dir: str = 'models/preprocessor'):
        """Sauvegarde le préprocesseur"""
        os.makedirs(output_dir, exist_ok=True)
        
        joblib.dump(self.scalers, f'{output_dir}/scalers.pkl')
        joblib.dump(self.encoders, f'{output_dir}/encoders.pkl')
        joblib.dump(self.feature_columns, f'{output_dir}/feature_columns.pkl')
        
        print(f"Préprocesseur sauvegardé dans {output_dir}")
    
    def load_preprocessor(self, input_dir: str = 'models/preprocessor'):
        """Charge le préprocesseur"""
        self.scalers = joblib.load(f'{input_dir}/scalers.pkl')
        self.encoders = joblib.load(f'{input_dir}/encoders.pkl')
        self.feature_columns = joblib.load(f'{input_dir}/feature_columns.pkl')
        
        print(f"Préprocesseur chargé depuis {input_dir}")

def main():
    """Fonction principale pour tester le préprocesseur"""
    
    preprocessor = BloodStockPreprocessor()
    
    # Charger les données
    print("Chargement des données...")
    df = preprocessor.load_data('data/synthetic/blood_stock_data.csv')
    print(f"Données chargées: {len(df)} enregistrements")
    
    # Préparation des features
    print("\nPréparation des features...")
    df_processed = preprocessor.prepare_features(df, fit=True)
    
    # Division des données
    print("\nDivision des données...")
    train_df, val_df, test_df = preprocessor.split_data(df_processed)
    
    # Extraction features/target
    X_train, y_train = preprocessor.get_features_and_target(train_df)
    X_val, y_val = preprocessor.get_features_and_target(val_df)
    X_test, y_test = preprocessor.get_features_and_target(test_df)
    
    print(f"\nShapes finales:")
    print(f"X_train: {X_train.shape}")
    print(f"X_val: {X_val.shape}")
    print(f"X_test: {X_test.shape}")
    
    # Sauvegarde
    print("\nSauvegarde du préprocesseur...")
    preprocessor.save_preprocessor()
    
    # Sauvegarde des données préprocessées
    os.makedirs('data/processed', exist_ok=True)
    train_df.to_csv('data/processed/train.csv', index=False)
    val_df.to_csv('data/processed/val.csv', index=False)
    test_df.to_csv('data/processed/test.csv', index=False)
    
    print("Préprocessing terminé avec succès!")

if __name__ == "__main__":
    main()