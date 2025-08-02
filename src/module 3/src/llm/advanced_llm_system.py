#!/usr/bin/env python3
"""
Système LLM Avancé pour Analyse Médicale
Agent LLM + RAG + Prompts Spécialisés + Alertes Intelligentes
"""

import pandas as pd
import numpy as np
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import re
import hashlib
from pathlib import Path
import sqlite3
from collections import defaultdict, deque
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor
import warnings

# Imports pour RAG et embeddings
try:
    import openai
    from sentence_transformers import SentenceTransformer
    import faiss
    import tiktoken
except ImportError:
    print("⚠️ Modules LLM optionnels non installés. Utilisation des versions simplifiées.")
    openai = None
    SentenceTransformer = None
    faiss = None
    tiktoken = None

warnings.filterwarnings('ignore')

@dataclass
class MedicalKnowledge:
    """Structure pour la base de connaissances médicales"""
    id: str
    title: str
    content: str
    category: str
    blood_types: List[str]
    urgency_level: int  # 1-5
    keywords: List[str]
    source: str
    last_updated: str
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class IncidentClassification:
    """Classification automatique des incidents"""
    incident_id: str
    category: str  # 'stock_critique', 'qualite_degradee', 'temperature_anormale', etc.
    severity: str  # 'low', 'medium', 'high', 'critical'
    urgency_score: float  # 0-1
    recommended_actions: List[str]
    affected_blood_types: List[str]
    estimated_impact: str
    classification_confidence: float
    timestamp: str

@dataclass
class IntelligentAlert:
    """Alerte intelligente générée par LLM"""
    alert_id: str
    title: str
    message: str
    priority: str  # 'low', 'medium', 'high', 'critical'
    category: str
    affected_hospitals: List[str]
    recommended_actions: List[str]
    context: Dict[str, Any]
    generated_at: str
    expires_at: str
    
    def to_dict(self) -> Dict:
        return asdict(self)

