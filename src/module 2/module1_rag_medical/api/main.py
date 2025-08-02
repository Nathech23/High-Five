#!/usr/bin/env python3
"""
API FastAPI pour le Système RAG Médical

API REST complète pour le système de Récupération et Génération Augmentée
développé pour l'Hôpital Général de Douala.

Objectifs Hackathon:
25. ✅ Créer API FastAPI pour service RAG
26. ✅ Implémenter endpoints de recherche de connaissances
27. ✅ Valider pipeline complet : query → embeddings → search → context
28. ✅ Documenter architecture RAG

Auteur: Équipe Hackathon Hôpital Général de Douala
Module: 1 - RAG & Medical Knowledge
Version: 1.0.0
"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import traceback
import uvicorn

from fastapi import FastAPI, HTTPException, Depends, Query, Body, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from pydantic import BaseModel, Field, validator
import sys
import os

# Ajouter le chemin parent pour les imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from rag import (
        create_default_rag_system,
        RAGConfiguration,
        MedicalRAGOrchestrator,
        get_module_info
    )
    from data_collection import create_orchestrator
except ImportError as e:
    print(f"Erreur d'import: {e}")
    print("Assurez-vous que tous les modules sont installés")
    sys.exit(1)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# MODÈLES PYDANTIC
# ============================================================================

class HealthResponse(BaseModel):
    """Réponse de santé de l'API"""
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = "1.0.0"
    components: Dict[str, bool] = {}
    uptime_seconds: float = 0.0

class QueryRequest(BaseModel):
    """Requête de recherche RAG"""
    query: str = Field(..., min_length=3, max_length=1000, description="Question médicale")
    language: str = Field(default="fr", description="Langue de la requête (fr, en)")
    max_results: int = Field(default=5, ge=1, le=20, description="Nombre maximum de résultats")
    search_strategy: str = Field(default="hybrid", description="Stratégie de recherche")
    fusion_strategy: str = Field(default="medical_priority", description="Stratégie de fusion")
    include_metadata: bool = Field(default=True, description="Inclure les métadonnées")
    confidence_threshold: float = Field(default=0.3, ge=0.0, le=1.0, description="Seuil de confiance")
    
    @validator('search_strategy')
    def validate_search_strategy(cls, v):
        allowed = ["semantic", "keyword", "hybrid", "medical_entity"]
        if v not in allowed:
            raise ValueError(f"Stratégie de recherche doit être parmi: {allowed}")
        return v
    
    @validator('fusion_strategy')
    def validate_fusion_strategy(cls, v):
        allowed = ["concatenation", "weighted_merge", "hierarchical", "semantic_clustering", "medical_priority"]
        if v not in allowed:
            raise ValueError(f"Stratégie de fusion doit être parmi: {allowed}")
        return v

class SearchResult(BaseModel):
    """Résultat de recherche"""
    document_id: str
    content: str
    score: float
    metadata: Dict[str, Any] = {}
    chunk_info: Dict[str, Any] = {}

class ContextChunk(BaseModel):
    """Chunk de contexte récupéré"""
    chunk_id: str
    content: str
    relevance_score: float
    context_type: str
    medical_entities: List[str] = []
    metadata: Dict[str, Any] = {}

class QueryResponse(BaseModel):
    """Réponse complète à une requête RAG"""
    query: str
    answer: Optional[str] = None
    confidence_score: float
    processing_time: float
    search_results: List[SearchResult]
    retrieved_chunks: List[ContextChunk]
    fused_context: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}
    pipeline_info: Dict[str, Any] = {}

class IndexRequest(BaseModel):
    """Requête d'indexation de documents"""
    documents: List[Dict[str, Any]] = Field(..., description="Documents à indexer")
    batch_size: int = Field(default=10, ge=1, le=100, description="Taille des lots")
    update_existing: bool = Field(default=False, description="Mettre à jour les documents existants")

class IndexResponse(BaseModel):
    """Réponse d'indexation"""
    success: bool
    indexed_count: int
    failed_count: int
    processing_time: float
    errors: List[str] = []
    metadata: Dict[str, Any] = {}

