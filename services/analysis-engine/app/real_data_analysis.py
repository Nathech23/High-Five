import pandas as pd
from collections import Counter
import re

# Charger les données nettoyées
df = pd.read_csv('patient_feedback_clean.csv')

print("=== ANALYSE RÉELLE DES FEEDBACKS ===")
print(f"Nombre total : {len(df)}")

print("\n=== ÉCHANTILLON ALÉATOIRE DE 20 FEEDBACKS ===")
sample_feedbacks = df.sample(20)
for i, row in sample_feedbacks.iterrows():
    print(f"Rating {row['rating']}: {row['feedback_text']}")

print("\n=== FEEDBACKS PAR RATING ===")
for rating in [1, 2, 3, 4, 5]:
    print(f"\n--- RATING {rating} (10 exemples) ---")
    examples = df[df['rating'] == rating]['feedback_text'].head(10)
    for feedback in examples:
        print(f"  • {feedback}")


import pandas as pd

df = pd.read_csv('patient_feedback_clean.csv')

print("=== ANALYSE COMPLÈTE DES FEEDBACKS UNIQUES ===")

# Toutes les valeurs uniques de feedback_text
unique_feedbacks = df['feedback_text'].unique()
print(f"Nombre de feedbacks uniques : {len(unique_feedbacks)}")

print("\n=== TOUS LES FEEDBACKS UNIQUES ===")
for i, feedback in enumerate(sorted(unique_feedbacks), 1):
    print(f"{i:2d}. {feedback}")

print("\n=== ANALYSE DES INCOHÉRENCES ===")
# Pour chaque feedback unique, voir tous ses ratings
feedback_ratings = df.groupby('feedback_text')['rating'].apply(list).to_dict()

print("Feedbacks avec plusieurs ratings différents :")
for feedback, ratings in feedback_ratings.items():
    unique_ratings = list(set(ratings))
    if len(unique_ratings) > 1:
        print(f"'{feedback}' → Ratings: {sorted(unique_ratings)}")

print("\n=== DISTRIBUTION DES FEEDBACKS ===")
feedback_counts = df['feedback_text'].value_counts()
print(feedback_counts)