class MedicalKnowledgeBase:
    """Base de connaissances médicales pour RAG"""
    
    def __init__(self, db_path: str = "data/medical_knowledge.db"):
        self.db_path = db_path
        self.embedding_model = None
        self.index = None
        self.knowledge_items = []
        self._init_database()
        self._load_default_knowledge()
        
        # Initialiser le modèle d'embeddings si disponible
        if SentenceTransformer:
            try:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                print("✓ Modèle d'embeddings chargé")
            except Exception as e:
                print(f"⚠️ Erreur chargement embeddings: {e}")
    
    def _init_database(self):
        """Initialise la base de données SQLite"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    content TEXT,
                    category TEXT,
                    blood_types TEXT,
                    urgency_level INTEGER,
                    keywords TEXT,
                    source TEXT,
                    last_updated TEXT,
                    embedding BLOB
                )
            """)
    
    def _load_default_knowledge(self):
        """Charge les connaissances médicales par défaut"""
        default_knowledge = [
            {
                "id": "blood_storage_temp",
                "title": "Température de stockage du sang",
                "content": "Le sang total et les globules rouges doivent être stockés entre 1°C et 6°C. Une température supérieure à 6°C peut entraîner une croissance bactérienne. Une température inférieure à 1°C peut causer une hémolyse.",
                "category": "stockage",
                "blood_types": ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"],
                "urgency_level": 4,
                "keywords": ["température", "stockage", "hémolyse", "bactérie"],
                "source": "Guidelines OMS",
                "last_updated": datetime.now().isoformat()
            },
            {
                "id": "o_negative_universal",
                "title": "Sang O- donneur universel",
                "content": "Le sang O- est le donneur universel pour les globules rouges. Il peut être transfusé à tous les patients en urgence. Stock critique si < 10 unités.",
                "category": "compatibilite",
                "blood_types": ["O-"],
                "urgency_level": 5,
                "keywords": ["donneur universel", "urgence", "O négatif", "stock critique"],
                "source": "Protocoles transfusionnels",
                "last_updated": datetime.now().isoformat()
            },
            {
                "id": "quality_degradation",
                "title": "Dégradation qualité sanguine",
                "content": "Score qualité < 80: vérifier température, durée stockage, contamination. Score < 70: analyse microbiologique urgente. Score < 60: destruction recommandée.",
                "category": "qualite",
                "blood_types": ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"],
                "urgency_level": 3,
                "keywords": ["qualité", "contamination", "microbiologie", "destruction"],
                "source": "Standards qualité",
                "last_updated": datetime.now().isoformat()
            },
            {
                "id": "emergency_protocols",
                "title": "Protocoles d'urgence transfusionnelle",
                "content": "En cas de stock critique: 1) Alerter centres régionaux, 2) Activer donneurs d'urgence, 3) Prioriser patients critiques, 4) Considérer alternatives (autotransfusion).",
                "category": "urgence",
                "blood_types": ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"],
                "urgency_level": 5,
                "keywords": ["urgence", "stock critique", "donneurs", "priorisation"],
                "source": "Protocoles hospitaliers",
                "last_updated": datetime.now().isoformat()
            }
        ]
        
        for knowledge in default_knowledge:
            self.add_knowledge(MedicalKnowledge(**knowledge))
    
    def add_knowledge(self, knowledge: MedicalKnowledge):
        """Ajoute une connaissance à la base"""
        with sqlite3.connect(self.db_path) as conn:
            # Calculer l'embedding si possible
            embedding = None
            if self.embedding_model:
                try:
                    embedding_vector = self.embedding_model.encode(knowledge.content)
                    embedding = embedding_vector.tobytes()
                except Exception as e:
                    print(f"Erreur calcul embedding: {e}")
            
            conn.execute("""
                INSERT OR REPLACE INTO knowledge 
                (id, title, content, category, blood_types, urgency_level, keywords, source, last_updated, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                knowledge.id,
                knowledge.title,
                knowledge.content,
                knowledge.category,
                json.dumps(knowledge.blood_types),
                knowledge.urgency_level,
                json.dumps(knowledge.keywords),
                knowledge.source,
                knowledge.last_updated,
                embedding
            ))
        
        self.knowledge_items.append(knowledge)
    
    def search_knowledge(self, query: str, category: str = None, 
                        blood_type: str = None, top_k: int = 5) -> List[MedicalKnowledge]:
        """Recherche dans la base de connaissances"""
        # Recherche par mots-clés simple
        query_lower = query.lower()
        results = []
        
        for knowledge in self.knowledge_items:
            score = 0
            
            # Score basé sur le contenu
            if query_lower in knowledge.content.lower():
                score += 3
            
            # Score basé sur les mots-clés
            for keyword in knowledge.keywords:
                if keyword.lower() in query_lower:
                    score += 2
            
            # Score basé sur le titre
            if query_lower in knowledge.title.lower():
                score += 1
            
            # Filtres
            if category and knowledge.category != category:
                continue
            
            if blood_type and blood_type not in knowledge.blood_types:
                continue
            
            if score > 0:
                results.append((score, knowledge))
        
        # Trier par score et retourner top_k
        results.sort(key=lambda x: x[0], reverse=True)
        return [knowledge for _, knowledge in results[:top_k]]

class SpecializedPromptManager:
    """Gestionnaire de prompts spécialisés pour la gestion des stocks"""
    
    def __init__(self):
        self.prompts = {
            'stock_analysis': """
Vous êtes un expert en gestion des stocks sanguins hospitaliers. 
Analysez les données suivantes et fournissez une évaluation détaillée:

Données: {data}
Contexte médical: {medical_context}

Veuillez analyser:
1. État actuel des stocks par type sanguin
2. Risques identifiés (température, qualité, quantités)
3. Prédictions à court terme (24-48h)
4. Recommandations d'actions prioritaires
5. Niveau d'urgence global (1-5)

Répondez en format JSON structuré.
""",
            
            'incident_classification': """
Classifiez cet incident médical lié aux stocks sanguins:

Incident: {incident_description}
Données contextuelles: {context_data}
Historique: {historical_data}

Classification requise:
1. Catégorie (stock_critique, qualite_degradee, temperature_anormale, contamination, autre)
2. Sévérité (low, medium, high, critical)
3. Urgence (score 0-1)
4. Actions recommandées (liste prioritaire)
5. Impact estimé sur les patients
6. Types sanguins affectés

Format de réponse: JSON structuré.
""",
            
            'alert_generation': """
Générez une alerte intelligente basée sur cette situation:

Situation: {situation}
Données temps réel: {realtime_data}
Seuils d'alerte: {thresholds}
Contexte hospitalier: {hospital_context}

Générez:
1. Titre d'alerte concis et informatif
2. Message détaillé pour le personnel médical
3. Niveau de priorité (low, medium, high, critical)
4. Actions recommandées immédiates
5. Délai d'expiration de l'alerte
6. Hôpitaux/services à notifier

Ton: Professionnel, précis, orienté action.
""",
            
            'contextual_recommendations': """
Fournissez des recommandations contextuelles pour cette situation:

Contexte actuel: {current_context}
Données patient: {patient_data}
Disponibilité stocks: {stock_availability}
Contraintes opérationnelles: {operational_constraints}
Historique décisions: {decision_history}

Recommandations à fournir:
1. Actions immédiates (< 1h)
2. Actions à court terme (1-24h)
3. Actions préventives (> 24h)
4. Alternatives en cas d'indisponibilité
5. Optimisations suggérées
6. Points de vigilance

Personnalisez selon le contexte hospitalier spécifique.
""",
            
            'multimodal_analysis': """
Analyse multi-modale des données de stock sanguin:

Données numériques: {numerical_data}
Commentaires textuels: {text_comments}
Alertes système: {system_alerts}
Tendances historiques: {historical_trends}
Facteurs externes: {external_factors}

Synthèse requise:
1. Corrélations entre données numériques et commentaires
2. Anomalies détectées dans les patterns
3. Sentiment général des commentaires (positif/négatif/neutre)
4. Facteurs de risque identifiés
5. Prédictions basées sur l'analyse croisée
6. Recommandations d'amélioration

Intégrez toutes les modalités pour une analyse holistique.
"""
        }
    
    def get_prompt(self, prompt_type: str, **kwargs) -> str:
        """Récupère et formate un prompt spécialisé"""
        if prompt_type not in self.prompts:
            raise ValueError(f"Type de prompt inconnu: {prompt_type}")
        
        return self.prompts[prompt_type].format(**kwargs)
    
    def add_custom_prompt(self, name: str, template: str):
        """Ajoute un prompt personnalisé"""
        self.prompts[name] = template

class LLMCostOptimizer:
    """Optimiseur de coûts pour les API LLM"""
    
    def __init__(self, cache_size: int = 1000, cache_ttl: int = 3600):
        self.cache = {}
        self.cache_timestamps = {}
        self.cache_size = cache_size
        self.cache_ttl = cache_ttl
        self.usage_stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'tokens_saved': 0,
            'estimated_cost_saved': 0.0
        }
    
    def _get_cache_key(self, prompt: str, model: str = "gpt-3.5-turbo") -> str:
        """Génère une clé de cache pour le prompt"""
        content = f"{model}:{prompt}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Vérifie si l'entrée du cache est encore valide"""
        if cache_key not in self.cache_timestamps:
            return False
        
        return time.time() - self.cache_timestamps[cache_key] < self.cache_ttl
    
    def _cleanup_cache(self):
        """Nettoie le cache des entrées expirées"""
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self.cache_timestamps.items()
            if current_time - timestamp > self.cache_ttl
        ]
        
        for key in expired_keys:
            self.cache.pop(key, None)
            self.cache_timestamps.pop(key, None)
    
    def get_cached_response(self, prompt: str, model: str = "gpt-3.5-turbo") -> Optional[str]:
        """Récupère une réponse du cache si disponible"""
        cache_key = self._get_cache_key(prompt, model)
        
        if cache_key in self.cache and self._is_cache_valid(cache_key):
            self.usage_stats['cache_hits'] += 1
            return self.cache[cache_key]
        
        self.usage_stats['cache_misses'] += 1
        return None
    
    def cache_response(self, prompt: str, response: str, model: str = "gpt-3.5-turbo"):
        """Met en cache une réponse"""
        cache_key = self._get_cache_key(prompt, model)
        
        # Nettoyer le cache si nécessaire
        if len(self.cache) >= self.cache_size:
            self._cleanup_cache()
            
            # Si encore trop plein, supprimer les plus anciennes
            if len(self.cache) >= self.cache_size:
                oldest_key = min(self.cache_timestamps.keys(), 
                               key=lambda k: self.cache_timestamps[k])
                self.cache.pop(oldest_key, None)
                self.cache_timestamps.pop(oldest_key, None)
        
        self.cache[cache_key] = response
        self.cache_timestamps[cache_key] = time.time()
        
        # Estimer les tokens économisés
        if tiktoken:
            try:
                encoding = tiktoken.encoding_for_model(model)
                tokens_saved = len(encoding.encode(prompt + response))
                self.usage_stats['tokens_saved'] += tokens_saved
                
                # Estimation coût (prix approximatif GPT-3.5)
                cost_per_token = 0.000002  # $0.002 per 1K tokens
                self.usage_stats['estimated_cost_saved'] += tokens_saved * cost_per_token
            except Exception:
                pass
    
    def get_usage_stats(self) -> Dict:
        """Retourne les statistiques d'utilisation"""
        total_requests = self.usage_stats['cache_hits'] + self.usage_stats['cache_misses']
        cache_hit_rate = (self.usage_stats['cache_hits'] / total_requests) if total_requests > 0 else 0
        
        return {
            **self.usage_stats,
            'cache_hit_rate': cache_hit_rate,
            'cache_size_current': len(self.cache)
        }

