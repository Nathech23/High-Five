import pandas as pd
import numpy as np

# Charger le dataset
df = pd.read_csv(r'C:\Code2Care\High-Five\services\analysis-engine\app\data\patient_feedback.csv')

print("=== EXPLORATION DU DATASET ===")
print(f"Nombre de lignes : {len(df)}")
print(f"Nombre de colonnes : {len(df.columns)}")
print("\nColonnes disponibles :")
print(df.columns.tolist())

print("\n=== APERÇU DES DONNÉES ===")
print(df.head(5))

print("\n=== INFO GÉNÉRALES ===")
print(df.info())

print("\n=== ANALYSE DU TEXTE ===")
print(f"Feedbacks non vides : {df['feedback_text'].notna().sum()}")
print(f"Feedbacks vides : {df['feedback_text'].isna().sum()}")

# Longueur des textes
df['text_length'] = df['feedback_text'].str.len()
print(f"Longueur moyenne : {df['text_length'].mean():.1f} caractères")
print(f"Longueur min : {df['text_length'].min()}")
print(f"Longueur max : {df['text_length'].max()}")

print("\n=== EXEMPLES DE FEEDBACKS ===")
for i in range(3):
    print(f"\n--- Feedback {i+1} ---")
    print(f"Rating: {df.iloc[i]['rating']}")
    print(f"Département: {df.iloc[i]['department']}")
    print(f"Texte: {df.iloc[i]['feedback_text']}")

print("\n=== DISTRIBUTION DES RATINGS ===")
print(df['rating'].value_counts().sort_index())

print("\n=== DÉPARTEMENTS ===")
print(df['department'].value_counts())

print("\n=== EXEMPLES DE FEEDBACKS PAR RATING ===")
# Nettoyer les données - enlever les NaN
df_clean = df[df['feedback_text'].notna()].copy()

for rating in [1, 3, 5]:
    feedback_sample = df_clean[df_clean['rating'] == rating]['feedback_text'].iloc[0]
    print(f"\nRating {rating}: {feedback_sample}")

print("\n=== LONGUEUR PAR RATING ===")
avg_length_by_rating = df_clean.groupby('rating')['text_length'].mean()
print(avg_length_by_rating)

print(f"\n=== RÉSUMÉ POUR L'ANALYSE ===")
print(f" Feedbacks à analyser : {len(df_clean)}")
print(f" Langue principale : Anglais")
print(f" Ratings : {df_clean['rating'].min()} à {df_clean['rating'].max()}")
print(f" Départements : {df_clean['department'].nunique()} différents")

print("\n=== DIAGNOSTIC DES RATINGS BIZARRES ===")
print("Valeurs uniques de rating :")
unique_ratings = df['rating'].unique()
print(sorted(unique_ratings))

print(f"\nNombre total de ratings : {len(df)}")
print(f"Ratings valides (1-5) : {len(df[df['rating'].isin([1,2,3,4,5])])}")
print(f"Ratings bizarres : {len(df[~df['rating'].isin([1,2,3,4,5])])}")

print("\n=== EXEMPLES DE RATINGS BIZARRES ===")
weird_ratings = df[~df['rating'].isin([1,2,3,4,5])].head(3)
print(weird_ratings[['feedback_id', 'rating', 'feedback_text']])

print("\n=== NETTOYAGE DES DONNÉES ===")
# Garder seulement les ratings valides (1-5) et les textes non vides
df_clean = df[
    (df['rating'].isin([1, 2, 3, 4, 5])) & 
    (df['feedback_text'].notna())
].copy()

print(f" Données nettoyées : {len(df_clean)} feedbacks")
print(f" Ratings supprimés : {len(df) - len(df_clean)}")

print("\n=== DISTRIBUTION APRÈS NETTOYAGE ===")
print(df_clean['rating'].value_counts().sort_index())

# Sauvegarder le dataset propre
df_clean.to_csv('patient_feedback_clean.csv', index=False)
print(f"\n Dataset propre sauvegardé : patient_feedback_clean.csv")