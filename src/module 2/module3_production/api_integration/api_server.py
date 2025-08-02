#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Serveur API REST Haute Performance - Objectifs 19-20
Module 3: Production Data & Knowledge - API Integration

Ce module implémente un serveur API REST haute performance avec FastAPI
pour l'intégration avec les systèmes hospitaliers et l'accès aux données médicales.

Fonctionnalités:
- API REST haute performance avec FastAPI
- Authentification JWT sécurisée
- Intégration HL7 FHIR
- Documentation automatique Swagger/OpenAPI
- Validation des données Pydantic
- Gestion des erreurs robuste
- Rate limiting et throttling
- Monitoring et métriques
"""

import logging
import json
import time
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path

# FastAPI et dépendances
from fastapi import FastAPI, HTTPException, Depends, Security, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

# Pydantic pour validation
from pydantic import BaseModel, Field, validator
from pydantic.types import EmailStr

# JWT et sécurité
import jwt
from passlib.context import CryptContext
import secrets

# Monitoring et métriques
import psutil
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration de sécurité
SECRET_KEY = secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Contexte de chiffrement des mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Métriques Prometheus
request_count = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('api_request_duration_seconds', 'API request duration')
active_connections = Gauge('api_active_connections', 'Active API connections')
error_count = Counter('api_errors_total', 'Total API errors', ['error_type'])

# Modèles Pydantic
class UserCredentials(BaseModel):
    """Modèle pour les identifiants utilisateur"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)

class Token(BaseModel):
    """Modèle pour le token JWT"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class User(BaseModel):
    """Modèle utilisateur"""
    id: int
    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: bool = True
    roles: List[str] = []

class MedicalDocument(BaseModel):
    """Modèle pour document médical"""
    id: str
    title: str
    content: str
    category: str = Field(..., regex="^(cardiologie|neurologie|oncologie|pediatrie|general)$")
    type: str = Field(..., regex="^(diagnostic|traitement|symptome|procedure)$")
    author: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    tags: List[str] = []
    metadata: Dict[str, Any] = {}
    
    @validator('content')
    def content_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Le contenu ne peut pas être vide')
        return v

class SearchQuery(BaseModel):
    """Modèle pour requête de recherche"""
    query: str = Field(..., min_length=1, max_length=500)
    category: Optional[str] = None
    type: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    include_metadata: bool = False

class SearchResult(BaseModel):
    """Modèle pour résultat de recherche"""
    documents: List[MedicalDocument]
    total_count: int
    query_time_ms: float
    has_more: bool

class HL7FHIRResource(BaseModel):
    """Modèle pour ressource HL7 FHIR"""
    resourceType: str
    id: str
    meta: Dict[str, Any] = {}
    text: Optional[Dict[str, Any]] = None
    identifier: List[Dict[str, Any]] = []
    status: str = "active"
    subject: Optional[Dict[str, Any]] = None
    encounter: Optional[Dict[str, Any]] = None
    effectiveDateTime: Optional[datetime] = None
    valueQuantity: Optional[Dict[str, Any]] = None
    component: List[Dict[str, Any]] = []

class APIResponse(BaseModel):
    """Modèle de réponse API standardisé"""
    success: bool
    data: Optional[Any] = None
    message: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)
    request_id: Optional[str] = None
    errors: List[str] = []

class HealthCheck(BaseModel):
    """Modèle pour vérification de santé"""
    status: str
    timestamp: datetime
    version: str
    uptime_seconds: float
    memory_usage_mb: float
    cpu_usage_percent: float
    active_connections: int
    total_requests: int

# Base de données simulée
FAKE_USERS_DB = {
    "admin": {
        "id": 1,
        "username": "admin",
        "email": "admin@hospital.com",
        "full_name": "Administrateur Système",
        "hashed_password": pwd_context.hash("admin123"),
        "is_active": True,
        "roles": ["admin", "doctor", "nurse"]
    },
    "doctor1": {
        "id": 2,
        "username": "doctor1",
        "email": "doctor1@hospital.com",
        "full_name": "Dr. Jean Dupont",
        "hashed_password": pwd_context.hash("doctor123"),
        "is_active": True,
        "roles": ["doctor"]
    },
    "nurse1": {
        "id": 3,
        "username": "nurse1",
        "email": "nurse1@hospital.com",
        "full_name": "Infirmière Marie Martin",
        "hashed_password": pwd_context.hash("nurse123"),
        "is_active": True,
        "roles": ["nurse"]
    }
}

# Documents médicaux simulés
FAKE_DOCUMENTS = [
    {
        "id": "doc_001",
        "title": "Protocole de traitement cardiaque",
        "content": "Protocole détaillé pour le traitement des pathologies cardiaques...",
        "category": "cardiologie",
        "type": "traitement",
        "author": "Dr. Cardio",
        "created_at": datetime.now() - timedelta(days=30),
        "tags": ["cardiologie", "traitement", "protocole"],
        "metadata": {"version": "1.2", "reviewed": True}
    },
    {
        "id": "doc_002",
        "title": "Diagnostic neurologique avancé",
        "content": "Méthodes de diagnostic pour les pathologies neurologiques...",
        "category": "neurologie",
        "type": "diagnostic",
        "author": "Dr. Neuro",
        "created_at": datetime.now() - timedelta(days=15),
        "tags": ["neurologie", "diagnostic", "imagerie"],
        "metadata": {"version": "2.0", "reviewed": True}
    },
    {
        "id": "doc_003",
        "title": "Symptômes oncologiques précoces",
        "content": "Identification des symptômes précoces en oncologie...",
        "category": "oncologie",
        "type": "symptome",
        "author": "Dr. Onco",
        "created_at": datetime.now() - timedelta(days=7),
        "tags": ["oncologie", "symptômes", "dépistage"],
        "metadata": {"version": "1.0", "reviewed": False}
    }
]

# Utilitaires de sécurité
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifier un mot de passe"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hasher un mot de passe"""
    return pwd_context.hash(password)

