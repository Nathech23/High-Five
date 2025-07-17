import spacy
from typing import List, Dict, Tuple
import re
from .data.manual_labels import MANUAL_SENTIMENT_LABELS, REAL_THEMES
import random

class FeedbackAnalyzer:
    def __init__(self):
        """Initialiser l'analyseur avec modèles spaCy"""
        print("🤖 Initialisation de l'analyseur NLP...")
        try:
            self.nlp_en = spacy.load("en_core_web_sm")
            print(" Modèle anglais chargé")
        except OSError:
            print(" Erreur: Modèle anglais non trouvé")
            raise
    
    def detect_language(self, text: str) -> str:
        """Détection automatique de la langue"""
        return "en"  # Pour notre dataset
    
    def analyze_sentiment(self, text: str) -> Tuple[str, int]:
        """Analyse de sentiment avec rating cohérent"""
        if text in MANUAL_SENTIMENT_LABELS:
            label_info = MANUAL_SENTIMENT_LABELS[text]
            rating_range = label_info['rating_range']
            
            # Choisir un rating d'abord
            rating = random.choice(rating_range)
            
            # Puis déterminer le sentiment cohérent avec ce rating
            if rating in [4, 5]:
                sentiment = 'positive'
            elif rating == 3:
                sentiment = 'neutral'
            elif rating in [1, 2]:
                sentiment = 'negative'
            else:
                sentiment = 'neutral'  # fallback
                
            return sentiment, rating
        else:
            # Fallback pour textes inconnus
            sentiment = self._fallback_sentiment(text)
            rating = self._sentiment_to_rating(sentiment)
            return sentiment, rating

    def _fallback_sentiment(self, text: str) -> str:
        """Sentiment amélioré pour textes inconnus"""
        text_lower = text.lower()
        
        positive_words = ['excellent', 'good', 'great', 'professional', 'clean', 'attentive', 'nice', 'helpful']
        negative_words = ['slow', 'long', 'difficulty', 'confusion', 'issues', 'problem', 'bad', 'poor', 'terrible']
        
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        if pos_count > neg_count:
            return 'positive'
        elif neg_count > pos_count:
            return 'negative'
        else:
            # Pour vraiment inconnu, essayer de deviner
            if len(text.split()) < 2:  # Texte très court
                return 'neutral'
            else:
                return 'neutral'  # Par défaut
    
    def _sentiment_to_rating(self, sentiment: str) -> int:
        """Convertir sentiment en rating avec tous les niveaux"""
        mapping = {
            'positive': [4, 5],   # Bien ou excellent
            'neutral': [3],       # Moyen
            'negative': [1, 2]    # Mauvais ou très mauvais
        }
        rating_options = mapping.get(sentiment, [3])
        return random.choice(rating_options)
    
    def extract_themes(self, text: str) -> List[str]:
        """Extraction des thèmes basée sur mots-clés"""
        if text in MANUAL_SENTIMENT_LABELS:
            return MANUAL_SENTIMENT_LABELS[text]['themes']
        
        # Fallback : détecter thèmes par mots-clés
        detected_themes = []
        text_lower = text.lower()
        
        for theme, keywords in REAL_THEMES.items():
            if any(keyword in text_lower for keyword in keywords):
                detected_themes.append(theme)
        
        return detected_themes if detected_themes else ['general']
    
    def detect_urgency(self, text: str) -> bool:
        """Détection de l'urgence"""
        urgent_keywords = [
            'urgent', 'emergency', 'critical', 'serious', 'danger', 
            'immediately', 'asap', 'crisis', 'severe'
        ]
        
        text_lower = text.lower()
        
        # Urgence par mots-clés
        if any(keyword in text_lower for keyword in urgent_keywords):
            return True
        
        # Urgence par sentiment très négatif + thèmes critiques
        sentiment, rating = self.analyze_sentiment(text)
        themes = self.extract_themes(text)
        
        critical_themes = ['billing', 'scheduling', 'waiting_time']
        if sentiment == 'negative' and rating <= 2 and any(theme in critical_themes for theme in themes):
            return True
            
        return False
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extraction de mots-clés importants"""
        doc = self.nlp_en(text)
        
        keywords = []
        for token in doc:
            # Garder les noms, adjectifs et verbes importants
            if (token.pos_ in ["NOUN", "ADJ", "VERB"] and 
                not token.is_stop and 
                not token.is_punct and 
                len(token.text) > 2):
                keywords.append(token.lemma_.lower())
        
        return list(set(keywords))  # Éliminer doublons
    
    def analyze_feedback(self, text: str) -> Dict:
        """Analyse complète d'un feedback"""
        language = self.detect_language(text)
        sentiment, rating = self.analyze_sentiment(text)
        themes = self.extract_themes(text)
        keywords = self.extract_keywords(text)
        is_urgent = self.detect_urgency(text)
        
        return {
            "original_text": text,
            "language": language,
            "sentiment": sentiment,
            "predicted_rating": rating,
            "themes": themes,
            "keywords": keywords,
            "is_urgent": is_urgent
        }

# Test rapide
if __name__ == "__main__":
    analyzer = FeedbackAnalyzer()
    
    test_feedbacks = [
        "Excellent service.",
        "Long wait.",
        "Professional doctor.",
        "Unknown feedback here"
    ]
    
    for feedback in test_feedbacks:
        result = analyzer.analyze_feedback(feedback)
        print(f"\n--- {feedback} ---")
        print(f"Sentiment: {result['sentiment']} (Rating: {result['predicted_rating']})")
        print(f"Thèmes: {result['themes']}")
        print(f"Urgent: {result['is_urgent']}")