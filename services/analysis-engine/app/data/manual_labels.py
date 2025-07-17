# Labels avec RANGES de sentiment ET rating
MANUAL_SENTIMENT_LABELS = {
    'Excellent service.': {
        'sentiment_range': ['positive'],  # Sans ambiguïté
        'rating_range': [5],
        'themes': ['service_quality', 'satisfaction']
    },
    'Attentive staff.': {
        'sentiment_range': ['positive'],  # Clairement positif
        'rating_range': [4, 5],
        'themes': ['staff_quality', 'care_quality']
    },
    'Clean facilities.': {
        'sentiment_range': ['neutral', 'positive'],  # Dépend des attentes
        'rating_range': [3, 4, 5],
        'themes': ['cleanliness', 'facilities']
    },
    'Professional doctor.': {
        'sentiment_range': ['neutral', 'positive'],  # Minimum attendu ou exceptionnel ?
        'rating_range': [3, 4, 5],
        'themes': ['staff_quality', 'professionalism']
    },
    'Well informed.': {
        'sentiment_range': ['neutral', 'positive'],  # Plutôt bien
        'rating_range': [3, 4],
        'themes': ['communication', 'information_quality']
    },
    'Long wait.': {
        'sentiment_range': ['negative'],  # Sans ambiguïté
        'rating_range': [1, 2],
        'themes': ['waiting_time', 'delays']
    },
    'Slow lab.': {
        'sentiment_range': ['negative', 'neutral'],  # Dépend de la gravité
        'rating_range': [2, 3],
        'themes': ['efficiency', 'lab_services']
    },
    'Parking difficulty.': {
        'sentiment_range': ['negative', 'neutral'],  # Peut être juste gênant
        'rating_range': [2, 3],
        'themes': ['parking', 'access_issues']
    },
    'Scheduling issues.': {
        'sentiment_range': ['negative'],  # Problème organisationnel
        'rating_range': [1, 2],
        'themes': ['scheduling', 'organization']
    },
    'Billing confusion.': {
        'sentiment_range': ['negative'],  # Problème sérieux
        'rating_range': [1, 2],
        'themes': ['billing', 'administrative_issues']
    }
}

REAL_THEMES = {
    "service_quality": ["service", "quality", "excellent"],
    "staff_quality": ["staff", "attentive", "professional", "doctor"],
    "waiting_time": ["wait", "long", "slow"],
    "efficiency": ["slow", "quick", "fast"],
    "cleanliness": ["clean", "facilities"],
    "parking": ["parking", "difficulty"],
    "scheduling": ["scheduling", "issues"],
    "billing": ["billing", "confusion"],
    "communication": ["informed", "well"],
    "care_quality": ["attentive", "care"],
    "professionalism": ["professional"],
    "administrative_issues": ["billing", "scheduling"],
    "access_issues": ["parking", "difficulty"],
    "delays": ["long", "slow", "wait"],
    "facilities": ["clean", "facilities"],
    "information_quality": ["informed", "well"],
    "lab_services": ["lab", "slow"],
    "organization": ["scheduling", "issues"],
    "satisfaction": ["excellent"]
}

# Correspondances logiques
SENTIMENT_RATING_MAPPING = {
    'positive': [4, 5],
    'neutral': [3],        # CORRIGÉ: seulement 3 !
    'negative': [1, 2]
}

print("=== LABELS AVEC RANGES DE SENTIMENT ===")
for feedback, info in MANUAL_SENTIMENT_LABELS.items():
    sent_str = f"[{', '.join(info['sentiment_range'])}]"
    rating_str = f"[{', '.join(map(str, info['rating_range']))}]"
    print(f"Sentiment {sent_str:20} | Ratings {rating_str:8} | {feedback}")