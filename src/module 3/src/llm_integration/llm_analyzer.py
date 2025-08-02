import openai
import pandas as pd
import numpy as np
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
from sentence_transformers import SentenceTransformer
import torch
import re
import json
import os
from typing import Dict, List, Tuple, Optional, Union
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class LLMBloodStockAnalyzer:
    """Analyseur LLM pour les commentaires de qualité et classification d'urgence"""
    
    def __init__(self, openai_api_key: str = None, use_local_models: bool = True):
        self.openai_api_key = openai_api_key
        self.use_local_models = use_local_models
        
        # Modèles locaux
        self.sentiment_analyzer = None
        self.embedding_model = None
        self.classification_model = None
        
        # Cache pour les analyses
        self.analysis_cache = {}
        
        # Configuration OpenAI
        if openai_api_key:
            openai.api_key = openai_api_key
        
        self.initialize_models()
    
    def initialize_models(self):
        """Initialise les modèles LLM locaux"""
        
        print("Initialisation des modèles LLM...")
        
        try:
            # Modèle d'analyse de sentiment
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model="nlptown/bert-base-multilingual-uncased-sentiment",
                device=0 if torch.cuda.is_available() else -1
            )
            print("✓ Modèle de sentiment chargé")
        except Exception as e:
            print(f"✗ Erreur chargement sentiment: {str(e)}")
        
        try:
            # Modèle d'embeddings
            self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            print("✓ Modèle d'embeddings chargé")
        except Exception as e:
            print(f"✗ Erreur chargement embeddings: {str(e)}")
    
    def preprocess_text(self, text: str) -> str:
        """Préprocesse le texte pour l'analyse"""
        
        if not isinstance(text, str):
            return ""
        
        # Nettoyer le texte
        text = re.sub(r'[^\w\s\-\.,;:!?]', '', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.strip().lower()
        
        return text
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extrait les mots-clés importants du texte"""
        
        # Mots-clés critiques pour les stocks de sang
        critical_keywords = {
            'urgence': ['urgent', 'critique', 'immédiat', 'emergency', 'critical'],
            'qualité': ['contamination', 'bactérie', 'infection', 'qualité', 'défaut'],
            'température': ['température', 'froid', 'chaud', 'congélation', 'décongélation'],
            'expiration': ['expiration', 'périmé', 'expire', 'date limite'],
            'stock': ['rupture', 'manque', 'insuffisant', 'vide', 'épuisé'],
            'positif': ['excellent', 'parfait', 'bon', 'satisfaisant', 'optimal']
        }
        
        found_keywords = []
        text_lower = text.lower()
        
        for category, keywords in critical_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    found_keywords.append(f"{category}:{keyword}")
        
        return found_keywords
    
    def analyze_sentiment_local(self, text: str) -> Dict:
        """Analyse le sentiment avec un modèle local"""
        
        if not self.sentiment_analyzer or not text:
            return {'label': 'NEUTRAL', 'score': 0.5}
        
        try:
            result = self.sentiment_analyzer(text[:512])  # Limiter la longueur
            return {
                'label': result[0]['label'],
                'score': result[0]['score']
            }
        except Exception as e:
            print(f"Erreur analyse sentiment: {str(e)}")
            return {'label': 'NEUTRAL', 'score': 0.5}
    
    def classify_urgency_rules(self, text: str, stock_level: float, quality_score: float, 
                              temperature: float, days_to_expiry: int) -> Dict:
        """Classification d'urgence basée sur des règles"""
        
        urgency_score = 0
        reasons = []
        
        # Analyse du texte
        text_lower = text.lower()
        
        # Mots-clés d'urgence
        urgent_keywords = ['urgent', 'critique', 'immédiat', 'attention', 'problème']
        for keyword in urgent_keywords:
            if keyword in text_lower:
                urgency_score += 30
                reasons.append(f"Mot-clé urgent: {keyword}")
        
        # Mots-clés de qualité
        quality_keywords = ['contamination', 'bactérie', 'infection', 'défaut']
        for keyword in quality_keywords:
            if keyword in text_lower:
                urgency_score += 40
                reasons.append(f"Problème qualité: {keyword}")
        
        # Analyse des métriques numériques
        if stock_level < 10:
            urgency_score += 50
            reasons.append(f"Stock critique: {stock_level}")
        elif stock_level < 20:
            urgency_score += 25
            reasons.append(f"Stock faible: {stock_level}")
        
        if quality_score < 70:
            urgency_score += 35
            reasons.append(f"Qualité faible: {quality_score}")
        
        if temperature < 2 or temperature > 6:
            urgency_score += 45
            reasons.append(f"Température hors norme: {temperature}°C")
        
        if days_to_expiry <= 2:
            urgency_score += 40
            reasons.append(f"Expiration imminente: {days_to_expiry} jours")
        elif days_to_expiry <= 5:
            urgency_score += 20
            reasons.append(f"Expiration proche: {days_to_expiry} jours")
        
        # Classification finale
        if urgency_score >= 80:
            urgency_level = 'critique'
        elif urgency_score >= 50:
            urgency_level = 'élevée'
        elif urgency_score >= 25:
            urgency_level = 'modérée'
        else:
            urgency_level = 'normale'
        
        return {
            'urgency_level': urgency_level,
            'urgency_score': min(urgency_score, 100),
            'reasons': reasons
        }
    
    def analyze_with_openai(self, text: str, context: Dict) -> Dict:
        """Analyse avec l'API OpenAI"""
        
        if not self.openai_api_key:
            return self.analyze_with_local_models(text, context)
        
        prompt = f"""
        Analysez ce commentaire sur la qualité du stock de sang dans un contexte médical:
        
        Commentaire: "{text}"
        
        Contexte:
        - Stock actuel: {context.get('stock_level', 'N/A')} unités
        - Score qualité: {context.get('quality_score', 'N/A')}/100
        - Température: {context.get('temperature', 'N/A')}°C
        - Jours avant expiration: {context.get('days_to_expiry', 'N/A')}
        - Hôpital: {context.get('hospital', 'N/A')}
        - Type de sang: {context.get('blood_type', 'N/A')}
        
        Fournissez une analyse JSON avec:
        1. sentiment: positif/négatif/neutre
        2. urgency_level: critique/élevée/modérée/normale
        3. key_issues: liste des problèmes identifiés
        4. recommendations: recommandations d'action
        5. confidence_score: score de confiance (0-1)
        
        Répondez uniquement en JSON valide.
        """
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Vous êtes un expert en gestion des stocks de sang dans un hôpital. Analysez les commentaires de qualité et classifiez l'urgence."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"Erreur OpenAI: {str(e)}")
            return self.analyze_with_local_models(text, context)
    
    def analyze_with_local_models(self, text: str, context: Dict) -> Dict:
        """Analyse avec les modèles locaux"""
        
        # Préprocesser le texte
        clean_text = self.preprocess_text(text)
        
        # Analyse de sentiment
        sentiment_result = self.analyze_sentiment_local(clean_text)
        
        # Classification d'urgence
        urgency_result = self.classify_urgency_rules(
            clean_text,
            context.get('stock_level', 0),
            context.get('quality_score', 100),
            context.get('temperature', 4),
            context.get('days_to_expiry', 30)
        )
        
        # Extraction de mots-clés
        keywords = self.extract_keywords(clean_text)
        
        # Recommandations basées sur l'analyse
        recommendations = self.generate_recommendations(urgency_result, context)
        
        return {
            'sentiment': sentiment_result['label'].lower(),
            'sentiment_score': sentiment_result['score'],
            'urgency_level': urgency_result['urgency_level'],
            'urgency_score': urgency_result['urgency_score'],
            'key_issues': urgency_result['reasons'],
            'keywords': keywords,
            'recommendations': recommendations,
            'confidence_score': 0.8  # Score fixe pour les modèles locaux
        }
    
    def generate_recommendations(self, urgency_result: Dict, context: Dict) -> List[str]:
        """Génère des recommandations basées sur l'analyse"""
        
        recommendations = []
        urgency_level = urgency_result['urgency_level']
        reasons = urgency_result['reasons']
        
        if urgency_level == 'critique':
            recommendations.append("🚨 ACTION IMMÉDIATE REQUISE")
            
            if any('stock' in reason.lower() for reason in reasons):
                recommendations.append("• Contacter immédiatement les donneurs d'urgence")
                recommendations.append("• Vérifier les stocks dans les hôpitaux partenaires")
            
            if any('température' in reason.lower() for reason in reasons):
                recommendations.append("• Vérifier le système de réfrigération")
                recommendations.append("• Isoler les unités affectées")
            
            if any('qualité' in reason.lower() for reason in reasons):
                recommendations.append("• Effectuer des tests de qualité supplémentaires")
                recommendations.append("• Quarantaine préventive")
        
        elif urgency_level == 'élevée':
            recommendations.append("⚠️ Surveillance renforcée nécessaire")
            recommendations.append("• Planifier un réapprovisionnement dans les 24h")
            recommendations.append("• Informer l'équipe médicale")
        
        elif urgency_level == 'modérée':
            recommendations.append("📋 Suivi recommandé")
            recommendations.append("• Programmer une vérification dans les 48h")
            recommendations.append("• Documenter l'évolution")
        
        else:
            recommendations.append("✅ Situation normale")
            recommendations.append("• Continuer la surveillance de routine")
        
        # Recommandations spécifiques au contexte
        stock_level = context.get('stock_level', 0)
        if stock_level < 15:
            recommendations.append(f"• Stock actuel: {stock_level} unités - Prévoir réapprovisionnement")
        
        days_to_expiry = context.get('days_to_expiry', 30)
        if days_to_expiry <= 5:
            recommendations.append(f"• Expiration dans {days_to_expiry} jours - Prioriser l'utilisation")
        
        return recommendations
    
    def batch_analyze(self, df: pd.DataFrame) -> pd.DataFrame:
        """Analyse en lot d'un DataFrame"""
        
        print(f"Analyse de {len(df)} commentaires...")
        
        results = []
        
        for idx, row in df.iterrows():
            if idx % 100 == 0:
                print(f"Progression: {idx}/{len(df)}")
            
            # Préparer le contexte
            context = {
                'stock_level': row.get('stock_final', 0),
                'quality_score': row.get('quality_score', 100),
                'temperature': row.get('temperature', 4),
                'days_to_expiry': row.get('days_to_expiry', 30),
                'hospital': row.get('hospital', ''),
                'blood_type': row.get('blood_type', '')
            }
            
            # Analyser le commentaire
            comment = row.get('quality_comment', '')
            
            # Utiliser le cache si disponible
            cache_key = f"{comment}_{hash(str(context))}"
            if cache_key in self.analysis_cache:
                analysis = self.analysis_cache[cache_key]
            else:
                if self.openai_api_key and not self.use_local_models:
                    analysis = self.analyze_with_openai(comment, context)
                else:
                    analysis = self.analyze_with_local_models(comment, context)
                
                self.analysis_cache[cache_key] = analysis
            
            results.append(analysis)
        
        # Ajouter les résultats au DataFrame
        df_result = df.copy()
        
        df_result['llm_sentiment'] = [r['sentiment'] for r in results]
        df_result['llm_sentiment_score'] = [r['sentiment_score'] for r in results]
        df_result['llm_urgency_level'] = [r['urgency_level'] for r in results]
        df_result['llm_urgency_score'] = [r['urgency_score'] for r in results]
        df_result['llm_key_issues'] = ['; '.join(r['key_issues']) for r in results]
        df_result['llm_keywords'] = ['; '.join(r['keywords']) for r in results]
        df_result['llm_recommendations'] = ['; '.join(r['recommendations']) for r in results]
        df_result['llm_confidence'] = [r['confidence_score'] for r in results]
        
        print("Analyse terminée!")
        return df_result
    
    def get_urgency_statistics(self, df: pd.DataFrame) -> Dict:
        """Calcule des statistiques sur les niveaux d'urgence"""
        
        if 'llm_urgency_level' not in df.columns:
            return {}
        
        urgency_counts = df['llm_urgency_level'].value_counts()
        total = len(df)
        
        stats = {
            'total_analyses': total,
            'urgency_distribution': urgency_counts.to_dict(),
            'urgency_percentages': (urgency_counts / total * 100).to_dict(),
            'critical_cases': len(df[df['llm_urgency_level'] == 'critique']),
            'high_urgency_cases': len(df[df['llm_urgency_level'] == 'élevée']),
            'average_urgency_score': df['llm_urgency_score'].mean() if 'llm_urgency_score' in df.columns else 0
        }
        
        return stats
    
    def generate_alert_report(self, df: pd.DataFrame) -> str:
        """Génère un rapport d'alerte basé sur l'analyse LLM"""
        
        if 'llm_urgency_level' not in df.columns:
            return "Aucune analyse LLM disponible"
        
        # Filtrer les cas critiques et élevés
        critical_cases = df[df['llm_urgency_level'] == 'critique']
        high_cases = df[df['llm_urgency_level'] == 'élevée']
        
        report = f"""
        🩸 RAPPORT D'ALERTE - STOCKS DE SANG
        Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        📊 RÉSUMÉ:
        - Total d'analyses: {len(df)}
        - Cas critiques: {len(critical_cases)} ({len(critical_cases)/len(df)*100:.1f}%)
        - Cas urgents: {len(high_cases)} ({len(high_cases)/len(df)*100:.1f}%)
        
        🚨 CAS CRITIQUES:
        """
        
        for idx, row in critical_cases.head(10).iterrows():
            report += f"""
        
        • {row['hospital']} - {row['blood_type']}
          Stock: {row['stock_final']} unités
          Problèmes: {row['llm_key_issues']}
          Recommandations: {row['llm_recommendations'][:100]}...
        """
        
        if len(high_cases) > 0:
            report += f"""
        
        ⚠️ CAS URGENTS (Top 5):
        """
            
            for idx, row in high_cases.head(5).iterrows():
                report += f"""
        
        • {row['hospital']} - {row['blood_type']}
          Stock: {row['stock_final']} unités
          Score urgence: {row['llm_urgency_score']}/100
        """
        
        return report
    
    def save_analysis_cache(self, filepath: str = 'models/llm/analysis_cache.json'):
        """Sauvegarde le cache d'analyse"""
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.analysis_cache, f, ensure_ascii=False, indent=2)
        
        print(f"Cache d'analyse sauvegardé: {len(self.analysis_cache)} entrées")
    
    def load_analysis_cache(self, filepath: str = 'models/llm/analysis_cache.json'):
        """Charge le cache d'analyse"""
        
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                self.analysis_cache = json.load(f)
            
            print(f"Cache d'analyse chargé: {len(self.analysis_cache)} entrées")