class AdvancedLLMAgent:
    """Agent LLM avancé pour analyse complexe"""
    
    def __init__(self, api_key: str = None, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model
        self.knowledge_base = MedicalKnowledgeBase()
        self.prompt_manager = SpecializedPromptManager()
        self.cost_optimizer = LLMCostOptimizer()
        self.conversation_history = deque(maxlen=50)
        
        # Configuration OpenAI si disponible
        if openai and self.api_key:
            openai.api_key = self.api_key
            self.llm_available = True
            print("✓ Agent LLM configuré avec OpenAI")
        else:
            self.llm_available = False
            print("⚠️ Agent LLM en mode simulation (pas d'API key)")
    
    def _call_llm(self, prompt: str, temperature: float = 0.3) -> str:
        """Appel à l'API LLM avec gestion du cache"""
        # Vérifier le cache d'abord
        cached_response = self.cost_optimizer.get_cached_response(prompt, self.model)
        if cached_response:
            return cached_response
        
        if not self.llm_available or not openai:
            # Mode simulation
            return self._simulate_llm_response(prompt)
        
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Vous êtes un expert en gestion des stocks sanguins hospitaliers."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=1500
            )
            
            result = response.choices[0].message.content
            
            # Mettre en cache
            self.cost_optimizer.cache_response(prompt, result, self.model)
            
            return result
            
        except Exception as e:
            print(f"Erreur API LLM: {e}")
            return self._simulate_llm_response(prompt)
    
    def _simulate_llm_response(self, prompt: str) -> str:
        """Simule une réponse LLM pour les tests"""
        if "stock_analysis" in prompt.lower():
            return json.dumps({
                "etat_stocks": "Stocks globalement stables avec attention sur O- (niveau bas)",
                "risques_identifies": ["Stock O- critique", "Température légèrement élevée unité 3"],
                "predictions_48h": "Diminution attendue de 15% sur O+ et A+",
                "actions_prioritaires": ["Réapprovisionner O-", "Vérifier température unité 3"],
                "niveau_urgence": 3
            }, indent=2)
        
        elif "incident_classification" in prompt.lower():
            return json.dumps({
                "categorie": "stock_critique",
                "severite": "medium",
                "urgence": 0.7,
                "actions_recommandees": ["Alerter centres régionaux", "Activer donneurs urgence"],
                "impact_estime": "Retard possible interventions non-urgentes",
                "types_sanguins_affectes": ["O-", "A-"]
            }, indent=2)
        
        elif "alert_generation" in prompt.lower():
            return json.dumps({
                "titre": "⚠️ Stock Critique - Type O- Négatif",
                "message": "Stock O- en dessous du seuil critique (8 unités). Action immédiate requise.",
                "priorite": "high",
                "actions_immediates": ["Contacter banque de sang régionale", "Préparer protocole urgence"],
                "expiration": "2024-01-15T18:00:00",
                "hopitaux_notifier": ["Hôpital Central", "Urgences Pédiatriques"]
            }, indent=2)
        
        else:
            return json.dumps({
                "analyse": "Analyse simulée en cours...",
                "recommandations": ["Surveillance continue", "Optimisation des stocks"],
                "confiance": 0.8
            }, indent=2)
    
    def analyze_stock_situation(self, stock_data: Dict, medical_context: str = "") -> Dict:
        """Analyse complexe de la situation des stocks"""
        # Rechercher des connaissances pertinentes
        relevant_knowledge = self.knowledge_base.search_knowledge(
            f"stock {medical_context}", top_k=3
        )
        
        knowledge_context = "\n".join([
            f"- {k.title}: {k.content}" for k in relevant_knowledge
        ])
        
        prompt = self.prompt_manager.get_prompt(
            'stock_analysis',
            data=json.dumps(stock_data, indent=2),
            medical_context=knowledge_context
        )
        
        response = self._call_llm(prompt)
        
        try:
            analysis = json.loads(response)
            analysis['knowledge_used'] = [k.title for k in relevant_knowledge]
            analysis['analysis_timestamp'] = datetime.now().isoformat()
            return analysis
        except json.JSONDecodeError:
            return {
                "error": "Erreur parsing réponse LLM",
                "raw_response": response,
                "analysis_timestamp": datetime.now().isoformat()
            }
    
    def classify_incident(self, incident_description: str, context_data: Dict, 
                         historical_data: List[Dict] = None) -> IncidentClassification:
        """Classification automatique des incidents"""
        prompt = self.prompt_manager.get_prompt(
            'incident_classification',
            incident_description=incident_description,
            context_data=json.dumps(context_data, indent=2),
            historical_data=json.dumps(historical_data or [], indent=2)
        )
        
        response = self._call_llm(prompt)
        
        try:
            classification_data = json.loads(response)
            
            return IncidentClassification(
                incident_id=hashlib.md5(incident_description.encode()).hexdigest()[:8],
                category=classification_data.get('categorie', 'autre'),
                severity=classification_data.get('severite', 'medium'),
                urgency_score=classification_data.get('urgence', 0.5),
                recommended_actions=classification_data.get('actions_recommandees', []),
                affected_blood_types=classification_data.get('types_sanguins_affectes', []),
                estimated_impact=classification_data.get('impact_estime', 'Impact non déterminé'),
                classification_confidence=0.85,  # Score simulé
                timestamp=datetime.now().isoformat()
            )
        except json.JSONDecodeError:
            # Classification par défaut en cas d'erreur
            return IncidentClassification(
                incident_id=hashlib.md5(incident_description.encode()).hexdigest()[:8],
                category='autre',
                severity='medium',
                urgency_score=0.5,
                recommended_actions=["Évaluation manuelle requise"],
                affected_blood_types=[],
                estimated_impact="Impact à évaluer",
                classification_confidence=0.3,
                timestamp=datetime.now().isoformat()
            )
    
    def generate_intelligent_alert(self, situation: str, realtime_data: Dict, 
                                 thresholds: Dict, hospital_context: Dict) -> IntelligentAlert:
        """Génère une alerte intelligente"""
        prompt = self.prompt_manager.get_prompt(
            'alert_generation',
            situation=situation,
            realtime_data=json.dumps(realtime_data, indent=2),
            thresholds=json.dumps(thresholds, indent=2),
            hospital_context=json.dumps(hospital_context, indent=2)
        )
        
        response = self._call_llm(prompt)
        
        try:
            alert_data = json.loads(response)
            
            alert_id = hashlib.md5(f"{situation}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
            
            return IntelligentAlert(
                alert_id=alert_id,
                title=alert_data.get('titre', 'Alerte Système'),
                message=alert_data.get('message', situation),
                priority=alert_data.get('priorite', 'medium'),
                category='stock_management',
                affected_hospitals=alert_data.get('hopitaux_notifier', []),
                recommended_actions=alert_data.get('actions_immediates', []),
                context={
                    'situation': situation,
                    'realtime_data': realtime_data,
                    'thresholds': thresholds
                },
                generated_at=datetime.now().isoformat(),
                expires_at=alert_data.get('expiration', 
                    (datetime.now() + timedelta(hours=24)).isoformat())
            )
        except json.JSONDecodeError:
            # Alerte par défaut
            alert_id = hashlib.md5(f"{situation}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
            
            return IntelligentAlert(
                alert_id=alert_id,
                title="Alerte Système - Attention Requise",
                message=situation,
                priority='medium',
                category='stock_management',
                affected_hospitals=[],
                recommended_actions=["Vérification manuelle recommandée"],
                context={'situation': situation},
                generated_at=datetime.now().isoformat(),
                expires_at=(datetime.now() + timedelta(hours=24)).isoformat()
            )
    
    def provide_contextual_recommendations(self, current_context: Dict, 
                                         patient_data: Dict = None,
                                         stock_availability: Dict = None) -> Dict:
        """Fournit des recommandations contextuelles"""
        prompt = self.prompt_manager.get_prompt(
            'contextual_recommendations',
            current_context=json.dumps(current_context, indent=2),
            patient_data=json.dumps(patient_data or {}, indent=2),
            stock_availability=json.dumps(stock_availability or {}, indent=2),
            operational_constraints=json.dumps({}, indent=2),
            decision_history=json.dumps([], indent=2)
        )
        
        response = self._call_llm(prompt)
        
        try:
            recommendations = json.loads(response)
            recommendations['generated_at'] = datetime.now().isoformat()
            recommendations['context_hash'] = hashlib.md5(
                json.dumps(current_context, sort_keys=True).encode()
            ).hexdigest()[:8]
            return recommendations
        except json.JSONDecodeError:
            return {
                "actions_immediates": ["Évaluation de la situation en cours"],
                "actions_court_terme": ["Surveillance continue des stocks"],
                "actions_preventives": ["Optimisation des procédures"],
                "alternatives": ["Protocoles de secours disponibles"],
                "generated_at": datetime.now().isoformat(),
                "error": "Erreur parsing recommandations"
            }
    
    def multimodal_analysis(self, numerical_data: Dict, text_comments: List[str], 
                          system_alerts: List[str], historical_trends: Dict) -> Dict:
        """Analyse multi-modale (texte + données numériques)"""
        prompt = self.prompt_manager.get_prompt(
            'multimodal_analysis',
            numerical_data=json.dumps(numerical_data, indent=2),
            text_comments=json.dumps(text_comments, indent=2),
            system_alerts=json.dumps(system_alerts, indent=2),
            historical_trends=json.dumps(historical_trends, indent=2),
            external_factors=json.dumps({}, indent=2)
        )
        
        response = self._call_llm(prompt, temperature=0.4)
        
        try:
            analysis = json.loads(response)
            
            # Ajouter des métriques calculées
            analysis['sentiment_score'] = self._calculate_sentiment_score(text_comments)
            analysis['anomaly_score'] = self._calculate_anomaly_score(numerical_data)
            analysis['analysis_timestamp'] = datetime.now().isoformat()
            
            return analysis
        except json.JSONDecodeError:
            return {
                "correlations": "Analyse en cours...",
                "anomalies": [],
                "sentiment": "neutre",
                "facteurs_risque": [],
                "predictions": "Données insuffisantes",
                "recommandations": ["Collecte de données supplémentaires"],
                "sentiment_score": self._calculate_sentiment_score(text_comments),
                "anomaly_score": self._calculate_anomaly_score(numerical_data),
                "analysis_timestamp": datetime.now().isoformat(),
                "error": "Erreur parsing analyse multi-modale"
            }
    
    def _calculate_sentiment_score(self, comments: List[str]) -> float:
        """Calcule un score de sentiment simple"""
        if not comments:
            return 0.0
        
        positive_words = ['bon', 'excellent', 'satisfaisant', 'optimal', 'stable']
        negative_words = ['problème', 'critique', 'urgent', 'dégradé', 'insuffisant']
        
        total_score = 0
        for comment in comments:
            comment_lower = comment.lower()
            score = 0
            
            for word in positive_words:
                score += comment_lower.count(word) * 1
            
            for word in negative_words:
                score -= comment_lower.count(word) * 1
            
            total_score += score
        
        # Normaliser entre -1 et 1
        return max(-1, min(1, total_score / len(comments)))
    
    def _calculate_anomaly_score(self, numerical_data: Dict) -> float:
        """Calcule un score d'anomalie simple"""
        if not numerical_data:
            return 0.0
        
        anomaly_indicators = 0
        total_checks = 0
        
        # Vérifications simples
        for key, value in numerical_data.items():
            if isinstance(value, (int, float)):
                total_checks += 1
                
                # Exemples de seuils d'anomalie
                if 'temperature' in key.lower() and (value < 1 or value > 8):
                    anomaly_indicators += 1
                elif 'stock' in key.lower() and value < 0:
                    anomaly_indicators += 1
                elif 'quality' in key.lower() and value < 70:
                    anomaly_indicators += 1
        
        return anomaly_indicators / total_checks if total_checks > 0 else 0.0
    
    def get_system_stats(self) -> Dict:
        """Retourne les statistiques du système LLM"""
        return {
            'llm_available': self.llm_available,
            'model': self.model,
            'knowledge_base_size': len(self.knowledge_base.knowledge_items),
            'conversation_history_size': len(self.conversation_history),
            'cost_optimizer_stats': self.cost_optimizer.get_usage_stats(),
            'prompts_available': list(self.prompt_manager.prompts.keys())
        }

def main():
    """Fonction principale pour tester le système LLM avancé"""
    print("🤖 Test du Système LLM Avancé")
    
    # Créer l'agent LLM
    agent = AdvancedLLMAgent()
    
    # Test 1: Analyse de situation de stock
    print("\n1. Test analyse de stock...")
    stock_data = {
        'O+': {'stock': 45, 'demand': 12, 'quality': 85},
        'O-': {'stock': 8, 'demand': 15, 'quality': 90},
        'A+': {'stock': 32, 'demand': 8, 'quality': 82},
        'temperature_moyenne': 4.2
    }
    
    analysis = agent.analyze_stock_situation(stock_data, "urgence chirurgicale")
    print(f"Analyse: {json.dumps(analysis, indent=2, ensure_ascii=False)}")
    
    # Test 2: Classification d'incident
    print("\n2. Test classification d'incident...")
    incident = "Stock O- en dessous de 10 unités, température frigo 3 en panne"
    context = {'hospital': 'CHU Central', 'time': '14:30', 'day': 'lundi'}
    
    classification = agent.classify_incident(incident, context)
    print(f"Classification: {classification.category} - {classification.severity}")
    print(f"Actions: {classification.recommended_actions}")
    
    # Test 3: Génération d'alerte intelligente
    print("\n3. Test génération d'alerte...")
    situation = "Stock critique O- détecté avec demande urgente en cours"
    realtime_data = {'current_stock': 7, 'pending_requests': 3}
    thresholds = {'critical_level': 10, 'emergency_level': 5}
    hospital_context = {'name': 'CHU Central', 'capacity': 500}
    
    alert = agent.generate_intelligent_alert(situation, realtime_data, thresholds, hospital_context)
    print(f"Alerte: {alert.title}")
    print(f"Priorité: {alert.priority}")
    print(f"Actions: {alert.recommended_actions}")
    
    # Test 4: Recommandations contextuelles
    print("\n4. Test recommandations contextuelles...")
    current_context = {
        'time_of_day': 'evening',
        'day_of_week': 'friday',
        'emergency_level': 'medium',
        'staff_availability': 'reduced'
    }
    
    recommendations = agent.provide_contextual_recommendations(current_context)
    print(f"Recommandations: {json.dumps(recommendations, indent=2, ensure_ascii=False)}")
    
    # Test 5: Analyse multi-modale
    print("\n5. Test analyse multi-modale...")
    numerical_data = {
        'stock_levels': [45, 8, 32, 28],
        'temperatures': [4.2, 3.8, 4.5, 4.1],
        'quality_scores': [85, 90, 82, 88]
    }
    
    text_comments = [
        "Stock O- très bas, attention particulière requise",
        "Qualité globalement satisfaisante",
        "Température frigo 2 légèrement élevée"
    ]
    
    system_alerts = ["STOCK_LOW_O_NEGATIVE", "TEMP_WARNING_UNIT_2"]
    historical_trends = {'trend': 'decreasing', 'rate': -0.05}
    
    multimodal_analysis = agent.multimodal_analysis(
        numerical_data, text_comments, system_alerts, historical_trends
    )
    print(f"Analyse multi-modale: {json.dumps(multimodal_analysis, indent=2, ensure_ascii=False)}")
    
    # Statistiques du système
    print("\n6. Statistiques du système...")
    stats = agent.get_system_stats()
    print(f"Stats: {json.dumps(stats, indent=2, ensure_ascii=False)}")
    
    print("\n✅ Test du système LLM avancé terminé avec succès!")

if __name__ == "__main__":
    main()