class SystemStatus(BaseModel):
    """Statut du système RAG"""
    status: str
    components_status: Dict[str, bool]
    indexed_documents_count: int
    total_queries: int
    avg_processing_time: float
    cache_hit_rate: float
    memory_usage: Dict[str, Any] = {}
    performance_metrics: Dict[str, Any] = {}

class EvaluationRequest(BaseModel):
    """Requête d'évaluation du système"""
    test_queries: List[str] = Field(default=[], description="Requêtes de test personnalisées")
    max_queries: int = Field(default=10, ge=1, le=50, description="Nombre maximum de requêtes à tester")
    include_metrics: bool = Field(default=True, description="Inclure les métriques détaillées")
    save_results: bool = Field(default=False, description="Sauvegarder les résultats")

class EvaluationResponse(BaseModel):
    """Réponse d'évaluation"""
    success: bool
    total_queries: int
    avg_precision: float
    avg_recall: float
    avg_f1_score: float
    avg_processing_time: float
    detailed_metrics: Dict[str, Any] = {}
    failed_queries: List[str] = []

# ============================================================================
# GESTIONNAIRE D'ÉTAT GLOBAL
# ============================================================================

class RAGAPIManager:
    """Gestionnaire global de l'API RAG"""
    
    def __init__(self):
        self.rag_system: Optional[MedicalRAGOrchestrator] = None
        self.data_orchestrator = None
        self.start_time = time.time()
        self.query_count = 0
        self.total_processing_time = 0.0
        self.is_initialized = False
        
    async def initialize(self):
        """Initialise le système RAG"""
        try:
            logger.info("Initialisation du système RAG...")
            
            # Créer le système RAG
            self.rag_system = create_default_rag_system(
                language="fr",
                medical_domain="general"
            )
            
            # Initialiser le système
            await self.rag_system.initialize()
            
            # Créer l'orchestrateur de données
            self.data_orchestrator = create_orchestrator()
            
            self.is_initialized = True
            logger.info("Système RAG initialisé avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation: {e}")
            raise
    
    async def cleanup(self):
        """Nettoie les ressources"""
        if self.rag_system:
            await self.rag_system.cleanup()
        logger.info("Nettoyage terminé")
    
    def get_uptime(self) -> float:
        """Retourne le temps de fonctionnement en secondes"""
        return time.time() - self.start_time
    
    def update_metrics(self, processing_time: float):
        """Met à jour les métriques de performance"""
        self.query_count += 1
        self.total_processing_time += processing_time
    
    def get_avg_processing_time(self) -> float:
        """Retourne le temps de traitement moyen"""
        if self.query_count == 0:
            return 0.0
        return self.total_processing_time / self.query_count

# Instance globale du gestionnaire
api_manager = RAGAPIManager()

# ============================================================================
# APPLICATION FASTAPI
# ============================================================================