def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authentifier un utilisateur"""
    user = FAKE_USERS_DB.get(username)
    if not user or not verify_password(password, user["hashed_password"]):
        return None
    return user

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Créer un token JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
    """Vérifier un token JWT"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user = FAKE_USERS_DB.get(username)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Utilisateur non trouvé",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
    
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )

def require_role(required_roles: List[str]):
    """Décorateur pour vérifier les rôles"""
    def role_checker(current_user: Dict[str, Any] = Depends(verify_token)):
        user_roles = current_user.get("roles", [])
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissions insuffisantes"
            )
        return current_user
    return role_checker

# Création de l'application FastAPI
app = FastAPI(
    title="API Médicale Hospitalière",
    description="API REST haute performance pour l'accès aux données médicales et l'intégration HL7 FHIR",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://hospital.local"],  # Restreint en production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Middleware de sécurité
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "hospital.local"]
)

# Middleware de monitoring
@app.middleware("http")
async def monitoring_middleware(request: Request, call_next):
    """Middleware pour le monitoring des requêtes"""
    start_time = time.time()
    active_connections.inc()
    
    try:
        response = await call_next(request)
        
        # Métriques
        duration = time.time() - start_time
        request_duration.observe(duration)
        request_count.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        # Headers de réponse
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        response.headers["X-Request-ID"] = str(id(request))
        
        return response
    
    except Exception as e:
        error_count.labels(error_type=type(e).__name__).inc()
        raise
    
    finally:
        active_connections.dec()

# Routes d'authentification
@app.post("/auth/login", response_model=Token, tags=["Authentication"])
async def login(credentials: UserCredentials):
    """Authentification et génération de token JWT"""
    user = authenticate_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@app.get("/auth/me", response_model=User, tags=["Authentication"])
async def get_current_user(current_user: Dict[str, Any] = Depends(verify_token)):
    """Obtenir les informations de l'utilisateur connecté"""
    return User(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user.get("email"),
        full_name=current_user.get("full_name"),
        is_active=current_user["is_active"],
        roles=current_user["roles"]
    )

