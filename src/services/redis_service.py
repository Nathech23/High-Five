"""Service Redis pour la gestion des files d'attente de rappels"""

import redis
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import asdict
import logging
from src.config.config_api import RedisConfig, RedisQueues, RedisKeys
from src.models.reminder_models import ReminderData, ReminderStatus, DeliveryStatus

logger = logging.getLogger(__name__)

class RedisService:
    """Service Redis pour la gestion des rappels"""
    
    def __init__(self, config: RedisConfig):
        self.config = config
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        """Établir la connexion Redis"""
        try:
            self.redis_client = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                decode_responses=self.config.decode_responses,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                retry_on_timeout=self.config.retry_on_timeout,
                health_check_interval=self.config.health_check_interval
            )
            
            # Test de connexion
            self.redis_client.ping()
            logger.info("Connexion Redis établie avec succès")
            
        except Exception as e:
            logger.error(f"Erreur de connexion Redis: {e}")
            raise
    
    def health_check(self) -> bool:
        """Vérifier l'état de la connexion Redis"""
        try:
            self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    # ============================================================================
    # GESTION DES QUEUES DE RAPPELS
    # ============================================================================
    
    def enqueue_scheduled_reminder(self, reminder_data: ReminderData, delay_seconds: int = 0):
        """Ajouter un rappel à la queue programmée"""
        try:
            reminder_json = json.dumps(asdict(reminder_data), default=str)
            
            if delay_seconds > 0:
                # Utiliser une queue avec délai
                execute_at = datetime.now() + timedelta(seconds=delay_seconds)
                score = execute_at.timestamp()
                self.redis_client.zadd(RedisQueues.SCHEDULED_REMINDERS, {reminder_json: score})
            else:
                # Queue immédiate
                self.redis_client.lpush(RedisQueues.IMMEDIATE_REMINDERS, reminder_json)
            
            logger.info(f"Rappel {reminder_data.id} ajouté à la queue (délai: {delay_seconds}s)")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du rappel à la queue: {e}")
            raise
    
    def enqueue_immediate_reminder(self, reminder_data: ReminderData):
        """Ajouter un rappel à la queue immédiate"""
        self.enqueue_scheduled_reminder(reminder_data, delay_seconds=0)
    
    def enqueue_retry_reminder(self, reminder_data: ReminderData, retry_delay: int):
        """Ajouter un rappel à la queue de retry"""
        try:
            reminder_json = json.dumps(asdict(reminder_data), default=str)
            execute_at = datetime.now() + timedelta(seconds=retry_delay)
            score = execute_at.timestamp()
            
            self.redis_client.zadd(RedisQueues.RETRY_REMINDERS, {reminder_json: score})
            logger.info(f"Rappel {reminder_data.id} programmé pour retry dans {retry_delay}s")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du rappel au retry: {e}")
            raise
    
    def get_due_scheduled_reminders(self, limit: int = 50) -> List[ReminderData]:
        """Récupérer les rappels programmés dus"""
        try:
            now = datetime.now().timestamp()
            
            # Récupérer les rappels dus depuis la queue programmée
            results = self.redis_client.zrangebyscore(
                RedisQueues.SCHEDULED_REMINDERS, 
                0, 
                now, 
                start=0, 
                num=limit,
                withscores=False
            )
            
            reminders = []
            for reminder_json in results:
                try:
                    reminder_dict = json.loads(reminder_json)
                    reminder_data = ReminderData(**reminder_dict)
                    reminders.append(reminder_data)
                    
                    # Supprimer de la queue programmée
                    self.redis_client.zrem(RedisQueues.SCHEDULED_REMINDERS, reminder_json)
                    
                except Exception as e:
                    logger.error(f"Erreur lors du parsing du rappel: {e}")
                    continue
            
            return reminders
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des rappels dus: {e}")
            return []
    
    def get_due_retry_reminders(self, limit: int = 50) -> List[ReminderData]:
        """Récupérer les rappels de retry dus"""
        try:
            now = datetime.now().timestamp()
            
            results = self.redis_client.zrangebyscore(
                RedisQueues.RETRY_REMINDERS, 
                0, 
                now, 
                start=0, 
                num=limit,
                withscores=False
            )
            
            reminders = []
            for reminder_json in results:
                try:
                    reminder_dict = json.loads(reminder_json)
                    reminder_data = ReminderData(**reminder_dict)
                    reminders.append(reminder_data)
                    
                    # Supprimer de la queue retry
                    self.redis_client.zrem(RedisQueues.RETRY_REMINDERS, reminder_json)
                    
                except Exception as e:
                    logger.error(f"Erreur lors du parsing du rappel retry: {e}")
                    continue
            
            return reminders
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des rappels retry: {e}")
            return []
    
    def get_immediate_reminders(self, limit: int = 50) -> List[ReminderData]:
        """Récupérer les rappels immédiats"""
        try:
            reminders = []
            
            for _ in range(min(limit, self.redis_client.llen(RedisQueues.IMMEDIATE_REMINDERS))):
                reminder_json = self.redis_client.rpop(RedisQueues.IMMEDIATE_REMINDERS)
                if reminder_json:
                    try:
                        reminder_dict = json.loads(reminder_json)
                        reminder_data = ReminderData(**reminder_dict)
                        reminders.append(reminder_data)
                    except Exception as e:
                        logger.error(f"Erreur lors du parsing du rappel immédiat: {e}")
                        continue
            
            return reminders
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des rappels immédiats: {e}")
            return []
    
    # ============================================================================
    # GESTION DU CACHE ET DES STATUTS
    # ============================================================================
    
    def cache_reminder_status(self, reminder_id: int, status: ReminderStatus, ttl: int = 3600):
        """Mettre en cache le statut d'un rappel"""
        try:
            key = RedisKeys.REMINDER_STATUS.format(reminder_id=reminder_id)
            self.redis_client.setex(key, ttl, status.value)
        except Exception as e:
            logger.error(f"Erreur lors de la mise en cache du statut: {e}")
    
    def get_cached_reminder_status(self, reminder_id: int) -> Optional[ReminderStatus]:
        """Récupérer le statut en cache d'un rappel"""
        try:
            key = RedisKeys.REMINDER_STATUS.format(reminder_id=reminder_id)
            status_str = self.redis_client.get(key)
            if status_str:
                return ReminderStatus(status_str)
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du statut en cache: {e}")
            return None
    
    def cache_delivery_status(self, twilio_sid: str, delivery_status: DeliveryStatus, ttl: int = 86400):
        """Mettre en cache le statut de livraison Twilio"""
        try:
            key = RedisKeys.DELIVERY_STATUS.format(twilio_sid=twilio_sid)
            status_data = asdict(delivery_status)
            self.redis_client.setex(key, ttl, json.dumps(status_data, default=str))
        except Exception as e:
            logger.error(f"Erreur lors de la mise en cache du statut de livraison: {e}")
    
    def get_cached_delivery_status(self, twilio_sid: str) -> Optional[DeliveryStatus]:
        """Récupérer le statut de livraison en cache"""
        try:
            key = RedisKeys.DELIVERY_STATUS.format(twilio_sid=twilio_sid)
            status_json = self.redis_client.get(key)
            if status_json:
                status_dict = json.loads(status_json)
                return DeliveryStatus(**status_dict)
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du statut de livraison: {e}")
            return None
    
    # ============================================================================
    # MÉTRIQUES ET STATISTIQUES
    # ============================================================================
    
    def increment_counter(self, metric_name: str, value: int = 1):
        """Incrémenter un compteur de métrique"""
        try:
            self.redis_client.hincrby(RedisKeys.STATS_COUNTERS, metric_name, value)
        except Exception as e:
            logger.error(f"Erreur lors de l'incrémentation du compteur {metric_name}: {e}")
    
    def set_gauge(self, metric_name: str, value: float):
        """Définir une valeur de gauge"""
        try:
            self.redis_client.hset(RedisKeys.STATS_GAUGES, metric_name, value)
        except Exception as e:
            logger.error(f"Erreur lors de la définition du gauge {metric_name}: {e}")
    
    def record_timer(self, metric_name: str, duration_ms: float):
        """Enregistrer une durée"""
        try:
            # Utiliser une liste pour stocker les dernières valeurs
            key = f"{RedisKeys.STATS_TIMERS}:{metric_name}"
            self.redis_client.lpush(key, duration_ms)
            self.redis_client.ltrim(key, 0, 999)  # Garder les 1000 dernières valeurs
            self.redis_client.expire(key, 3600)   # Expirer après 1 heure
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement du timer {metric_name}: {e}")
    
    def get_queue_sizes(self) -> Dict[str, int]:
        """Récupérer la taille des différentes queues"""
        try:
            return {
                'scheduled': self.redis_client.zcard(RedisQueues.SCHEDULED_REMINDERS),
                'immediate': self.redis_client.llen(RedisQueues.IMMEDIATE_REMINDERS),
                'retry': self.redis_client.zcard(RedisQueues.RETRY_REMINDERS),
                'failed': self.redis_client.llen(RedisQueues.FAILED_REMINDERS),
                'processing': self.redis_client.llen(RedisQueues.PROCESSING)
            }
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des tailles de queue: {e}")
            return {}
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Récupérer un résumé des métriques"""
        try:
            counters = self.redis_client.hgetall(RedisKeys.STATS_COUNTERS)
            gauges = self.redis_client.hgetall(RedisKeys.STATS_GAUGES)
            queue_sizes = self.get_queue_sizes()
            
            return {
                'counters': {k: int(v) for k, v in counters.items()},
                'gauges': {k: float(v) for k, v in gauges.items()},
                'queues': queue_sizes,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du résumé des métriques: {e}")
            return {}
    
    # ============================================================================
    # GESTION DES LOCKS DISTRIBUÉS
    # ============================================================================
    
    def acquire_lock(self, lock_name: str, timeout: int = 60) -> bool:
        """Acquérir un lock distribué"""
        try:
            lock_key = f"locks:{lock_name}"
            identifier = f"{datetime.now().timestamp()}"
            
            result = self.redis_client.set(
                lock_key, 
                identifier, 
                nx=True, 
                ex=timeout
            )
            
            return result is not None
        except Exception as e:
            logger.error(f"Erreur lors de l'acquisition du lock {lock_name}: {e}")
            return False
    
    def release_lock(self, lock_name: str) -> bool:
        """Libérer un lock distribué"""
        try:
            lock_key = f"locks:{lock_name}"
            return self.redis_client.delete(lock_key) > 0
        except Exception as e:
            logger.error(f"Erreur lors de la libération du lock {lock_name}: {e}")
            return False
    
    # ============================================================================
    # NETTOYAGE ET MAINTENANCE
    # ============================================================================
    
    def cleanup_expired_data(self):
        """Nettoyer les données expirées"""
        try:
            # Nettoyer les anciens rappels programmés (plus de 24h en retard)
            cutoff = (datetime.now() - timedelta(hours=24)).timestamp()
            
            expired_scheduled = self.redis_client.zremrangebyscore(
                RedisQueues.SCHEDULED_REMINDERS, 0, cutoff
            )
            
            expired_retry = self.redis_client.zremrangebyscore(
                RedisQueues.RETRY_REMINDERS, 0, cutoff
            )
            
            logger.info(f"Nettoyage: {expired_scheduled} rappels programmés expirés, {expired_retry} retry expirés")
            
            return expired_scheduled + expired_retry
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage: {e}")
            return 0
    
    def reset_all_queues(self):
        """Vider toutes les queues (pour les tests)"""
        try:
            queues = [
                RedisQueues.SCHEDULED_REMINDERS,
                RedisQueues.IMMEDIATE_REMINDERS,
                RedisQueues.RETRY_REMINDERS,
                RedisQueues.FAILED_REMINDERS,
                RedisQueues.PROCESSING
            ]
            
            for queue in queues:
                self.redis_client.delete(queue)
            
            logger.info("Toutes les queues ont été vidées")
            
        except Exception as e:
            logger.error(f"Erreur lors du reset des queues: {e}")
    
    def close(self):
        """Fermer la connexion Redis"""
        if self.redis_client:
            self.redis_client.close()
            logger.info("Connexion Redis fermée")