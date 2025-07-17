"""
Service de gestion des rappels avec Redis et planification
"""

import json
import redis
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import asdict
import logging
from contextlib import asynccontextmanager

from src.models.reminder_models import (
    ReminderData, ReminderStatus, ReminderType, DeliveryMethod, Priority,
    ReminderCreate, ReminderUpdate, DeliveryStatus, ReminderStats
)
from src.services.communication_service import CommunicationManager
from src.database.database import DatabaseManager
from src.services.templates_manager import PatientData

logger = logging.getLogger(__name__)

class ReminderService:
    """Service principal de gestion des rappels"""
    
    def __init__(self, db_manager: DatabaseManager, comm_manager: CommunicationManager, 
                 redis_host: str = "localhost", redis_port: int = 6379, redis_db: int = 0):
        self.db = db_manager
        self.comm = comm_manager
        
        # Configuration Redis
        try:
            self.redis_client = redis.Redis(
                host=redis_host, 
                port=redis_port, 
                db=redis_db,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            # Test de connexion
            self.redis_client.ping()
            logger.info(f"Connexion Redis établie: {redis_host}:{redis_port}")
        except Exception as e:
            logger.warning(f"Redis non disponible: {e}. Mode dégradé activé.")
            self.redis_client = None
        
        # Clés Redis
        self.QUEUE_KEY = "reminders:queue"
        self.SCHEDULED_KEY = "reminders:scheduled"
        self.PROCESSING_KEY = "reminders:processing"
        self.STATS_KEY = "reminders:stats"
        
        # Worker en cours d'exécution
        self._worker_running = False
        self._worker_task = None
    
    async def create_reminder(self, reminder_data: ReminderCreate) -> ReminderData:
        """Créer un nouveau rappel"""
        # Vérifier que le patient existe
        patient = await self.db.get_patient_by_id(reminder_data.patient_id)
        if not patient:
            raise ValueError(f"Patient {reminder_data.patient_id} introuvable")
        
        # Créer l'objet rappel
        reminder = ReminderData(
            patient_id=reminder_data.patient_id,
            reminder_type=reminder_data.reminder_type.value,
            delivery_method=reminder_data.delivery_method.value,
            scheduled_time=reminder_data.scheduled_time,
            priority=reminder_data.priority.value,
            custom_message=reminder_data.custom_message,
            metadata=reminder_data.metadata or {},
            max_retries=reminder_data.max_retries,
            retry_interval=reminder_data.retry_interval
        )
        
        # Sauvegarder en base
        reminder_id = await self._save_reminder_to_db(reminder)
        reminder.id = reminder_id
        
        # Ajouter à la file d'attente Redis
        await self._schedule_reminder(reminder)
        
        logger.info(f"Rappel créé: ID={reminder_id}, Patient={reminder_data.patient_id}, Type={reminder_data.reminder_type.value}")
        return reminder
    
    async def update_reminder(self, reminder_id: int, update_data: ReminderUpdate) -> Optional[ReminderData]:
        """Mettre à jour un rappel existant"""
        reminder = await self._get_reminder_from_db(reminder_id)
        if not reminder:
            return None
        
        # Vérifier que le rappel peut être modifié
        if reminder.status in [ReminderStatus.SENT.value, ReminderStatus.DELIVERED.value, ReminderStatus.CANCELLED.value]:
            raise ValueError(f"Impossible de modifier un rappel avec le statut: {reminder.status}")
        
        # Appliquer les modifications
        if update_data.scheduled_time:
            reminder.scheduled_time = update_data.scheduled_time
        if update_data.priority:
            reminder.priority = update_data.priority.value
        if update_data.custom_message is not None:
            reminder.custom_message = update_data.custom_message
        if update_data.metadata:
            reminder.metadata.update(update_data.metadata)
        if update_data.max_retries is not None:
            reminder.max_retries = update_data.max_retries
        if update_data.retry_interval is not None:
            reminder.retry_interval = update_data.retry_interval
        
        reminder.updated_at = datetime.now()
        
        # Sauvegarder en base
        await self._update_reminder_in_db(reminder)
        
        # Reprogrammer si nécessaire
        if update_data.scheduled_time:
            await self._reschedule_reminder(reminder)
        
        logger.info(f"Rappel mis à jour: ID={reminder_id}")
        return reminder
    
    async def cancel_reminder(self, reminder_id: int) -> bool:
        """Annuler un rappel"""
        reminder = await self._get_reminder_from_db(reminder_id)
        if not reminder:
            return False
        
        if reminder.status in [ReminderStatus.SENT.value, ReminderStatus.DELIVERED.value]:
            raise ValueError(f"Impossible d'annuler un rappel déjà envoyé")
        
        # Marquer comme annulé
        reminder.status = ReminderStatus.CANCELLED.value
        reminder.updated_at = datetime.now()
        
        await self._update_reminder_in_db(reminder)
        await self._remove_from_queue(reminder_id)
        
        logger.info(f"Rappel annulé: ID={reminder_id}")
        return True
    
    async def get_reminder(self, reminder_id: int) -> Optional[ReminderData]:
        """Récupérer un rappel par son ID"""
        return await self._get_reminder_from_db(reminder_id)
    
    async def list_reminders(self, patient_id: Optional[int] = None, 
                           status: Optional[ReminderStatus] = None,
                           limit: int = 100, offset: int = 0) -> List[ReminderData]:
        """Lister les rappels avec filtres"""
        return await self._list_reminders_from_db(patient_id, status, limit, offset)
    
    async def send_immediate(self, patient_id: int, reminder_type: ReminderType, 
                           delivery_method: DeliveryMethod = DeliveryMethod.SMS,
                           custom_message: Optional[str] = None) -> ReminderData:
        """Envoyer un rappel immédiatement (pour tests)"""
        # Créer un rappel avec envoi immédiat
        reminder_data = ReminderCreate(
            patient_id=patient_id,
            reminder_type=reminder_type,
            delivery_method=delivery_method,
            scheduled_time=datetime.now() + timedelta(seconds=5),  # 5 secondes de délai
            custom_message=custom_message,
            priority=Priority.HIGH
        )
        
        reminder = await self.create_reminder(reminder_data)
        
        # Traitement immédiat
        await self._process_reminder(reminder)
        
        return reminder
    
    async def retry_failed_reminder(self, reminder_id: int, force: bool = False) -> bool:
        """Relancer un rappel échoué"""
        reminder = await self._get_reminder_from_db(reminder_id)
        if not reminder:
            return False
        
        if reminder.status != ReminderStatus.FAILED.value and not force:
            raise ValueError(f"Le rappel n'est pas en échec: {reminder.status}")
        
        if reminder.retry_count >= reminder.max_retries and not force:
            raise ValueError(f"Nombre maximum de tentatives atteint: {reminder.retry_count}/{reminder.max_retries}")
        
        # Reprogrammer pour un envoi immédiat
        reminder.status = ReminderStatus.RETRY.value
        reminder.scheduled_time = datetime.now() + timedelta(seconds=reminder.retry_interval)
        reminder.updated_at = datetime.now()
        
        await self._update_reminder_in_db(reminder)
        await self._schedule_reminder(reminder)
        
        logger.info(f"Rappel reprogrammé pour retry: ID={reminder_id}")
        return True
    
    async def get_stats(self) -> ReminderStats:
        """Obtenir les statistiques des rappels"""
        stats_data = await self._get_stats_from_db()
        
        # Calculer le taux de livraison
        total_sent = stats_data.get('sent', 0) + stats_data.get('delivered', 0)
        delivery_rate = (stats_data.get('delivered', 0) / total_sent * 100) if total_sent > 0 else 0
        
        return ReminderStats(
            total_reminders=stats_data.get('total', 0),
            pending=stats_data.get('pending', 0),
            scheduled=stats_data.get('scheduled', 0),
            sent=stats_data.get('sent', 0),
            delivered=stats_data.get('delivered', 0),
            failed=stats_data.get('failed', 0),
            cancelled=stats_data.get('cancelled', 0),
            delivery_rate=round(delivery_rate, 2),
            average_delivery_time=stats_data.get('avg_delivery_time')
        )
    
    async def update_delivery_status(self, twilio_sid: str, status: str, 
                                   error_code: Optional[str] = None,
                                   error_message: Optional[str] = None) -> bool:
        """Mettre à jour le statut de livraison depuis Twilio webhook"""
        reminder = await self._get_reminder_by_twilio_sid(twilio_sid)
        if not reminder:
            logger.warning(f"Rappel introuvable pour Twilio SID: {twilio_sid}")
            return False
        
        # Mapper les statuts Twilio vers nos statuts
        status_mapping = {
            'delivered': ReminderStatus.DELIVERED.value,
            'sent': ReminderStatus.SENT.value,
            'failed': ReminderStatus.FAILED.value,
            'undelivered': ReminderStatus.FAILED.value
        }
        
        new_status = status_mapping.get(status.lower(), reminder.status)
        
        if new_status != reminder.status:
            reminder.status = new_status
            reminder.updated_at = datetime.now()
            
            if new_status == ReminderStatus.DELIVERED.value:
                reminder.delivered_at = datetime.now()
            elif new_status == ReminderStatus.FAILED.value:
                reminder.error_message = error_message or f"Erreur Twilio: {error_code}"
                # Programmer un retry si possible
                if reminder.retry_count < reminder.max_retries:
                    await self._schedule_retry(reminder)
            
            await self._update_reminder_in_db(reminder)
            logger.info(f"Statut mis à jour: ID={reminder.id}, Status={new_status}")
        
        return True
    
    # Méthodes privées pour la gestion Redis
    
    async def _schedule_reminder(self, reminder: ReminderData):
        """Ajouter un rappel à la file d'attente Redis"""
        if not self.redis_client:
            logger.warning("Redis non disponible, rappel non programmé dans la queue")
            return
        
        try:
            # Calculer le timestamp d'envoi
            timestamp = reminder.scheduled_time.timestamp()
            
            # Données du rappel pour Redis
            reminder_json = json.dumps({
                'id': reminder.id,
                'patient_id': reminder.patient_id,
                'reminder_type': reminder.reminder_type,
                'delivery_method': reminder.delivery_method,
                'priority': reminder.priority,
                'custom_message': reminder.custom_message,
                'metadata': reminder.metadata
            })
            
            # Ajouter au sorted set avec timestamp comme score
            self.redis_client.zadd(self.SCHEDULED_KEY, {reminder_json: timestamp})
            
            logger.debug(f"Rappel programmé dans Redis: ID={reminder.id}, Time={reminder.scheduled_time}")
        except Exception as e:
            logger.error(f"Erreur lors de la programmation Redis: {e}")
    
    async def _reschedule_reminder(self, reminder: ReminderData):
        """Reprogrammer un rappel dans Redis"""
        if not self.redis_client:
            return
        
        # Supprimer l'ancienne entrée et ajouter la nouvelle
        await self._remove_from_queue(reminder.id)
        await self._schedule_reminder(reminder)
    
    async def _remove_from_queue(self, reminder_id: int):
        """Supprimer un rappel de la file d'attente Redis"""
        if not self.redis_client:
            return
        
        try:
            # Rechercher et supprimer le rappel dans le sorted set
            members = self.redis_client.zrange(self.SCHEDULED_KEY, 0, -1)
            for member in members:
                data = json.loads(member)
                if data.get('id') == reminder_id:
                    self.redis_client.zrem(self.SCHEDULED_KEY, member)
                    break
        except Exception as e:
            logger.error(f"Erreur lors de la suppression Redis: {e}")
    
    async def _schedule_retry(self, reminder: ReminderData):
        """Programmer un retry pour un rappel échoué"""
        reminder.retry_count += 1
        reminder.status = ReminderStatus.RETRY.value
        reminder.scheduled_time = datetime.now() + timedelta(seconds=reminder.retry_interval)
        
        await self._update_reminder_in_db(reminder)
        await self._schedule_reminder(reminder)
        
        logger.info(f"Retry programmé: ID={reminder.id}, Tentative={reminder.retry_count}/{reminder.max_retries}")
    
    # Worker pour traiter la file d'attente
    
    async def start_worker(self):
        """Démarrer le worker de traitement des rappels"""
        if self._worker_running:
            logger.warning("Worker déjà en cours d'exécution")
            return
        
        self._worker_running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("Worker de rappels démarré")
    
    async def stop_worker(self):
        """Arrêter le worker de traitement des rappels"""
        if not self._worker_running:
            return
        
        self._worker_running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Worker de rappels arrêté")
    
    async def _worker_loop(self):
        """Boucle principale du worker"""
        while self._worker_running:
            try:
                await self._process_due_reminders()
                await asyncio.sleep(10)  # Vérifier toutes les 10 secondes
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erreur dans le worker: {e}")
                await asyncio.sleep(30)  # Attendre plus longtemps en cas d'erreur
    
    async def _process_due_reminders(self):
        """Traiter les rappels dus"""
        if not self.redis_client:
            # Mode dégradé: vérifier directement en base
            await self._process_due_reminders_from_db()
            return
        
        try:
            current_time = datetime.now().timestamp()
            
            # Récupérer les rappels dus
            due_reminders = self.redis_client.zrangebyscore(
                self.SCHEDULED_KEY, 0, current_time, withscores=True
            )
            
            for reminder_json, score in due_reminders:
                try:
                    reminder_data = json.loads(reminder_json)
                    reminder = await self._get_reminder_from_db(reminder_data['id'])
                    
                    if reminder and reminder.status in [ReminderStatus.SCHEDULED.value, ReminderStatus.RETRY.value]:
                        await self._process_reminder(reminder)
                    
                    # Supprimer de la file d'attente
                    self.redis_client.zrem(self.SCHEDULED_KEY, reminder_json)
                    
                except Exception as e:
                    logger.error(f"Erreur lors du traitement d'un rappel: {e}")
                    # Supprimer l'entrée défectueuse
                    self.redis_client.zrem(self.SCHEDULED_KEY, reminder_json)
        
        except Exception as e:
            logger.error(f"Erreur lors du traitement des rappels dus: {e}")
    
    async def _process_due_reminders_from_db(self):
        """Mode dégradé: traiter les rappels dus directement depuis la base"""
        try:
            # Récupérer les rappels dus depuis la base
            due_reminders = await self._get_due_reminders_from_db()
            
            for reminder in due_reminders:
                try:
                    await self._process_reminder(reminder)
                except Exception as e:
                    logger.error(f"Erreur lors du traitement du rappel {reminder.id}: {e}")
        
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des rappels dus: {e}")
    
    async def _process_reminder(self, reminder: ReminderData):
        """Traiter un rappel individuel"""
        try:
            # Récupérer les données du patient
            patient = await self.db.get_patient_by_id(reminder.patient_id)
            if not patient:
                raise ValueError(f"Patient {reminder.patient_id} introuvable")
            
            # Marquer comme en cours de traitement
            reminder.status = ReminderStatus.PENDING.value
            await self._update_reminder_in_db(reminder)
            
            # Envoyer le message
            if reminder.delivery_method == DeliveryMethod.SMS.value:
                result = await self._send_sms_reminder(reminder, patient)
            elif reminder.delivery_method == DeliveryMethod.VOICE.value:
                result = await self._send_voice_reminder(reminder, patient)
            elif reminder.delivery_method == DeliveryMethod.BOTH.value:
                # Envoyer SMS puis appel vocal
                sms_result = await self._send_sms_reminder(reminder, patient)
                voice_result = await self._send_voice_reminder(reminder, patient)
                result = sms_result and voice_result
            else:
                raise ValueError(f"Méthode de livraison inconnue: {reminder.delivery_method}")
            
            # Mettre à jour le statut
            if result:
                reminder.status = ReminderStatus.SENT.value
                reminder.sent_at = datetime.now()
            else:
                reminder.status = ReminderStatus.FAILED.value
                if reminder.retry_count < reminder.max_retries:
                    await self._schedule_retry(reminder)
            
            reminder.updated_at = datetime.now()
            await self._update_reminder_in_db(reminder)
            
            logger.info(f"Rappel traité: ID={reminder.id}, Status={reminder.status}")
        
        except Exception as e:
            logger.error(f"Erreur lors du traitement du rappel {reminder.id}: {e}")
            reminder.status = ReminderStatus.FAILED.value
            reminder.error_message = str(e)
            reminder.updated_at = datetime.now()
            await self._update_reminder_in_db(reminder)
    
    async def _send_sms_reminder(self, reminder: ReminderData, patient: PatientData) -> bool:
        """Envoyer un rappel par SMS"""
        try:
            # Utiliser le message personnalisé ou générer automatiquement
            if reminder.custom_message:
                message = reminder.custom_message
                language = patient.preferred_language or 'fr'
            else:
                # Générer le message avec le template manager
                message_data = self.comm.template_manager.personalizer.create_personalized_message(
                    ReminderType(reminder.reminder_type), patient, "sms"
                )
                message = message_data['message']
                language = message_data['language']
            
            # Envoyer le SMS
            result = self.comm.twilio.send_sms(patient.phone, message)
            
            if result['success']:
                reminder.twilio_sid = result['message_sid']
                return True
            else:
                reminder.error_message = result.get('error', 'Erreur inconnue')
                return False
        
        except Exception as e:
            reminder.error_message = str(e)
            return False
    
    async def _send_voice_reminder(self, reminder: ReminderData, patient: PatientData) -> bool:
        """Envoyer un rappel par appel vocal"""
        try:
            # Utiliser le message personnalisé ou générer automatiquement
            if reminder.custom_message:
                # Pour les appels vocaux, on utilise TwiML
                twiml_content = f"<Response><Say voice='alice' language='fr'>{reminder.custom_message}</Say></Response>"
            else:
                # Générer le TwiML avec le template manager
                message_data = self.comm.template_manager.personalizer.create_personalized_message(
                    ReminderType(reminder.reminder_type), patient, "twiml"
                )
                twiml_content = message_data['message']
            
            # Créer l'URL TwiML
            twiml_url = await self.comm.twiml_service.create_twiml_url(twiml_content)
            
            # Faire l'appel vocal
            result = self.comm.twilio.make_voice_call(patient.phone, twiml_url)
            
            if result['success']:
                reminder.twilio_sid = result['call_sid']
                return True
            else:
                reminder.error_message = result.get('error', 'Erreur inconnue')
                return False
        
        except Exception as e:
            reminder.error_message = str(e)
            return False
    
    # Méthodes d'accès à la base de données (à implémenter selon votre schéma)
    
    async def _save_reminder_to_db(self, reminder: ReminderData) -> int:
        """Sauvegarder un rappel en base et retourner son ID"""
        # TODO: Implémenter selon votre schéma de base de données
        # Pour l'instant, simulation avec un ID aléatoire
        import random
        reminder_id = random.randint(1000, 9999)
        logger.info(f"Rappel sauvegardé en base (simulé): ID={reminder_id}")
        return reminder_id
    
    async def _get_reminder_from_db(self, reminder_id: int) -> Optional[ReminderData]:
        """Récupérer un rappel depuis la base"""
        # TODO: Implémenter selon votre schéma de base de données
        return None
    
    async def _update_reminder_in_db(self, reminder: ReminderData):
        """Mettre à jour un rappel en base"""
        # TODO: Implémenter selon votre schéma de base de données
        logger.debug(f"Rappel mis à jour en base (simulé): ID={reminder.id}")
    
    async def _list_reminders_from_db(self, patient_id: Optional[int], status: Optional[ReminderStatus], 
                                    limit: int, offset: int) -> List[ReminderData]:
        """Lister les rappels depuis la base"""
        # TODO: Implémenter selon votre schéma de base de données
        return []
    
    async def _get_reminder_by_twilio_sid(self, twilio_sid: str) -> Optional[ReminderData]:
        """Récupérer un rappel par son SID Twilio"""
        # TODO: Implémenter selon votre schéma de base de données
        return None
    
    async def _get_stats_from_db(self) -> Dict[str, Any]:
        """Récupérer les statistiques depuis la base"""
        # TODO: Implémenter selon votre schéma de base de données
        return {
            'total': 0,
            'pending': 0,
            'scheduled': 0,
            'sent': 0,
            'delivered': 0,
            'failed': 0,
            'cancelled': 0,
            'avg_delivery_time': None
        }
    
    async def _get_due_reminders_from_db(self) -> List[ReminderData]:
        """Récupérer les rappels dus depuis la base (mode dégradé)"""
        # TODO: Implémenter selon votre schéma de base de données
        return []