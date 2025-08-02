from app.nlp_analyzer import FeedbackAnalyzer
from app.data.manual_labels import MANUAL_SENTIMENT_LABELS

analyzer = FeedbackAnalyzer()

print("=== VALIDATION DE COHÉRENCE ===")
print("Test : sentiment doit être cohérent avec rating")

coherence_errors = 0
total_tests = 0

# Tester 50 fois chaque feedback connu pour vérifier cohérence
for feedback_text in MANUAL_SENTIMENT_LABELS.keys():
    print(f"\n--- {feedback_text} ---")
    
    sentiments = []
    ratings = []
    
    # Tester 10 fois (à cause du random)
    for i in range(10):
        sentiment, rating = analyzer.analyze_sentiment(feedback_text)
        sentiments.append(sentiment)
        ratings.append(rating)
        total_tests += 1
        
        # Vérifier cohérence
        coherent = False
        if sentiment == 'positive' and rating in [4, 5]:
            coherent = True
        elif sentiment == 'neutral' and rating == 3:
            coherent = True
        elif sentiment == 'negative' and rating in [1, 2]:
            coherent = True
            
        if not coherent:
            coherence_errors += 1
            print(f"   Incohérent : sentiment={sentiment}, rating={rating}")
    
    # Statistiques pour ce feedback
    unique_sentiments = set(sentiments)
    unique_ratings = set(ratings)
    print(f"  Sentiments obtenus : {unique_sentiments}")
    print(f"  Ratings obtenus : {unique_ratings}")

print(f"\n=== RÉSULTATS DE COHÉRENCE ===")
print(f"Tests total : {total_tests}")
print(f"Erreurs de cohérence : {coherence_errors}")
print(f"Taux de cohérence : {(total_tests-coherence_errors)/total_tests*100:.1f}%")

if coherence_errors == 0:
    print(" Parfaite cohérence sentiment ↔ rating !")
else:
    print(" Incohérences détectées - à corriger")