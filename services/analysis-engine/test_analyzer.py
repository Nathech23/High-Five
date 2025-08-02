import sys
sys.path.append('.')

from app.data.manual_labels import MANUAL_SENTIMENT_LABELS, REAL_THEMES
from app.nlp_analyzer import FeedbackAnalyzer

# Test de l'analyseur
analyzer = FeedbackAnalyzer()

test_feedbacks = [
    "Excellent service.",
    "Long wait.", 
    "Professional doctor.",
    "Unknown feedback here"
]

print("=== TEST DE L'ANALYSEUR ===")
for feedback in test_feedbacks:
    result = analyzer.analyze_feedback(feedback)
    print(f"\n--- {feedback} ---")
    print(f"Sentiment: {result['sentiment']} (Rating: {result['predicted_rating']})")
    print(f"Themes: {result['themes']}")
    print(f"Urgent: {result['is_urgent']}")
    print(f"Keywords: {result['keywords']}")