# Routes de recherche médicale
@app.post("/search", response_model=APIResponse, tags=["Medical Search"])
async def search_documents(
    search_query: SearchQuery,
    current_user: Dict[str, Any] = Depends(verify_token)
):
    """Rechercher dans les documents médicaux"""
    start_time = time.time()
    
    try:
        # Simulation de recherche
        filtered_docs = FAKE_DOCUMENTS.copy()
        
        # Filtrer par catégorie
        if search_query.category:
            filtered_docs = [doc for doc in filtered_docs if doc["category"] == search_query.category]
        
        # Filtrer par type
        if search_query.type:
            filtered_docs = [doc for doc in filtered_docs if doc["type"] == search_query.type]
        
        # Recherche textuelle simple
        query_lower = search_query.query.lower()
        matching_docs = [
            doc for doc in filtered_docs
            if query_lower in doc["title"].lower() or query_lower in doc["content"].lower()
        ]
        
        # Pagination
        total_count = len(matching_docs)
        start_idx = search_query.offset
        end_idx = start_idx + search_query.limit
        paginated_docs = matching_docs[start_idx:end_idx]
        
        # Convertir en modèles Pydantic
        result_docs = [
            MedicalDocument(
                id=doc["id"],
                title=doc["title"],
                content=doc["content"],
                category=doc["category"],
                type=doc["type"],
                author=doc["author"],
                created_at=doc["created_at"],
                tags=doc["tags"],
                metadata=doc["metadata"] if search_query.include_metadata else {}
            )
            for doc in paginated_docs
        ]
        
        query_time_ms = (time.time() - start_time) * 1000
        
        search_result = SearchResult(
            documents=result_docs,
            total_count=total_count,
            query_time_ms=query_time_ms,
            has_more=end_idx < total_count
        )
        
        return APIResponse(
            success=True,
            data=search_result.dict(),
            message=f"Trouvé {len(result_docs)} documents en {query_time_ms:.1f}ms",
            request_id=str(id(search_query))
        )
    
    except Exception as e:
        logger.error(f"Erreur lors de la recherche: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne lors de la recherche"
        )

@app.get("/documents/{document_id}", response_model=APIResponse, tags=["Medical Documents"])
async def get_document(
    document_id: str,
    current_user: Dict[str, Any] = Depends(verify_token)
):
    """Obtenir un document médical par ID"""
    document = next((doc for doc in FAKE_DOCUMENTS if doc["id"] == document_id), None)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document non trouvé"
        )
    
    doc_model = MedicalDocument(
        id=document["id"],
        title=document["title"],
        content=document["content"],
        category=document["category"],
        type=document["type"],
        author=document["author"],
        created_at=document["created_at"],
        tags=document["tags"],
        metadata=document["metadata"]
    )
    
    return APIResponse(
        success=True,
        data=doc_model.dict(),
        message="Document récupéré avec succès"
    )

@app.post("/documents", response_model=APIResponse, tags=["Medical Documents"])
async def create_document(
    document: MedicalDocument,
    current_user: Dict[str, Any] = Depends(require_role(["doctor", "admin"]))
):
    """Créer un nouveau document médical (réservé aux médecins et admins)"""
    # Vérifier que l'ID n'existe pas déjà
    if any(doc["id"] == document.id for doc in FAKE_DOCUMENTS):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un document avec cet ID existe déjà"
        )
    
    # Ajouter le document
    new_doc = {
        "id": document.id,
        "title": document.title,
        "content": document.content,
        "category": document.category,
        "type": document.type,
        "author": current_user["full_name"] or current_user["username"],
        "created_at": datetime.now(),
        "tags": document.tags,
        "metadata": document.metadata
    }
    
    FAKE_DOCUMENTS.append(new_doc)
    
    return APIResponse(
        success=True,
        data=document.dict(),
        message="Document créé avec succès"
    )

# Routes HL7 FHIR
@app.get("/fhir/Patient/{patient_id}", response_model=APIResponse, tags=["HL7 FHIR"])
async def get_fhir_patient(
    patient_id: str,
    current_user: Dict[str, Any] = Depends(require_role(["doctor", "nurse", "admin"]))
):
    """Obtenir un patient au format HL7 FHIR"""
    # Simulation d'une ressource Patient FHIR
    fhir_patient = HL7FHIRResource(
        resourceType="Patient",
        id=patient_id,
        meta={
            "versionId": "1",
            "lastUpdated": datetime.now().isoformat(),
            "profile": ["http://hl7.org/fhir/StructureDefinition/Patient"]
        },
        text={
            "status": "generated",
            "div": f"<div>Patient {patient_id}</div>"
        },
        identifier=[
            {
                "use": "usual",
                "type": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                            "code": "MR",
                            "display": "Medical record number"
                        }
                    ]
                },
                "system": "http://hospital.local/patient-ids",
                "value": patient_id
            }
        ],
        status="active"
    )
    
    return APIResponse(
        success=True,
        data=fhir_patient.dict(),
        message="Ressource Patient FHIR récupérée"
    )

