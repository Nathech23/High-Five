from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query, Path, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import asyncio
from contextlib import asynccontextmanager

from src.models.reminder_models import (
    ReminderCreate, ReminderUpdate, ReminderResponse, ReminderBatch,
    ReminderStats, ScheduleRequest, RetryRequest, DeliveryStatus,
    ReminderStatus, ReminderType, DeliveryMethod, Priority
)
from src.services.reminder_service import ReminderService
from src.services.communication_service import CommunicationManager
from src.database import DatabaseManager
from src.services.redis_service import RedisService
from src.services.scheduler import ReminderScheduler
from src.config.config_api import AppConfig, config

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Services globaux
db_manager = None
communication_manager = None
reminder_service = None
redis_service = None
scheduler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestionnaire de cycle de vie de l'application"""
    global db_manager, communication_manager, reminder_service, redis_service, scheduler
    
    # Initialisation
    logger.info("Initialisation des services...")
    
    try:
        # Initialiser la base de données
        db_manager = DatabaseManager()
        db_manager.create_tables()
        
        # Initialiser Redis
        redis_service = RedisService(config.redis)
        
        # Initialiser le gestionnaire de communication
        communication_manager = CommunicationManager()
        
        # Initialiser le service de rappels
        reminder_service = ReminderService(
            db_manager=db_manager,
            comm_manager=communication_manager
        )
        
        # Initialiser et démarrer le planificateur
        scheduler = ReminderScheduler(
            config=config.scheduler,
            redis_service=redis_service,
            reminder_service=reminder_service
        )
        scheduler.start()
        
        logger.info("Services initialisés avec succès")
        
        yield
        
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation: {e}")
        raise
    
    finally:
        # Nettoyage
        logger.info("Arrêt des services...")
        
        if scheduler:
            scheduler.stop()
        
        if redis_service:
            redis_service.close()
        
        # Base de données fermée automatiquement
        
        logger.info("Services arrêtés")

