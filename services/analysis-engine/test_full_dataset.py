import pandas as pd
from app.nlp_analyzer import FeedbackAnalyzer
from collections import Counter
import time

# Charger l'analyseur
print("=== CHARGEMENT DE L'ANALYSEUR ===")
analyzer = FeedbackAnalyzer()

# Charger le dataset nettoyé
print("=== CHARGEMENT DU DATASET ===")
df = pd.read_csv('patient_feedback_clean.csv')
print(f"Feedbacks à analyser : {len(df)}")

# Tester sur échantillon d'abord (pour éviter d'attendre 45k analyses)
print("=== TEST SUR ÉCHANTILLON (100 feedbacks) ===")
sample_df = df.sample(100, random_state=42)

results = []
start_time = time.time()

for idx, row in sample_df.iterrows():
    feedback_text = row['feedback_text']
    original_rating = row['rating']
    
    # Analyser
    analysis = analyzer.analyze_feedback(feedback_text)
    
    results.append({
        'original_text': feedback_text,
        'original_rating': original_rating,
        'predicted_sentiment': analysis['sentiment'],
        'predicted_rating': analysis['predicted_rating'],
        'themes': analysis['themes'],
        'is_urgent': analysis['is_urgent'],
        'keywords': analysis['keywords']
    })

end_time = time.time()
print(f"Temps d'analyse : {end_time - start_time:.2f} secondes")
print(f"Vitesse : {len(results)/(end_time - start_time):.1f} feedbacks/seconde")

# Analyser les résultats
results_df = pd.DataFrame(results)

print("\n=== DISTRIBUTION DES SENTIMENTS PRÉDITS ===")
sentiment_counts = Counter(results_df['predicted_sentiment'])
print(sentiment_counts)

print("\n=== DISTRIBUTION DES RATINGS PRÉDITS ===")
rating_counts = Counter(results_df['predicted_rating'])
print(dict(sorted(rating_counts.items())))

print("\n=== THÈMES LES PLUS FRÉQUENTS ===")
all_themes = []
for themes_list in results_df['themes']:
    all_themes.extend(themes_list)
theme_counts = Counter(all_themes)
print(theme_counts.most_common(10))

print("\n=== FEEDBACKS URGENTS DÉTECTÉS ===")
urgent_count = results_df['is_urgent'].sum()
print(f"Feedbacks urgents : {urgent_count}/{len(results_df)} ({urgent_count/len(results_df)*100:.1f}%)")

if urgent_count > 0:
    urgent_feedbacks = results_df[results_df['is_urgent'] == True]
    print("Exemples de feedbacks urgents :")
    for idx, row in urgent_feedbacks.head(3).iterrows():
        print(f"  • {row['original_text']} → {row['predicted_sentiment']} (Rating: {row['predicted_rating']})")