app = FastAPI(
    title="API RAG Médical - Hôpital Général de Douala",
    description="""
    API REST pour le système de Récupération et Génération Augmentée (RAG) 
    développé pour l'Hôpital Général de Douala.
    
    ## Fonctionnalités
    
    - 🔍 **Recherche sémantique** dans les connaissances médicales
    - 🧠 **Récupération de contexte** intelligent
    - 📊 **Indexation** de documents médicaux
    - 🎯 **Évaluation** de performance du système
    - 📈 **Monitoring** en temps réel
    
    ## Pipeline RAG
    
    1. **Query** → Analyse de la requête utilisateur
    2. **Embeddings** → Conversion en vecteurs sémantiques
    3. **Search** → Recherche dans la base de connaissances
    4. **Context** → Récupération et fusion du contexte pertinent
    5. **Response** → Génération de la réponse finale
    
    ## Objectifs Hackathon
    
    - ✅ 25. Créer API FastAPI pour service RAG
    - ✅ 26. Implémenter endpoints de recherche de connaissances
    - ✅ 27. Valider pipeline complet : query → embeddings → search → context
    - ✅ 28. Documenter architecture RAG
    """,
    version="1.0.0",
    contact={
        "name": "Équipe Hackathon Hôpital Général de Douala",
        "email": "hackathon@hopitaldouala.cm"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, spécifier les domaines autorisés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# DÉPENDANCES
# ============================================================================

async def get_rag_system() -> MedicalRAGOrchestrator:
    """Dépendance pour obtenir le système RAG"""
    if not api_manager.is_initialized or not api_manager.rag_system:
        raise HTTPException(
            status_code=503,
            detail="Système RAG non initialisé. Veuillez attendre l'initialisation."
        )
    return api_manager.rag_system

# ============================================================================
# ENDPOINTS DE SANTÉ ET STATUT
# ============================================================================

@app.get("/health", response_model=HealthResponse, tags=["Santé"])
async def health_check():
    """
    Vérification de santé de l'API
    
    Retourne le statut de santé de l'API et de ses composants.
    """
    components = {
        "rag_system": api_manager.rag_system is not None,
        "data_orchestrator": api_manager.data_orchestrator is not None,
        "initialized": api_manager.is_initialized
    }
    
    status = "healthy" if all(components.values()) else "degraded"
    
    return HealthResponse(
        status=status,
        components=components,
        uptime_seconds=api_manager.get_uptime()
    )

@app.get("/status", response_model=SystemStatus, tags=["Santé"])
async def system_status(rag_system: MedicalRAGOrchestrator = Depends(get_rag_system)):
    """
    Statut détaillé du système RAG
    
    Retourne des informations détaillées sur l'état du système RAG.
    """
    try:
        status_info = rag_system.get_system_status()
        
        return SystemStatus(
            status="operational" if status_info.get("is_ready", False) else "initializing",
            components_status=status_info.get("components_status", {}),
            indexed_documents_count=status_info.get("indexed_documents_count", 0),
            total_queries=api_manager.query_count,
            avg_processing_time=api_manager.get_avg_processing_time(),
            cache_hit_rate=status_info.get("metrics", {}).get("cache_hit_rate", 0.0),
            memory_usage=status_info.get("memory_usage", {}),
            performance_metrics=status_info.get("metrics", {})
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du statut: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/info", tags=["Information"])
async def system_info():
    """
    Informations sur le système
    
    Retourne des informations générales sur le module RAG.
    """
    try:
        module_info = get_module_info()
        return {
            "module": "RAG & Medical Knowledge",
            "version": module_info.get("version", "1.0.0"),
            "components": module_info.get("components", []),
            "description": module_info.get("description", ""),
            "hackathon_objectives": [
                "25. ✅ Créer API FastAPI pour service RAG",
                "26. ✅ Implémenter endpoints de recherche de connaissances",
                "27. ✅ Valider pipeline complet : query → embeddings → search → context",
                "28. ✅ Documenter architecture RAG"
            ],
            "uptime_seconds": api_manager.get_uptime(),
            "total_queries": api_manager.query_count
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des informations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ENDPOINTS RAG PRINCIPAUX
# ============================================================================

@app.post("/query", response_model=QueryResponse, tags=["RAG"])
async def query_rag(
    request: QueryRequest,
    rag_system: MedicalRAGOrchestrator = Depends(get_rag_system)
):
    """
    Effectuer une requête RAG
    
    Pipeline complet : query → embeddings → search → context → response
    
    ## Paramètres
    - **query**: Question médicale (3-1000 caractères)
    - **language**: Langue de la requête (fr, en)
    - **max_results**: Nombre maximum de résultats (1-20)
    - **search_strategy**: Stratégie de recherche (semantic, hybrid, etc.)
    - **fusion_strategy**: Stratégie de fusion du contexte
    - **confidence_threshold**: Seuil de confiance minimum (0.0-1.0)
    
    ## Réponse
    - Réponse générée avec score de confiance
    - Résultats de recherche détaillés
    - Chunks de contexte récupérés
    - Métadonnées du pipeline
    """
    start_time = time.time()
    
    try:
        logger.info(f"Requête RAG reçue: {request.query[:100]}...")
        
        # Effectuer la requête RAG
        response = await rag_system.query(
            query_text=request.query,
            language=request.language,
            max_results=request.max_results,
            search_strategy=request.search_strategy,
            fusion_strategy=request.fusion_strategy,
            confidence_threshold=request.confidence_threshold
        )
        
        processing_time = time.time() - start_time
        api_manager.update_metrics(processing_time)
        
        # Convertir la réponse au format API
        search_results = [
            SearchResult(
                document_id=result.get("document_id", ""),
                content=result.get("content", ""),
                score=result.get("score", 0.0),
                metadata=result.get("metadata", {}),
                chunk_info=result.get("chunk_info", {})
            )
            for result in response.search_results
        ]
        
        retrieved_chunks = [
            ContextChunk(
                chunk_id=chunk.get("chunk_id", ""),
                content=chunk.get("content", ""),
                relevance_score=chunk.get("relevance_score", 0.0),
                context_type=chunk.get("context_type", "unknown"),
                medical_entities=chunk.get("medical_entities", []),
                metadata=chunk.get("metadata", {})
            )
            for chunk in response.retrieved_chunks
        ]
        
        return QueryResponse(
            query=request.query,
            answer=getattr(response, 'answer', None),
            confidence_score=response.confidence_score,
            processing_time=processing_time,
            search_results=search_results,
            retrieved_chunks=retrieved_chunks,
            fused_context=getattr(response, 'fused_context', {}).__dict__ if hasattr(getattr(response, 'fused_context', {}), '__dict__') else {},
            metadata={
                "search_strategy": request.search_strategy,
                "fusion_strategy": request.fusion_strategy,
                "language": request.language,
                "timestamp": datetime.now().isoformat()
            },
            pipeline_info={
                "embeddings_generated": True,
                "search_completed": True,
                "context_retrieved": len(retrieved_chunks) > 0,
                "response_generated": response.confidence_score >= request.confidence_threshold
            }
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de la requête RAG: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement de la requête: {str(e)}")

@app.post("/search", tags=["RAG"])
async def search_knowledge(
    query: str = Body(..., description="Requête de recherche"),
    max_results: int = Query(default=10, ge=1, le=50, description="Nombre maximum de résultats"),
    search_type: str = Query(default="hybrid", description="Type de recherche"),
    rag_system: MedicalRAGOrchestrator = Depends(get_rag_system)
):
    """
    Recherche dans la base de connaissances
    
    Endpoint simplifié pour la recherche sémantique uniquement.
    """
    try:
        start_time = time.time()
        
        # Effectuer la recherche
        results = await rag_system.search(
            query=query,
            max_results=max_results,
            search_type=search_type
        )
        
        processing_time = time.time() - start_time
        
        return {
            "query": query,
            "results": results,
            "count": len(results),
            "processing_time": processing_time,
            "search_type": search_type
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la recherche: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ENDPOINTS D'INDEXATION
# ============================================================================

@app.post("/index", response_model=IndexResponse, tags=["Indexation"])
async def index_documents(
    request: IndexRequest,
    background_tasks: BackgroundTasks,
    rag_system: MedicalRAGOrchestrator = Depends(get_rag_system)
):
    """
    Indexer des documents dans le système RAG
    
    Ajoute de nouveaux documents à la base de connaissances.
    
    ## Paramètres
    - **documents**: Liste des documents à indexer
    - **batch_size**: Taille des lots pour le traitement
    - **update_existing**: Mettre à jour les documents existants
    """
    start_time = time.time()
    
    try:
        logger.info(f"Indexation de {len(request.documents)} documents")
        
        # Indexer les documents
        result = await rag_system.index_documents(
            documents=request.documents,
            batch_size=request.batch_size,
            update_existing=request.update_existing
        )
        
        processing_time = time.time() - start_time
        
        return IndexResponse(
            success=result.get("success", True),
            indexed_count=result.get("indexed_count", len(request.documents)),
            failed_count=result.get("failed_count", 0),
            processing_time=processing_time,
            errors=result.get("errors", []),
            metadata={
                "batch_size": request.batch_size,
                "update_existing": request.update_existing,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de l'indexation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/index/{document_id}", tags=["Indexation"])
async def delete_document(
    document_id: str,
    rag_system: MedicalRAGOrchestrator = Depends(get_rag_system)
):
    """
    Supprimer un document de l'index
    
    Retire un document spécifique de la base de connaissances.
    """
    try:
        result = await rag_system.delete_document(document_id)
        
        if result.get("success", False):
            return {"message": f"Document {document_id} supprimé avec succès"}
        else:
            raise HTTPException(status_code=404, detail=f"Document {document_id} non trouvé")
            
    except Exception as e:
        logger.error(f"Erreur lors de la suppression: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ENDPOINTS D'ÉVALUATION
# ============================================================================

@app.post("/evaluate", response_model=EvaluationResponse, tags=["Évaluation"])
async def evaluate_system(
    request: EvaluationRequest,
    background_tasks: BackgroundTasks,
    rag_system: MedicalRAGOrchestrator = Depends(get_rag_system)
):
    """
    Évaluer les performances du système RAG
    
    Lance une évaluation complète du système avec des métriques de performance.
    
    ## Métriques calculées
    - Précision@k, Rappel@k, F1@k
    - MAP (Mean Average Precision)
    - NDCG (Normalized Discounted Cumulative Gain)
    - MRR (Mean Reciprocal Rank)
    - Temps de traitement moyen
    """
    try:
        logger.info(f"Évaluation du système avec {request.max_queries} requêtes")
        
        # Lancer l'évaluation
        evaluation_result = await rag_system.evaluate_performance(
            test_queries=request.test_queries,
            max_queries=request.max_queries,
            include_detailed_metrics=request.include_metrics
        )
        
        if request.save_results:
            # Sauvegarder les résultats en arrière-plan
            background_tasks.add_task(
                save_evaluation_results,
                evaluation_result
            )
        
        metrics = evaluation_result.get("metrics", {})
        
        return EvaluationResponse(
            success=evaluation_result.get("success", True),
            total_queries=evaluation_result.get("total_queries", 0),
            avg_precision=metrics.get("avg_precision_at_5", 0.0),
            avg_recall=metrics.get("avg_recall_at_5", 0.0),
            avg_f1_score=metrics.get("avg_f1_at_5", 0.0),
            avg_processing_time=metrics.get("avg_processing_time", 0.0),
            detailed_metrics=metrics if request.include_metrics else {},
            failed_queries=evaluation_result.get("failed_queries", [])
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de l'évaluation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/metrics", tags=["Évaluation"])
async def get_metrics(rag_system: MedicalRAGOrchestrator = Depends(get_rag_system)):
    """
    Obtenir les métriques de performance actuelles
    
    Retourne les métriques de performance en temps réel du système.
    """
    try:
        status = rag_system.get_system_status()
        metrics = status.get("metrics", {})
        
        return {
            "system_metrics": metrics,
            "api_metrics": {
                "total_queries": api_manager.query_count,
                "avg_processing_time": api_manager.get_avg_processing_time(),
                "uptime_seconds": api_manager.get_uptime()
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des métriques: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ENDPOINTS DE VALIDATION DU PIPELINE
# ============================================================================

@app.post("/validate-pipeline", tags=["Validation"])
async def validate_pipeline(
    test_query: str = Body(..., description="Requête de test pour valider le pipeline"),
    rag_system: MedicalRAGOrchestrator = Depends(get_rag_system)
):
    """
    Valider le pipeline complet RAG
    
    Objectif 27: Valider pipeline complet : query → embeddings → search → context
    
    Teste chaque étape du pipeline et retourne des informations détaillées.
    """
    try:
        validation_result = {
            "query": test_query,
            "pipeline_steps": {},
            "success": True,
            "errors": [],
            "timing": {}
        }
        
        # Étape 1: Analyse de la requête
        step_start = time.time()
        try:
            query_analysis = await rag_system.analyze_query(test_query)
            validation_result["pipeline_steps"]["query_analysis"] = {
                "status": "success",
                "result": query_analysis
            }
        except Exception as e:
            validation_result["pipeline_steps"]["query_analysis"] = {
                "status": "error",
                "error": str(e)
            }
            validation_result["errors"].append(f"Query analysis: {e}")
        validation_result["timing"]["query_analysis"] = time.time() - step_start
        
        # Étape 2: Génération d'embeddings
        step_start = time.time()
        try:
            embeddings = await rag_system.generate_embeddings(test_query)
            validation_result["pipeline_steps"]["embeddings"] = {
                "status": "success",
                "embedding_dimension": len(embeddings) if embeddings is not None else 0,
                "embedding_norm": float(sum(x*x for x in embeddings)**0.5) if embeddings else 0.0
            }
        except Exception as e:
            validation_result["pipeline_steps"]["embeddings"] = {
                "status": "error",
                "error": str(e)
            }
            validation_result["errors"].append(f"Embeddings generation: {e}")
        validation_result["timing"]["embeddings"] = time.time() - step_start
        
        # Étape 3: Recherche sémantique
        step_start = time.time()
        try:
            search_results = await rag_system.search(test_query, max_results=5)
            validation_result["pipeline_steps"]["search"] = {
                "status": "success",
                "results_count": len(search_results),
                "top_score": search_results[0].get("score", 0.0) if search_results else 0.0
            }
        except Exception as e:
            validation_result["pipeline_steps"]["search"] = {
                "status": "error",
                "error": str(e)
            }
            validation_result["errors"].append(f"Search: {e}")
        validation_result["timing"]["search"] = time.time() - step_start
        
        # Étape 4: Récupération de contexte
        step_start = time.time()
        try:
            context = await rag_system.retrieve_context(test_query)
            validation_result["pipeline_steps"]["context_retrieval"] = {
                "status": "success",
                "context_chunks": len(context.get("chunks", [])),
                "total_context_length": len(context.get("content", ""))
            }
        except Exception as e:
            validation_result["pipeline_steps"]["context_retrieval"] = {
                "status": "error",
                "error": str(e)
            }
            validation_result["errors"].append(f"Context retrieval: {e}")
        validation_result["timing"]["context_retrieval"] = time.time() - step_start
        
        # Déterminer le succès global
        validation_result["success"] = len(validation_result["errors"]) == 0
        validation_result["total_time"] = sum(validation_result["timing"].values())
        
        return validation_result
        
    except Exception as e:
        logger.error(f"Erreur lors de la validation du pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

async def save_evaluation_results(evaluation_result: Dict[str, Any]):
    """Sauvegarde les résultats d'évaluation"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"evaluation_results_{timestamp}.json"
        
        # Créer le dossier de résultats s'il n'existe pas
        results_dir = Path("evaluation_results")
        results_dir.mkdir(exist_ok=True)
        
        # Sauvegarder les résultats
        import json
        with open(results_dir / filename, 'w', encoding='utf-8') as f:
            json.dump(evaluation_result, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Résultats d'évaluation sauvegardés: {filename}")
        
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde: {e}")

# ============================================================================
# ÉVÉNEMENTS DE CYCLE DE VIE
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage de l'API"""
    logger.info("Démarrage de l'API RAG Médical...")
    try:
        await api_manager.initialize()
        logger.info("API RAG Médical démarrée avec succès")
    except Exception as e:
        logger.error(f"Erreur lors du démarrage: {e}")
        # Ne pas arrêter l'API, permettre les tentatives de réinitialisation

@app.on_event("shutdown")
async def shutdown_event():
    """Nettoyage à l'arrêt de l'API"""
    logger.info("Arrêt de l'API RAG Médical...")
    await api_manager.cleanup()
    logger.info("API RAG Médical arrêtée")

# ============================================================================
# DOCUMENTATION PERSONNALISÉE
# ============================================================================

@app.get("/docs-architecture", response_class=HTMLResponse, tags=["Documentation"])
async def architecture_docs():
    """
    Documentation de l'architecture RAG
    
    Objectif 28: Documenter architecture RAG
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Architecture RAG - Hôpital Général de Douala</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }
            .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; }
            .section { margin: 20px 0; padding: 20px; border-left: 4px solid #3498db; }
            .pipeline { background: #f8f9fa; padding: 15px; border-radius: 5px; }
            .step { margin: 10px 0; padding: 10px; background: white; border-radius: 3px; }
            .code { background: #f4f4f4; padding: 10px; border-radius: 3px; font-family: monospace; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🏥 Architecture RAG - Système Médical</h1>
            <p>Hôpital Général de Douala - Hackathon 2024</p>
        </div>
        
        <div class="section">
            <h2>🎯 Objectifs Hackathon Accomplis</h2>
            <ul>
                <li>✅ 25. Créer API FastAPI pour service RAG</li>
                <li>✅ 26. Implémenter endpoints de recherche de connaissances</li>
                <li>✅ 27. Valider pipeline complet : query → embeddings → search → context</li>
                <li>✅ 28. Documenter architecture RAG</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>🏗️ Architecture Générale</h2>
            <div class="pipeline">
                <h3>Pipeline RAG Complet</h3>
                <div class="step">1. <strong>Query Analysis</strong> - Analyse et préprocessing de la requête</div>
                <div class="step">2. <strong>Embeddings Generation</strong> - Conversion en vecteurs sémantiques</div>
                <div class="step">3. <strong>Semantic Search</strong> - Recherche dans la base vectorielle</div>
                <div class="step">4. <strong>Context Retrieval</strong> - Récupération et fusion du contexte</div>
                <div class="step">5. <strong>Response Generation</strong> - Génération de la réponse finale</div>
            </div>
        </div>
        
        <div class="section">
            <h2>🔧 Composants Techniques</h2>
            <h3>Chunking Intelligent</h3>
            <p>Segmentation hybride combinant analyse structurelle et sémantique avec reconnaissance d'entités médicales.</p>
            
            <h3>Pipeline d'Embeddings</h3>
            <p>Utilisation de sentence-transformers optimisés pour le domaine médical avec cache intelligent.</p>
            
            <h3>Recherche Sémantique</h3>
            <p>Système multi-vectoriel avec stratégies hybrides et scoring de pertinence multi-critères.</p>
            
            <h3>Récupération de Contexte</h3>
            <p>Fusion contextuelle intelligente avec classification automatique et enrichissement médical.</p>
        </div>
        
        <div class="section">
            <h2>📊 Endpoints API</h2>
            <div class="code">
GET  /health              - Santé de l'API
GET  /status              - Statut détaillé du système
POST /query               - Requête RAG complète
POST /search              - Recherche sémantique
POST /index               - Indexation de documents
POST /evaluate            - Évaluation de performance
POST /validate-pipeline   - Validation du pipeline
GET  /docs-architecture   - Documentation architecture
            </div>
        </div>
        
        <div class="section">
            <h2>🎯 Métriques de Performance</h2>
            <ul>
                <li><strong>Précision@k</strong> - Précision des k premiers résultats</li>
                <li><strong>Rappel@k</strong> - Rappel des k premiers résultats</li>
                <li><strong>MAP</strong> - Mean Average Precision</li>
                <li><strong>NDCG</strong> - Normalized Discounted Cumulative Gain</li>
                <li><strong>MRR</strong> - Mean Reciprocal Rank</li>
                <li><strong>Temps de traitement</strong> - Performance en temps réel</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>🔬 Validation du Pipeline</h2>
            <p>Le endpoint <code>/validate-pipeline</code> permet de tester chaque étape :</p>
            <div class="pipeline">
                <div class="step">✅ Analyse de requête - Preprocessing et extraction d'entités</div>
                <div class="step">✅ Génération d'embeddings - Vectorisation sémantique</div>
                <div class="step">✅ Recherche - Matching dans la base vectorielle</div>
                <div class="step">✅ Récupération de contexte - Fusion et enrichissement</div>
            </div>
        </div>
        
        <div class="section">
            <h2>🌍 Adaptation Camerounaise</h2>
            <ul>
                <li>Support multilingue (français, anglais, langues locales)</li>
                <li>Données médicales adaptées au contexte africain</li>
                <li>Priorité aux maladies tropicales et endémiques</li>
                <li>Intégration des pratiques médicales locales</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>📈 Monitoring et Observabilité</h2>
            <p>Surveillance en temps réel avec métriques de performance, logs détaillés et alertes automatiques.</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# ============================================================================
# POINT D'ENTRÉE PRINCIPAL
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Démarrage du serveur API RAG Médical...")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )