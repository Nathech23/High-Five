"""Planificateur de rappels médicaux"""

import asyncio
import threading
import time
from datetime import datetime, timedelta
from typing import List, Optional
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict

from src.config.config_api import SchedulerConfig
from src.services.redis_service import RedisService
from src.services.reminder_service import ReminderService
from src.models.reminder_models import ReminderData, ReminderStatus

logger = logging.getLogger(__name__)

class ReminderScheduler:
    """Planificateur pour le traitement des rappels médicaux"""
    
    def __init__(self, 
                 config: SchedulerConfig,
                 redis_service: RedisService,
                 reminder_service: ReminderService):
        self.config = config
        self.redis_service = redis_service
        self.reminder_service = reminder_service
        
        # État du planificateur
        self._running = False
        self._scheduler_thread = None
        self._metrics_thread = None
        self._cleanup_thread = None
        
        # Pool de threads pour l'envoi des rappels
        self._executor = ThreadPoolExecutor(max_workers=config.worker_threads)
        
        # Statistiques
        self._stats = {
            'processed_count': 0,
            'success_count': 0,
            'error_count': 0,
            'retry_count': 0,
            'last_run': None,
            'last_error': None
        }
    
    def start(self):
        """Démarrer le planificateur"""
        if self._running:
            logger.warning("Le planificateur est déjà en cours d'exécution")
            return
        
        logger.info("Démarrage du planificateur de rappels")
        self._running = True
        
        # Démarrer les threads de traitement
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._metrics_thread = threading.Thread(target=self._metrics_loop, daemon=True)
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        
        self._scheduler_thread.start()
        self._metrics_thread.start()
        self._cleanup_thread.start()
        
        logger.info("Planificateur démarré avec succès")
    
    def stop(self):
        """Arrêter le planificateur"""
        if not self._running:
            return
        
        logger.info("Arrêt du planificateur de rappels")
        self._running = False
        
        # Attendre l'arrêt des threads
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=10)
        if self._metrics_thread:
            self._metrics_thread.join(timeout=5)
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
        
        # Fermer le pool de threads
        self._executor.shutdown(wait=True)
        
        logger.info("Planificateur arrêté")
    
    def _scheduler_loop(self):
        """Boucle principale du planificateur"""
        logger.info("Boucle du planificateur démarrée")
        
        while self._running:
            try:
                start_time = time.time()
                
                # Acquérir un lock pour éviter les exécutions concurrentes
                if self.redis_service.acquire_lock("scheduler", timeout=self.config.check_interval):
                    try:
                        self._process_due_reminders()
                    finally:
                        self.redis_service.release_lock("scheduler")
                else:
                    logger.debug("Lock du planificateur déjà acquis, passage du cycle")
                
                # Calculer le temps d'attente
                elapsed = time.time() - start_time
                sleep_time = max(0, self.config.check_interval - elapsed)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Erreur dans la boucle du planificateur: {e}")
                self._stats['last_error'] = str(e)
                time.sleep(self.config.check_interval)
        
        logger.info("Boucle du planificateur terminée")
    
    def _process_due_reminders(self):
        """Traiter les rappels dus"""
        try:
            self._stats['last_run'] = datetime.now()
            
            # Récupérer les rappels dus depuis Redis
            scheduled_reminders = self.redis_service.get_due_scheduled_reminders(self.config.batch_size)
            retry_reminders = self.redis_service.get_due_retry_reminders(self.config.batch_size)
            immediate_reminders = self.redis_service.get_immediate_reminders(self.config.batch_size)
            
            all_reminders = scheduled_reminders + retry_reminders + immediate_reminders
            
            if not all_reminders:
                logger.debug("Aucun rappel à traiter")
                return
            
            logger.info(f"Traitement de {len(all_reminders)} rappels")
            
            # Traiter les rappels en parallèle
            futures = []
            for reminder in all_reminders:
                future = self._executor.submit(self._process_single_reminder, reminder)
                futures.append(future)
            
            # Attendre la completion de tous les rappels
            for future in futures:
                try:
                    future.result(timeout=30)  # Timeout de 30 secondes par rappel
                except Exception as e:
                    logger.error(f"Erreur lors du traitement d'un rappel: {e}")
                    self._stats['error_count'] += 1
            
            # Mettre à jour les métriques Redis
            self.redis_service.increment_counter('reminders_processed', len(all_reminders))
            self.redis_service.set_gauge('last_batch_size', len(all_reminders))
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement des rappels dus: {e}")
            self._stats['last_error'] = str(e)
    
    def _process_single_reminder(self, reminder: ReminderData):
        """Traiter un rappel individuel"""
        try:
            start_time = time.time()
            
            logger.info(f"Traitement du rappel {reminder.id}")
            
            # Marquer le rappel comme en cours de traitement
            self.redis_service.cache_reminder_status(
                reminder.id, 
                ReminderStatus.PROCESSING,
                ttl=300  # 5 minutes
            )
            
            # Envoyer le rappel
            success = self.reminder_service.send_reminder(reminder)
            
            if success:
                logger.info(f"Rappel {reminder.id} envoyé avec succès")
                self._stats['success_count'] += 1
                self.redis_service.increment_counter('reminders_sent_success')
            else:
                logger.warning(f"Échec de l'envoi du rappel {reminder.id}")
                self._handle_failed_reminder(reminder)
            
            # Enregistrer le temps de traitement
            processing_time = (time.time() - start_time) * 1000
            self.redis_service.record_timer('reminder_processing_time', processing_time)
            
            self._stats['processed_count'] += 1
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement du rappel {reminder.id}: {e}")
            self._handle_failed_reminder(reminder, error_message=str(e))
            self._stats['error_count'] += 1
    
    def _handle_failed_reminder(self, reminder: ReminderData, error_message: str = None):
        """Gérer un rappel qui a échoué"""
        try:
            # Incrémenter le compteur de retry
            reminder.retry_count += 1
            reminder.error_message = error_message
            
            if reminder.retry_count < reminder.max_retries:
                # Programmer un retry
                retry_delay = self._calculate_retry_delay(reminder.retry_count)
                reminder.status = ReminderStatus.RETRY
                
                # Mettre à jour en base de données
                self.reminder_service.update_reminder(reminder)
                
                # Ajouter à la queue de retry
                self.redis_service.enqueue_retry_reminder(reminder, retry_delay)
                
                logger.info(f"Rappel {reminder.id} programmé pour retry #{reminder.retry_count} dans {retry_delay}s")
                self._stats['retry_count'] += 1
                self.redis_service.increment_counter('reminders_retried')
                
            else:
                # Marquer comme définitivement échoué
                reminder.status = ReminderStatus.FAILED
                self.reminder_service.update_reminder(reminder)
                
                logger.error(f"Rappel {reminder.id} définitivement échoué après {reminder.retry_count} tentatives")
                self.redis_service.increment_counter('reminders_failed_final')
            
        except Exception as e:
            logger.error(f"Erreur lors de la gestion de l'échec du rappel {reminder.id}: {e}")
    
    def _calculate_retry_delay(self, retry_count: int) -> int:
        """Calculer le délai de retry avec backoff exponentiel"""
        if retry_count <= len(self.config.retry_delays):
            return self.config.retry_delays[retry_count - 1]
        else:
            # Backoff exponentiel pour les retries supplémentaires
            base_delay = self.config.retry_delays[-1]
            return min(base_delay * (2 ** (retry_count - len(self.config.retry_delays))), 3600)
    
    def _metrics_loop(self):
        """Boucle pour calculer les métriques périodiques"""
        logger.info("Boucle des métriques démarrée")
        
        while self._running:
            try:
                if self.redis_service.acquire_lock("metrics", timeout=self.config.metrics_interval):
                    try:
                        self._calculate_metrics()
                    finally:
                        self.redis_service.release_lock("metrics")
                
                time.sleep(self.config.metrics_interval)
                
            except Exception as e:
                logger.error(f"Erreur dans la boucle des métriques: {e}")
                time.sleep(self.config.metrics_interval)
        
        logger.info("Boucle des métriques terminée")
    
    def _calculate_metrics(self):
        """Calculer et mettre à jour les métriques"""
        try:
            # Mettre à jour les métriques Redis
            queue_sizes = self.redis_service.get_queue_sizes()
            for queue_name, size in queue_sizes.items():
                self.redis_service.set_gauge(f'queue_size_{queue_name}', size)
            
            # Métriques du planificateur
            self.redis_service.set_gauge('scheduler_processed_count', self._stats['processed_count'])
            self.redis_service.set_gauge('scheduler_success_count', self._stats['success_count'])
            self.redis_service.set_gauge('scheduler_error_count', self._stats['error_count'])
            
            logger.debug("Métriques calculées et mises à jour")
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul des métriques: {e}")
    
    def _cleanup_loop(self):
        """Boucle pour le nettoyage périodique"""
        logger.info("Boucle de nettoyage démarrée")
        
        while self._running:
            try:
                if self.redis_service.acquire_lock("cleanup", timeout=self.config.cleanup_interval):
                    try:
                        self._perform_cleanup()
                    finally:
                        self.redis_service.release_lock("cleanup")
                
                time.sleep(self.config.cleanup_interval)
                
            except Exception as e:
                logger.error(f"Erreur dans la boucle de nettoyage: {e}")
                time.sleep(self.config.cleanup_interval)
        
        logger.info("Boucle de nettoyage terminée")
    
    def _perform_cleanup(self):
        """Effectuer le nettoyage périodique"""
        try:
            # Nettoyer les données expirées dans Redis
            expired_count = self.redis_service.cleanup_expired_data()
            
            logger.info(f"Nettoyage effectué: {expired_count} éléments Redis")
            
            self.redis_service.increment_counter('cleanup_redis_items', expired_count)
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage: {e}")
    
    def get_status(self) -> dict:
        """Récupérer le statut du planificateur"""
        return {
            'running': self._running,
            'stats': self._stats.copy(),
            'config': {
                'check_interval': self.config.check_interval,
                'batch_size': self.config.batch_size,
                'worker_threads': self.config.worker_threads,
                'max_retry_attempts': self.config.max_retry_attempts
            },
            'queue_sizes': self.redis_service.get_queue_sizes(),
            'redis_metrics': self.redis_service.get_metrics_summary()
        }
    
    def force_process_reminders(self) -> dict:
        """Forcer le traitement immédiat des rappels (pour les tests)"""
        if not self._running:
            return {'error': 'Planificateur non démarré'}
        
        try:
            start_time = time.time()
            initial_stats = self._stats.copy()
            
            self._process_due_reminders()
            
            processing_time = time.time() - start_time
            processed_count = self._stats['processed_count'] - initial_stats['processed_count']
            
            return {
                'success': True,
                'processed_count': processed_count,
                'processing_time_seconds': processing_time,
                'stats': self._stats.copy()
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement forcé: {e}")
            return {'error': str(e)}