# Créer l'application FastAPI
app = FastAPI(
    title="API de Gestion des Rappels",
    description="API pour la gestion des rappels de rendez-vous médicaux",
    version="1.0.0",
    lifespan=lifespan
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dépendances
def get_reminder_service() -> ReminderService:
    if reminder_service is None:
        raise HTTPException(
            status_code=500, 
            detail="Service de rappels non initialisé"
        )
    return reminder_service

def get_redis_service() -> RedisService:
    if redis_service is None:
        raise HTTPException(
            status_code=500, 
            detail="Service Redis non initialisé"
        )
    return redis_service

def get_scheduler() -> ReminderScheduler:
    if scheduler is None:
        raise HTTPException(
            status_code=500, 
            detail="Planificateur non initialisé"
        )
    return scheduler

# ============================================================================
# ENDPOINT 1: Créer un rappel
# ============================================================================

@app.post("/reminders", response_model=ReminderResponse, status_code=201)
async def create_reminder(
    reminder_data: ReminderCreate,
    service: ReminderService = Depends(get_reminder_service)
):
    """
    Créer un nouveau rappel programmé
    
    - **patient_id**: ID du patient
    - **reminder_type**: Type de rappel (appointment_reminder, medication_reminder, etc.)
    - **delivery_method**: Méthode de livraison (sms, voice, both)
    - **scheduled_time**: Date et heure programmées d'envoi
    - **priority**: Priorité du rappel (low, normal, high, urgent)
    - **custom_message**: Message personnalisé (optionnel)
    - **metadata**: Métadonnées additionnelles
    - **max_retries**: Nombre maximum de tentatives en cas d'échec
    - **retry_interval**: Intervalle entre les tentatives (secondes)
    """
    try:
        reminder = await service.create_reminder(reminder_data)
        
        # Convertir en modèle de réponse
        return ReminderResponse(
            id=reminder.id,
            patient_id=reminder.patient_id,
            reminder_type=ReminderType(reminder.reminder_type),
            delivery_method=DeliveryMethod(reminder.delivery_method),
            status=ReminderStatus(reminder.status),
            scheduled_time=reminder.scheduled_time,
            priority=Priority(reminder.priority),
            custom_message=reminder.custom_message,
            metadata=reminder.metadata,
            created_at=reminder.created_at,
            updated_at=reminder.updated_at,
            sent_at=reminder.sent_at,
            delivered_at=reminder.delivered_at,
            retry_count=reminder.retry_count,
            max_retries=reminder.max_retries,
            retry_interval=reminder.retry_interval,
            twilio_sid=reminder.twilio_sid,
            error_message=reminder.error_message
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur lors de la création du rappel: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

# ============================================================================
# ENDPOINT 2: Lister et filtrer les rappels
# ============================================================================

@app.get("/reminders", response_model=List[ReminderResponse])
async def list_reminders(
    patient_id: Optional[int] = Query(None, description="Filtrer par ID patient"),
    status: Optional[ReminderStatus] = Query(None, description="Filtrer par statut"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre maximum de résultats"),
    offset: int = Query(0, ge=0, description="Décalage pour la pagination"),
    service: ReminderService = Depends(get_reminder_service)
):
    """
    Lister les rappels avec filtres optionnels
    
    - **patient_id**: Filtrer par ID patient
    - **status**: Filtrer par statut (pending, scheduled, sent, delivered, failed, cancelled)
    - **limit**: Nombre maximum de résultats (1-1000)
    - **offset**: Décalage pour la pagination
    """
    try:
        reminders = await service.list_reminders(patient_id, status, limit, offset)
        
        # Convertir en modèles de réponse
        return [
            ReminderResponse(
                id=reminder.id,
                patient_id=reminder.patient_id,
                reminder_type=ReminderType(reminder.reminder_type),
                delivery_method=DeliveryMethod(reminder.delivery_method),
                status=ReminderStatus(reminder.status),
                scheduled_time=reminder.scheduled_time,
                priority=Priority(reminder.priority),
                custom_message=reminder.custom_message,
                metadata=reminder.metadata,
                created_at=reminder.created_at,
                updated_at=reminder.updated_at,
                sent_at=reminder.sent_at,
                delivered_at=reminder.delivered_at,
                retry_count=reminder.retry_count,
                max_retries=reminder.max_retries,
                retry_interval=reminder.retry_interval,
                twilio_sid=reminder.twilio_sid,
                error_message=reminder.error_message
            )
            for reminder in reminders
        ]
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des rappels: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

# ============================================================================
# ENDPOINT 3: Gérer un rappel spécifique (GET, PUT, DELETE)
# ============================================================================

@app.get("/reminders/{reminder_id}", response_model=ReminderResponse)
async def get_reminder(
    reminder_id: int = Path(..., description="ID du rappel"),
    service: ReminderService = Depends(get_reminder_service)
):
    """
    Récupérer un rappel spécifique par son ID
    """
    try:
        reminder = await service.get_reminder(reminder_id)
        if not reminder:
            raise HTTPException(status_code=404, detail="Rappel introuvable")
        
        return ReminderResponse(
            id=reminder.id,
            patient_id=reminder.patient_id,
            reminder_type=ReminderType(reminder.reminder_type),
            delivery_method=DeliveryMethod(reminder.delivery_method),
            status=ReminderStatus(reminder.status),
            scheduled_time=reminder.scheduled_time,
            priority=Priority(reminder.priority),
            custom_message=reminder.custom_message,
            metadata=reminder.metadata,
            created_at=reminder.created_at,
            updated_at=reminder.updated_at,
            sent_at=reminder.sent_at,
            delivered_at=reminder.delivered_at,
            retry_count=reminder.retry_count,
            max_retries=reminder.max_retries,
            retry_interval=reminder.retry_interval,
            twilio_sid=reminder.twilio_sid,
            error_message=reminder.error_message
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du rappel {reminder_id}: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.put("/reminders/{reminder_id}", response_model=ReminderResponse)
async def update_reminder(
    reminder_id: int = Path(..., description="ID du rappel"),
    update_data: ReminderUpdate = None,
    service: ReminderService = Depends(get_reminder_service)
):
    """
    Mettre à jour un rappel existant
    
    - **scheduled_time**: Nouvelle date/heure programmée
    - **priority**: Nouvelle priorité
    - **custom_message**: Nouveau message personnalisé
    - **metadata**: Nouvelles métadonnées
    - **max_retries**: Nouveau nombre maximum de tentatives
    - **retry_interval**: Nouvel intervalle entre tentatives
    """
    try:
        reminder = await service.update_reminder(reminder_id, update_data)
        if not reminder:
            raise HTTPException(status_code=404, detail="Rappel introuvable")
        
        return ReminderResponse(
            id=reminder.id,
            patient_id=reminder.patient_id,
            reminder_type=ReminderType(reminder.reminder_type),
            delivery_method=DeliveryMethod(reminder.delivery_method),
            status=ReminderStatus(reminder.status),
            scheduled_time=reminder.scheduled_time,
            priority=Priority(reminder.priority),
            custom_message=reminder.custom_message,
            metadata=reminder.metadata,
            created_at=reminder.created_at,
            updated_at=reminder.updated_at,
            sent_at=reminder.sent_at,
            delivered_at=reminder.delivered_at,
            retry_count=reminder.retry_count,
            max_retries=reminder.max_retries,
            retry_interval=reminder.retry_interval,
            twilio_sid=reminder.twilio_sid,
            error_message=reminder.error_message
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du rappel {reminder_id}: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.delete("/reminders/{reminder_id}", status_code=204)
async def cancel_reminder(
    reminder_id: int = Path(..., description="ID du rappel"),
    service: ReminderService = Depends(get_reminder_service)
):
    """
    Annuler un rappel
    """
    try:
        success = await service.cancel_reminder(reminder_id)
        if not success:
            raise HTTPException(status_code=404, detail="Rappel introuvable")
        
        return JSONResponse(status_code=204, content=None)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur lors de l'annulation du rappel {reminder_id}: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

# ============================================================================
# ENDPOINT 4: Envoi immédiat pour tests
# ============================================================================

@app.post("/reminders/send-immediate", response_model=ReminderResponse)
async def send_immediate_reminder(
    schedule_request: ScheduleRequest,
    service: ReminderService = Depends(get_reminder_service)
):
    """
    Envoyer un rappel immédiatement (pour tests)
    
    - **patient_id**: ID du patient
    - **reminder_type**: Type de rappel
    - **delivery_method**: Méthode de livraison (sms, voice, both)
    - **delay_seconds**: Délai avant envoi en secondes (0 = immédiat)
    - **custom_message**: Message personnalisé (optionnel)
    """
    try:
        # Calculer l'heure d'envoi
        send_time = datetime.now() + timedelta(seconds=schedule_request.delay_seconds)
        
        # Créer le rappel avec envoi immédiat/rapide
        reminder_data = ReminderCreate(
            patient_id=schedule_request.patient_id,
            reminder_type=schedule_request.reminder_type,
            delivery_method=schedule_request.delivery_method,
            scheduled_time=send_time,
            priority=Priority.HIGH,
            custom_message=schedule_request.custom_message,
            metadata={"test_mode": True, "immediate_send": True}
        )
        
        reminder = await service.create_reminder(reminder_data)
        
        # Si délai = 0, traiter immédiatement
        if schedule_request.delay_seconds == 0:
            reminder = await service.send_immediate(
                schedule_request.patient_id,
                schedule_request.reminder_type,
                schedule_request.delivery_method,
                schedule_request.custom_message
            )
        
        return ReminderResponse(
            id=reminder.id,
            patient_id=reminder.patient_id,
            reminder_type=ReminderType(reminder.reminder_type),
            delivery_method=DeliveryMethod(reminder.delivery_method),
            status=ReminderStatus(reminder.status),
            scheduled_time=reminder.scheduled_time,
            priority=Priority(reminder.priority),
            custom_message=reminder.custom_message,
            metadata=reminder.metadata,
            created_at=reminder.created_at,
            updated_at=reminder.updated_at,
            sent_at=reminder.sent_at,
            delivered_at=reminder.delivered_at,
            retry_count=reminder.retry_count,
            max_retries=reminder.max_retries,
            retry_interval=reminder.retry_interval,
            twilio_sid=reminder.twilio_sid,
            error_message=reminder.error_message
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi immédiat: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

# ============================================================================
# ENDPOINT 5: Gestion des lots et statistiques
# ============================================================================

@app.post("/reminders/batch", response_model=List[ReminderResponse])
async def create_batch_reminders(
    batch_data: ReminderBatch,
    background_tasks: BackgroundTasks,
    service: ReminderService = Depends(get_reminder_service)
):
    """
    Créer des rappels en lot pour plusieurs patients
    
    - **patient_ids**: Liste des IDs patients (max 1000)
    - **reminder_type**: Type de rappel
    - **delivery_method**: Méthode de livraison
    - **scheduled_time**: Date/heure programmée
    - **priority**: Priorité
    - **custom_message**: Message personnalisé (optionnel)
    - **metadata**: Métadonnées
    """
    try:
        created_reminders = []
        
        for patient_id in batch_data.patient_ids:
            try:
                reminder_data = ReminderCreate(
                    patient_id=patient_id,
                    reminder_type=batch_data.reminder_type,
                    delivery_method=batch_data.delivery_method,
                    scheduled_time=batch_data.scheduled_time,
                    priority=batch_data.priority,
                    custom_message=batch_data.custom_message,
                    metadata=batch_data.metadata or {}
                )
                
                reminder = await service.create_reminder(reminder_data)
                created_reminders.append(reminder)
                
            except Exception as e:
                logger.error(f"Erreur lors de la création du rappel pour le patient {patient_id}: {e}")
                # Continuer avec les autres patients
                continue
        
        # Convertir en modèles de réponse
        return [
            ReminderResponse(
                id=reminder.id,
                patient_id=reminder.patient_id,
                reminder_type=ReminderType(reminder.reminder_type),
                delivery_method=DeliveryMethod(reminder.delivery_method),
                status=ReminderStatus(reminder.status),
                scheduled_time=reminder.scheduled_time,
                priority=Priority(reminder.priority),
                custom_message=reminder.custom_message,
                metadata=reminder.metadata,
                created_at=reminder.created_at,
                updated_at=reminder.updated_at,
                sent_at=reminder.sent_at,
                delivered_at=reminder.delivered_at,
                retry_count=reminder.retry_count,
                max_retries=reminder.max_retries,
                retry_interval=reminder.retry_interval,
                twilio_sid=reminder.twilio_sid,
                error_message=reminder.error_message
            )
            for reminder in created_reminders
        ]
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur lors de la création en lot: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.get("/reminders/stats", response_model=ReminderStats)
async def get_reminder_stats(
    service: ReminderService = Depends(get_reminder_service)
):
    """
    Obtenir les statistiques des rappels
    
    Retourne:
    - Nombre total de rappels
    - Répartition par statut
    - Taux de livraison
    - Temps moyen de livraison
    """
    try:
        stats = await service.get_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

# ============================================================================
# ENDPOINTS ADDITIONNELS: Retry et webhooks
# ============================================================================

@app.post("/reminders/{reminder_id}/retry", response_model=ReminderResponse)
async def retry_reminder(
    reminder_id: int = Path(..., description="ID du rappel"),
    retry_request: RetryRequest = None,
    service: ReminderService = Depends(get_reminder_service)
):
    """
    Relancer un rappel échoué
    
    - **force_retry**: Forcer le retry même si max_retries atteint
    - **new_scheduled_time**: Nouvelle heure programmée (optionnel)
    """
    try:
        if retry_request and retry_request.new_scheduled_time:
            # Mettre à jour l'heure programmée d'abord
            update_data = ReminderUpdate(scheduled_time=retry_request.new_scheduled_time)
            await service.update_reminder(reminder_id, update_data)
        
        success = await service.retry_failed_reminder(
            reminder_id, 
            force=retry_request.force_retry if retry_request else False
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Rappel introuvable")
        
        # Récupérer le rappel mis à jour
        reminder = await service.get_reminder(reminder_id)
        
        return ReminderResponse(
            id=reminder.id,
            patient_id=reminder.patient_id,
            reminder_type=ReminderType(reminder.reminder_type),
            delivery_method=DeliveryMethod(reminder.delivery_method),
            status=ReminderStatus(reminder.status),
            scheduled_time=reminder.scheduled_time,
            priority=Priority(reminder.priority),
            custom_message=reminder.custom_message,
            metadata=reminder.metadata,
            created_at=reminder.created_at,
            updated_at=reminder.updated_at,
            sent_at=reminder.sent_at,
            delivered_at=reminder.delivered_at,
            retry_count=reminder.retry_count,
            max_retries=reminder.max_retries,
            retry_interval=reminder.retry_interval,
            twilio_sid=reminder.twilio_sid,
            error_message=reminder.error_message
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erreur lors du retry du rappel {reminder_id}: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@app.post("/webhook/twilio/status")
async def twilio_status_webhook(
    request: Request,
    service: ReminderService = Depends(get_reminder_service)
):
    """
    Webhook pour recevoir les mises à jour de statut de Twilio
    
    Ce endpoint est appelé par Twilio pour notifier les changements de statut
    des SMS et appels vocaux.
    """
    try:
        # Récupérer les données du webhook
        form_data = await request.form()
        
        # Extraire les informations du webhook Twilio
        message_sid = form_data.get('MessageSid')
        message_status = form_data.get('MessageStatus')
        error_code = form_data.get('ErrorCode')
        error_message = form_data.get('ErrorMessage')
        
        if not message_sid:
            raise HTTPException(status_code=400, detail="MessageSid manquant")
        
        # Créer l'objet de statut de livraison
        delivery_status = DeliveryStatus(
            twilio_sid=message_sid,
            status=message_status,
            error_code=error_code,
            error_message=error_message,
            timestamp=datetime.now()
        )
        
        # Mettre à jour le statut du rappel
        success = await service.update_delivery_status(
            twilio_sid=delivery_status.twilio_sid,
            status=delivery_status.status,
            error_code=delivery_status.error_code,
            error_message=delivery_status.error_message
        )
        
        if success:
            return {"status": "success", "message": "Statut mis à jour"}
        else:
            return {"status": "warning", "message": "Rappel introuvable"}
        
    except Exception as e:
        logger.error(f"Erreur lors du traitement du webhook Twilio: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

# ============================================================================
# ENDPOINTS DE SANTÉ ET MONITORING
# ============================================================================

@app.get("/health")
async def health_check(
    redis_service: RedisService = Depends(get_redis_service),
    scheduler_service: ReminderScheduler = Depends(get_scheduler)
) -> Dict[str, Any]:
    """
    Vérification de santé de l'API
    """
    try:
        # Vérifier Redis
        redis_healthy = redis_service.health_check()
        
        # Vérifier le planificateur
        scheduler_status = scheduler_service.get_status()
        
        # Vérifier la base de données
        db_healthy = True
        try:
            if db_manager:
                # Test simple de connexion DB
                await db_manager.get_session().execute("SELECT 1")
        except:
            db_healthy = False
        
        overall_healthy = redis_healthy and scheduler_status['running'] and db_healthy
        
        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "redis": "healthy" if redis_healthy else "unhealthy",
                "scheduler": "healthy" if scheduler_status['running'] else "unhealthy",
                "database": "healthy" if db_healthy else "unhealthy"
            },
            "scheduler_stats": scheduler_status['stats'],
            "queue_sizes": scheduler_status['queue_sizes']
        }
        
    except Exception as e:
        logger.error(f"Erreur health check: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/metrics")
async def get_metrics(
    redis_service: RedisService = Depends(get_redis_service),
    scheduler_service: ReminderScheduler = Depends(get_scheduler)
) -> Dict[str, Any]:
    """
    Récupérer les métriques détaillées du système
    """
    try:
        # Métriques Redis
        redis_metrics = redis_service.get_metrics_summary()
        
        # Statut du planificateur
        scheduler_status = scheduler_service.get_status()
        
        # Métriques de la base de données
        db_stats = await reminder_service.get_reminder_stats()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "redis_metrics": redis_metrics,
            "scheduler_status": scheduler_status,
            "database_stats": db_stats,
            "system_info": {
                "api_version": "1.0.0",
                "environment": config.environment,
                "timezone": config.timezone
            }
        }
        
    except Exception as e:
        logger.error(f"Erreur récupération métriques: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/scheduler/force-process")
async def force_process_reminders(
    scheduler_service: ReminderScheduler = Depends(get_scheduler)
) -> Dict[str, Any]:
    """
    Forcer le traitement immédiat des rappels (pour les tests)
    """
    try:
        result = scheduler_service.force_process_reminders()
        return result
        
    except Exception as e:
        logger.error(f"Erreur traitement forcé: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/cleanup")
async def cleanup_old_data(
    days_to_keep: int = Query(90, description="Nombre de jours à conserver"),
    redis_service: RedisService = Depends(get_redis_service)
) -> Dict[str, Any]:
    """
    Nettoyer les anciennes données
    """
    try:
        # Nettoyer Redis
        redis_cleaned = redis_service.cleanup_expired_data()
        
        # Nettoyer la base de données
        db_cleaned = await db_manager.cleanup_old_reminders(days_to_keep)
        
        return {
            "status": "success",
            "redis_items_cleaned": redis_cleaned,
            "db_reminders_cleaned": db_cleaned,
            "days_kept": days_to_keep
        }
        
    except Exception as e:
        logger.error(f"Erreur nettoyage: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """
    Page d'accueil de l'API
    """
    return {
        "message": "API Rappels - Hôpital Général de Douala",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="192.168.1.101", port=8000, log_level="info")