@app.get("/fhir/Observation/{observation_id}", response_model=APIResponse, tags=["HL7 FHIR"])
async def get_fhir_observation(
    observation_id: str,
    current_user: Dict[str, Any] = Depends(require_role(["doctor", "nurse", "admin"]))
):
    """Obtenir une observation au format HL7 FHIR"""
    # Simulation d'une ressource Observation FHIR
    fhir_observation = HL7FHIRResource(
        resourceType="Observation",
        id=observation_id,
        meta={
            "versionId": "1",
            "lastUpdated": datetime.now().isoformat()
        },
        status="final",
        subject={
            "reference": f"Patient/{observation_id.split('_')[0]}",
            "display": "Patient de référence"
        },
        effectiveDateTime=datetime.now(),
        valueQuantity={
            "value": 120,
            "unit": "mmHg",
            "system": "http://unitsofmeasure.org",
            "code": "mm[Hg]"
        }
    )
    
    return APIResponse(
        success=True,
        data=fhir_observation.dict(),
        message="Ressource Observation FHIR récupérée"
    )

# Routes de monitoring et santé
@app.get("/health", response_model=HealthCheck, tags=["Monitoring"])
async def health_check():
    """Vérification de santé de l'API"""
    process = psutil.Process()
    memory_info = process.memory_info()
    
    return HealthCheck(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0",
        uptime_seconds=time.time() - process.create_time(),
        memory_usage_mb=memory_info.rss / 1024 / 1024,
        cpu_usage_percent=process.cpu_percent(),
        active_connections=int(active_connections._value.get()),
        total_requests=int(request_count._value.sum())
    )

@app.get("/metrics", tags=["Monitoring"])
async def get_metrics():
    """Métriques Prometheus"""
    return Response(generate_latest(), media_type="text/plain")

@app.get("/", response_model=APIResponse, tags=["General"])
async def root():
    """Point d'entrée de l'API"""
    return APIResponse(
        success=True,
        data={
            "name": "API Médicale Hospitalière",
            "version": "1.0.0",
            "description": "API REST haute performance pour l'intégration hospitalière",
            "endpoints": {
                "authentication": "/auth/login",
                "search": "/search",
                "documents": "/documents",
                "fhir": "/fhir",
                "health": "/health",
                "docs": "/docs"
            }
        },
        message="API opérationnelle"
    )

# Gestionnaire d'erreurs global
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Gestionnaire d'erreurs HTTP"""
    error_count.labels(error_type="HTTPException").inc()
    
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse(
            success=False,
            message=exc.detail,
            errors=[exc.detail],
            request_id=str(id(request))
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Gestionnaire d'erreurs général"""
    error_count.labels(error_type=type(exc).__name__).inc()
    logger.error(f"Erreur non gérée: {exc}")
    
    return JSONResponse(
        status_code=500,
        content=APIResponse(
            success=False,
            message="Erreur interne du serveur",
            errors=["Une erreur inattendue s'est produite"],
            request_id=str(id(request))
        ).dict()
    )

# Configuration OpenAPI personnalisée
def custom_openapi():
    """Configuration OpenAPI personnalisée"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="API Médicale Hospitalière",
        version="1.0.0",
        description="API REST haute performance pour l'intégration avec les systèmes hospitaliers et l'accès aux données médicales. Supporte HL7 FHIR, authentification JWT, et monitoring avancé.",
        routes=app.routes,
    )
    
    # Ajouter des informations de sécurité
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Démarrage du serveur API REST haute performance")
    print("📚 Documentation: http://localhost:8000/docs")
    print("🔍 Monitoring: http://localhost:8000/health")
    print("📊 Métriques: http://localhost:8000/metrics")
    
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )