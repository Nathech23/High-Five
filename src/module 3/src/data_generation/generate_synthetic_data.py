import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os
from typing import Dict, List

class BloodStockDataGenerator:
    """Générateur de données synthétiques pour les stocks de sang"""
    
    def __init__(self, seed: int = 42):
        np.random.seed(seed)
        random.seed(seed)
        
        self.blood_types = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
        self.blood_type_distribution = [0.34, 0.06, 0.09, 0.02, 0.03, 0.01, 0.38, 0.07]
        
        self.hospitals = [
            'Hôpital Général Douala', 'Hôpital Laquintinie', 'Hôpital de District Bonassama',
            'Clinique des Spécialités', 'Centre Médical d\'Excellence', 'Hôpital Militaire'
        ]
        
        self.quality_comments = [
            'Excellent état, conservation parfaite',
            'Bon état général, légère variation température',
            'État satisfaisant, contrôle qualité OK',
            'Attention: proche expiration',
            'Urgent: vérifier température stockage',
            'Parfait pour transfusion immédiate',
            'Contrôle bactériologique négatif',
            'Hémoglobine dans les normes'
        ]
    
    def generate_time_series_data(self, start_date: str, end_date: str, n_records: int = 10000) -> pd.DataFrame:
        """Génère des données de time series pour les stocks de sang"""
        
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Génération des timestamps
        timestamps = []
        for i in range(n_records):
            random_date = start + timedelta(
                seconds=random.randint(0, int((end - start).total_seconds()))
            )
            timestamps.append(random_date)
        
        timestamps.sort()
        
        data = []
        
        for i, timestamp in enumerate(timestamps):
            # Simulation de patterns saisonniers et hebdomadaires
            day_of_week = timestamp.weekday()
            hour = timestamp.hour
            month = timestamp.month
            
            # Facteurs d'influence
            weekend_factor = 0.7 if day_of_week >= 5 else 1.0
            night_factor = 0.5 if hour < 6 or hour > 22 else 1.0
            seasonal_factor = 1.2 if month in [12, 1, 7, 8] else 1.0
            
            # Sélection du type de sang
            blood_type = np.random.choice(self.blood_types, p=self.blood_type_distribution)
            hospital = random.choice(self.hospitals)
            
            # Génération des stocks avec patterns réalistes
            base_stock = np.random.normal(50, 15)
            stock_current = max(0, int(base_stock * weekend_factor * night_factor * seasonal_factor))
            
            # Demande basée sur des patterns réalistes
            base_demand = np.random.normal(8, 3)
            demand = max(0, int(base_demand * weekend_factor * seasonal_factor))
            
            # Stock après demande
            stock_after_demand = max(0, stock_current - demand)
            
            # Approvisionnement (simulation de livraisons)
            supply = 0
            if random.random() < 0.3:  # 30% de chance d'approvisionnement
                supply = np.random.poisson(20)
            
            # Stock final
            stock_final = stock_after_demand + supply
            
            # Température de stockage (doit être entre 2-6°C)
            temperature = np.random.normal(4, 0.5)
            temperature = max(1, min(8, temperature))  # Contraintes physiques
            
            # Durée de conservation (jours restants)
            days_to_expiry = max(1, int(np.random.exponential(15)))
            
            # Qualité basée sur température et expiration
            quality_score = 100
            if temperature < 2 or temperature > 6:
                quality_score -= 20
            if days_to_expiry < 5:
                quality_score -= 15
            if days_to_expiry < 2:
                quality_score -= 25
            
            quality_score = max(0, min(100, quality_score + np.random.normal(0, 5)))
            
            # Classification urgence
            urgency = 'normale'
            if stock_final < 10:
                urgency = 'critique'
            elif stock_final < 20:
                urgency = 'faible'
            elif quality_score < 70:
                urgency = 'attention'
            
            # Commentaire qualité
            comment = random.choice(self.quality_comments)
            if urgency == 'critique':
                comment = f"URGENT: Stock critique - {comment}"
            elif temperature < 2 or temperature > 6:
                comment = f"ATTENTION TEMPÉRATURE: {comment}"
            
            record = {
                'timestamp': timestamp,
                'hospital': hospital,
                'blood_type': blood_type,
                'stock_initial': stock_current,
                'demand': demand,
                'supply': supply,
                'stock_final': stock_final,
                'temperature': round(temperature, 1),
                'days_to_expiry': days_to_expiry,
                'quality_score': round(quality_score, 1),
                'urgency': urgency,
                'quality_comment': comment,
                'day_of_week': day_of_week,
                'hour': hour,
                'month': month,
                'is_weekend': day_of_week >= 5,
                'is_holiday_season': month in [12, 1, 7, 8]
            }
            
            data.append(record)
        
        df = pd.DataFrame(data)
        return df.sort_values('timestamp').reset_index(drop=True)
    
    def add_external_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ajoute des facteurs externes influençant les stocks"""
        
        # Événements spéciaux
        special_events = []
        for _, row in df.iterrows():
            event = 'normal'
            if random.random() < 0.05:  # 5% de chance d'événement spécial
                events = ['accident_route', 'épidémie', 'campagne_don', 'urgence_médicale']
                event = random.choice(events)
            special_events.append(event)
        
        df['special_event'] = special_events
        
        # Météo (influence sur les dons)
        weather_conditions = []
        for _ in range(len(df)):
            weather = random.choices(
                ['ensoleillé', 'pluvieux', 'orageux', 'nuageux'],
                weights=[0.4, 0.3, 0.1, 0.2]
            )[0]
            weather_conditions.append(weather)
        
        df['weather'] = weather_conditions
        
        return df
    
    def save_data(self, df: pd.DataFrame, output_dir: str = 'data/synthetic'):
        """Sauvegarde les données générées"""
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Sauvegarde complète
        df.to_csv(f'{output_dir}/blood_stock_data.csv', index=False)
        
        # Sauvegarde par hôpital
        for hospital in df['hospital'].unique():
            hospital_data = df[df['hospital'] == hospital]
            filename = hospital.replace(' ', '_').replace('\'', '').lower()
            hospital_data.to_csv(f'{output_dir}/{filename}.csv', index=False)
        
        # Sauvegarde par type de sang
        for blood_type in df['blood_type'].unique():
            blood_data = df[df['blood_type'] == blood_type]
            blood_data.to_csv(f'{output_dir}/blood_type_{blood_type.replace("+", "pos").replace("-", "neg")}.csv', index=False)
        
        print(f"Données sauvegardées dans {output_dir}")
        print(f"Total des enregistrements: {len(df)}")
        print(f"Période: {df['timestamp'].min()} à {df['timestamp'].max()}")
        print(f"Hôpitaux: {df['hospital'].nunique()}")
        print(f"Types de sang: {df['blood_type'].nunique()}")

def main():
    """Fonction principale pour générer les données"""
    
    generator = BloodStockDataGenerator()
    
    # Génération des données sur 2 ans
    start_date = '2022-01-01'
    end_date = '2024-01-01'
    n_records = 12000
    
    print(f"Génération de {n_records} enregistrements...")
    df = generator.generate_time_series_data(start_date, end_date, n_records)
    
    print("Ajout des facteurs externes...")
    df = generator.add_external_factors(df)
    
    print("Sauvegarde des données...")
    generator.save_data(df)
    
    # Statistiques
    print("\n=== STATISTIQUES ====")
    print(f"Moyenne stock final: {df['stock_final'].mean():.1f}")
    print(f"Médiane stock final: {df['stock_final'].median():.1f}")
    print(f"Stock critique (< 10): {(df['stock_final'] < 10).sum()} ({(df['stock_final'] < 10).mean()*100:.1f}%)")
    print(f"Température hors norme: {((df['temperature'] < 2) | (df['temperature'] > 6)).sum()}")
    print(f"Qualité < 70: {(df['quality_score'] < 70).sum()}")
    
    print("\n=== RÉPARTITION PAR URGENCE ====")
    print(df['urgency'].value_counts())
    
    print("\n=== RÉPARTITION PAR TYPE DE SANG ====")
    print(df['blood_type'].value_counts())

if __name__ == "__main__":
    main()