def main():
    """Fonction principale pour tester l'analyseur LLM"""
    
    # Créer l'analyseur
    analyzer = LLMBloodStockAnalyzer(use_local_models=True)
    
    # Charger les données
    print("Chargement des données...")
    df = pd.read_csv('data/synthetic/blood_stock_data.csv')
    
    # Prendre un échantillon pour le test
    sample_df = df.sample(n=min(500, len(df)), random_state=42)
    
    # Analyse en lot
    print("\nAnalyse LLM en cours...")
    analyzed_df = analyzer.batch_analyze(sample_df)
    
    # Statistiques
    print("\nStatistiques d'urgence:")
    stats = analyzer.get_urgency_statistics(analyzed_df)
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Rapport d'alerte
    print("\nRapport d'alerte:")
    alert_report = analyzer.generate_alert_report(analyzed_df)
    print(alert_report)
    
    # Sauvegarder les résultats
    os.makedirs('data/llm_analysis', exist_ok=True)
    analyzed_df.to_csv('data/llm_analysis/analyzed_data.csv', index=False)
    
    with open('data/llm_analysis/alert_report.txt', 'w', encoding='utf-8') as f:
        f.write(alert_report)
    
    # Sauvegarder le cache
    analyzer.save_analysis_cache()
    
    print("\nAnalyse LLM terminée avec succès!")

if __name__ == "__main__":
    main()