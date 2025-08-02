#!/usr/bin/env python3
"""
Continuous Updater - Objectif 2

Implémente un système de mise à jour continue pour la base de connaissances médicales.
Gère les mises à jour automatiques, la synchronisation et la validation en temps réel.

Auteur: Équipe Hackathon Hôpital Général de Douala
Version: 3.0.0
"""

import os
import json
import time
import logging
import threading
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Vérification des dépendances optionnelles
try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False
    logger.warning("schedule non disponible - planification limitée")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests non disponible - synchronisation externe limitée")

class UpdateType(Enum):
    """Types de mise à jour"""
    CONTENT = "content"
    METADATA = "metadata"
    VALIDATION = "validation"
    INDEX = "index"
    FULL = "full"

class UpdateStatus(Enum):
    """Statuts de mise à jour"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class UpdatePriority(Enum):
    """Priorités de mise à jour"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class UpdateRequest:
    """Requête de mise à jour"""
    id: str
    type: UpdateType
    priority: UpdatePriority
    source: str
    target: str
    data: Dict[str, Any]
    created_at: datetime
    scheduled_at: Optional[datetime] = None
    status: UpdateStatus = UpdateStatus.PENDING
    progress: float = 0.0
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class UpdateResult:
    """Résultat de mise à jour"""
    request_id: str
    status: UpdateStatus
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: float
    items_processed: int
    items_updated: int
    items_failed: int
    error_details: List[str]
    performance_metrics: Dict[str, Any]

@dataclass
class SyncSource:
    """Source de synchronisation"""
    id: str
    name: str
    type: str  # "api", "file", "database", "ftp"
    url: str
    credentials: Dict[str, str]
    sync_frequency: str  # "hourly", "daily", "weekly"
    last_sync: Optional[datetime]
    enabled: bool = True
    filters: Optional[Dict[str, Any]] = None

class ContinuousUpdater:
    """Système de mise à jour continue"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {
            "update_frequency": "hourly",
            "max_concurrent_updates": 3,
            "retry_attempts": 3,
            "retry_delay": 60,  # secondes
            "backup_before_update": True,
            "validation_required": True,
            "auto_rollback_on_failure": True
        }
        
        self.update_queue: List[UpdateRequest] = []
        self.active_updates: Dict[str, UpdateRequest] = {}
        self.update_history: List[UpdateResult] = []
        self.sync_sources: List[SyncSource] = []
        
        self.is_running = False
        self.update_thread = None
        self.scheduler_thread = None
        
        # Callbacks
        self.on_update_start: Optional[Callable] = None
        self.on_update_complete: Optional[Callable] = None
        self.on_update_failed: Optional[Callable] = None
        
        # Métriques
        self.metrics = {
            "total_updates": 0,
            "successful_updates": 0,
            "failed_updates": 0,
            "average_update_time": 0.0,
            "last_update": None,
            "uptime_hours": 0.0
        }
        
        self.start_time = datetime.now()
        
        logger.info("ContinuousUpdater initialisé")
        
    def add_sync_source(self, source: SyncSource) -> bool:
        """Ajoute une source de synchronisation"""
        try:
            # Vérification de l'unicité
            if any(s.id == source.id for s in self.sync_sources):
                logger.error(f"Source {source.id} déjà existante")
                return False
                
            self.sync_sources.append(source)
            logger.info(f"Source de sync ajoutée: {source.name}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur ajout source: {e}")
            return False
            
    def create_update_request(self, 
                            update_type: UpdateType,
                            source: str,
                            target: str,
                            data: Dict[str, Any],
                            priority: UpdatePriority = UpdatePriority.NORMAL,
                            scheduled_at: Optional[datetime] = None) -> str:
        """Crée une requête de mise à jour"""
        
        request_id = f"update_{int(time.time())}_{len(self.update_queue)}"
        
        request = UpdateRequest(
            id=request_id,
            type=update_type,
            priority=priority,
            source=source,
            target=target,
            data=data,
            created_at=datetime.now(),
            scheduled_at=scheduled_at,
            metadata={
                "created_by": "continuous_updater",
                "version": "3.0.0"
            }
        )
        
        # Insertion selon la priorité
        self._insert_by_priority(request)
        
        logger.info(f"Requête de mise à jour créée: {request_id} ({update_type.value})")
        return request_id
        
    def _insert_by_priority(self, request: UpdateRequest):
        """Insère la requête selon sa priorité"""
        inserted = False
        for i, existing in enumerate(self.update_queue):
            if request.priority.value > existing.priority.value:
                self.update_queue.insert(i, request)
                inserted = True
                break
                
        if not inserted:
            self.update_queue.append(request)
            
    def start_continuous_updates(self) -> bool:
        """Démarre le système de mise à jour continue"""
        if self.is_running:
            logger.warning("Système déjà en cours d'exécution")
            return False
            
        try:
            self.is_running = True
            
            # Thread principal de traitement
            self.update_thread = threading.Thread(
                target=self._update_worker,
                daemon=True
            )
            self.update_thread.start()
            
            # Thread de planification
            if SCHEDULE_AVAILABLE:
                self.scheduler_thread = threading.Thread(
                    target=self._scheduler_worker,
                    daemon=True
                )
                self.scheduler_thread.start()
                
            logger.info("Système de mise à jour continue démarré")
            return True
            
        except Exception as e:
            logger.error(f"Erreur démarrage: {e}")
            self.is_running = False
            return False
            
    def stop_continuous_updates(self):
        """Arrête le système de mise à jour continue"""
        logger.info("Arrêt du système de mise à jour...")
        self.is_running = False
        
        # Attendre la fin des mises à jour en cours
        max_wait = 30  # secondes
        waited = 0
        while self.active_updates and waited < max_wait:
            time.sleep(1)
            waited += 1
            
        logger.info("Système de mise à jour arrêté")
        
    def _update_worker(self):
        """Worker principal pour traiter les mises à jour"""
        logger.info("Worker de mise à jour démarré")
        
        while self.is_running:
            try:
                # Vérifier s'il y a des mises à jour à traiter
                if (len(self.active_updates) < self.config["max_concurrent_updates"] and 
                    self.update_queue):
                    
                    # Prendre la prochaine requête
                    request = self.update_queue.pop(0)
                    
                    # Vérifier si c'est le moment de l'exécuter
                    if (request.scheduled_at is None or 
                        request.scheduled_at <= datetime.now()):
                        
                        # Démarrer la mise à jour
                        self._start_update(request)
                        
                    else:
                        # Remettre en queue si pas encore le moment
                        self.update_queue.append(request)
                        
                time.sleep(1)  # Pause courte
                
            except Exception as e:
                logger.error(f"Erreur dans update_worker: {e}")
                time.sleep(5)
                
        logger.info("Worker de mise à jour arrêté")
        
    def _scheduler_worker(self):
        """Worker pour la planification automatique"""
        if not SCHEDULE_AVAILABLE:
            return
            
        logger.info("Scheduler de mise à jour démarré")
        
        # Configuration des tâches planifiées
        schedule.every().hour.do(self._scheduled_sync_check)
        schedule.every().day.at("02:00").do(self._scheduled_full_sync)
        schedule.every().week.do(self._scheduled_cleanup)
        
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Vérifier chaque minute
            except Exception as e:
                logger.error(f"Erreur dans scheduler: {e}")
                time.sleep(300)  # Attendre 5 minutes en cas d'erreur
                
        logger.info("Scheduler arrêté")
        
    def _scheduled_sync_check(self):
        """Vérification planifiée des sources de sync"""
        logger.info("Vérification planifiée des sources...")
        
        for source in self.sync_sources:
            if source.enabled:
                self._check_source_for_updates(source)
                
    def _scheduled_full_sync(self):
        """Synchronisation complète planifiée"""
        logger.info("Synchronisation complète planifiée...")
        
        self.create_update_request(
            UpdateType.FULL,
            "scheduler",
            "knowledge_base",
            {"type": "full_sync"},
            UpdatePriority.HIGH
        )
        
    def _scheduled_cleanup(self):
        """Nettoyage planifié"""
        logger.info("Nettoyage planifié...")
        
        # Nettoyer l'historique ancien (> 30 jours)
        cutoff_date = datetime.now() - timedelta(days=30)
        original_count = len(self.update_history)
        
        self.update_history = [
            result for result in self.update_history
            if result.start_time > cutoff_date
        ]
        
        cleaned_count = original_count - len(self.update_history)
        logger.info(f"Historique nettoyé: {cleaned_count} entrées supprimées")
        
    def _check_source_for_updates(self, source: SyncSource):
        """Vérifie une source pour des mises à jour"""
        try:
            # Vérifier la fréquence
            if source.last_sync:
                if source.sync_frequency == "hourly":
                    next_sync = source.last_sync + timedelta(hours=1)
                elif source.sync_frequency == "daily":
                    next_sync = source.last_sync + timedelta(days=1)
                elif source.sync_frequency == "weekly":
                    next_sync = source.last_sync + timedelta(weeks=1)
                else:
                    next_sync = source.last_sync + timedelta(hours=1)
                    
                if datetime.now() < next_sync:
                    return  # Pas encore le moment
                    
            # Créer une requête de mise à jour
            self.create_update_request(
                UpdateType.CONTENT,
                source.id,
                "knowledge_base",
                {
                    "source_type": source.type,
                    "source_url": source.url,
                    "filters": source.filters
                },
                UpdatePriority.NORMAL
            )
            
            # Mettre à jour la dernière sync
            source.last_sync = datetime.now()
            
        except Exception as e:
            logger.error(f"Erreur vérification source {source.id}: {e}")
            
    def _start_update(self, request: UpdateRequest):
        """Démarre une mise à jour"""
        try:
            request.status = UpdateStatus.IN_PROGRESS
            self.active_updates[request.id] = request
            
            # Callback de début
            if self.on_update_start:
                self.on_update_start(request)
                
            # Démarrer le thread de mise à jour
            update_thread = threading.Thread(
                target=self._execute_update,
                args=(request,),
                daemon=True
            )
            update_thread.start()
            
        except Exception as e:
            logger.error(f"Erreur démarrage mise à jour {request.id}: {e}")
            self._handle_update_failure(request, str(e))
            
    def _execute_update(self, request: UpdateRequest):
        """Exécute une mise à jour"""
        start_time = datetime.now()
        result = UpdateResult(
            request_id=request.id,
            status=UpdateStatus.IN_PROGRESS,
            start_time=start_time,
            end_time=None,
            duration_seconds=0.0,
            items_processed=0,
            items_updated=0,
            items_failed=0,
            error_details=[],
            performance_metrics={}
        )
        
        try:
            logger.info(f"Exécution mise à jour {request.id} ({request.type.value})")
            
            # Backup si requis
            if self.config["backup_before_update"]:
                self._create_backup(request)
                
            # Exécution selon le type
            if request.type == UpdateType.CONTENT:
                result = self._update_content(request, result)
            elif request.type == UpdateType.METADATA:
                result = self._update_metadata(request, result)
            elif request.type == UpdateType.VALIDATION:
                result = self._update_validation(request, result)
            elif request.type == UpdateType.INDEX:
                result = self._update_index(request, result)
            elif request.type == UpdateType.FULL:
                result = self._update_full(request, result)
                
            # Finalisation
            end_time = datetime.now()
            result.end_time = end_time
            result.duration_seconds = (end_time - start_time).total_seconds()
            result.status = UpdateStatus.COMPLETED
            
            request.status = UpdateStatus.COMPLETED
            request.progress = 100.0
            
            # Mise à jour des métriques
            self._update_metrics(result)
            
            # Callback de succès
            if self.on_update_complete:
                self.on_update_complete(request, result)
                
            logger.info(f"Mise à jour {request.id} terminée avec succès")
            
        except Exception as e:
            logger.error(f"Erreur exécution mise à jour {request.id}: {e}")
            result.status = UpdateStatus.FAILED
            result.error_details.append(str(e))
            self._handle_update_failure(request, str(e))
            
        finally:
            # Nettoyage
            if request.id in self.active_updates:
                del self.active_updates[request.id]
                
            self.update_history.append(result)
            
    def _update_content(self, request: UpdateRequest, result: UpdateResult) -> UpdateResult:
        """Met à jour le contenu"""
        logger.info(f"Mise à jour contenu depuis {request.source}")
        
        # Simulation de mise à jour de contenu
        items_to_process = request.data.get("item_count", 100)
        
        for i in range(items_to_process):
            try:
                # Simulation du traitement
                time.sleep(0.01)  # Simulation du temps de traitement
                
                # Mise à jour du progrès
                request.progress = (i + 1) / items_to_process * 100
                result.items_processed += 1
                
                # Simulation de succès/échec
                if i % 50 == 0 and i > 0:  # Échec occasionnel
                    result.items_failed += 1
                    result.error_details.append(f"Échec traitement item {i}")
                else:
                    result.items_updated += 1
                    
            except Exception as e:
                result.items_failed += 1
                result.error_details.append(f"Erreur item {i}: {e}")
                
        return result
        
    def _update_metadata(self, request: UpdateRequest, result: UpdateResult) -> UpdateResult:
        """Met à jour les métadonnées"""
        logger.info("Mise à jour métadonnées")
        
        # Simulation
        result.items_processed = 50
        result.items_updated = 48
        result.items_failed = 2
        
        return result
        
    def _update_validation(self, request: UpdateRequest, result: UpdateResult) -> UpdateResult:
        """Met à jour la validation"""
        logger.info("Mise à jour validation")
        
        # Simulation
        result.items_processed = 200
        result.items_updated = 195
        result.items_failed = 5
        
        return result
        
    def _update_index(self, request: UpdateRequest, result: UpdateResult) -> UpdateResult:
        """Met à jour l'index"""
        logger.info("Mise à jour index vectoriel")
        
        # Simulation
        result.items_processed = 1000
        result.items_updated = 1000
        result.items_failed = 0
        
        return result
        
    def _update_full(self, request: UpdateRequest, result: UpdateResult) -> UpdateResult:
        """Mise à jour complète"""
        logger.info("Mise à jour complète")
        
        # Simulation d'une mise à jour complète
        result.items_processed = 2000
        result.items_updated = 1950
        result.items_failed = 50
        
        return result
        
    def _create_backup(self, request: UpdateRequest):
        """Crée un backup avant mise à jour"""
        logger.info(f"Création backup pour {request.id}")
        # Simulation du backup
        time.sleep(0.5)
        
    def _handle_update_failure(self, request: UpdateRequest, error: str):
        """Gère l'échec d'une mise à jour"""
        request.status = UpdateStatus.FAILED
        request.error_message = error
        
        # Callback d'échec
        if self.on_update_failed:
            self.on_update_failed(request, error)
            
        # Auto-rollback si configuré
        if self.config["auto_rollback_on_failure"]:
            self._rollback_update(request)
            
    def _rollback_update(self, request: UpdateRequest):
        """Effectue un rollback"""
        logger.info(f"Rollback de la mise à jour {request.id}")
        # Simulation du rollback
        time.sleep(1)
        
    def _update_metrics(self, result: UpdateResult):
        """Met à jour les métriques"""
        self.metrics["total_updates"] += 1
        
        if result.status == UpdateStatus.COMPLETED:
            self.metrics["successful_updates"] += 1
        else:
            self.metrics["failed_updates"] += 1
            
        # Temps moyen
        total_time = sum(r.duration_seconds for r in self.update_history if r.end_time)
        completed_updates = len([r for r in self.update_history if r.end_time])
        
        if completed_updates > 0:
            self.metrics["average_update_time"] = total_time / completed_updates
            
        self.metrics["last_update"] = datetime.now().isoformat()
        
        # Uptime
        uptime = datetime.now() - self.start_time
        self.metrics["uptime_hours"] = uptime.total_seconds() / 3600
        
    def get_update_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Retourne le statut d'une mise à jour"""
        # Chercher dans les actives
        if request_id in self.active_updates:
            request = self.active_updates[request_id]
            return {
                "id": request.id,
                "type": request.type.value,
                "status": request.status.value,
                "progress": request.progress,
                "created_at": request.created_at.isoformat(),
                "error_message": request.error_message
            }
            
        # Chercher dans l'historique
        for result in self.update_history:
            if result.request_id == request_id:
                return {
                    "id": result.request_id,
                    "status": result.status.value,
                    "start_time": result.start_time.isoformat(),
                    "end_time": result.end_time.isoformat() if result.end_time else None,
                    "duration_seconds": result.duration_seconds,
                    "items_processed": result.items_processed,
                    "items_updated": result.items_updated,
                    "items_failed": result.items_failed
                }
                
        return None
        
    def get_system_status(self) -> Dict[str, Any]:
        """Retourne le statut du système"""
        return {
            "is_running": self.is_running,
            "active_updates": len(self.active_updates),
            "queued_updates": len(self.update_queue),
            "sync_sources": len(self.sync_sources),
            "metrics": self.metrics.copy(),
            "uptime_hours": self.metrics["uptime_hours"],
            "last_update": self.metrics["last_update"]
        }
        
    def export_data(self, output_path: str) -> Dict[str, Any]:
        """Exporte les données du système"""
        export_data = {
            "metadata": {
                "export_date": datetime.now().isoformat(),
                "system_version": "3.0.0",
                "objective": "Objectif 2 - Système de mise à jour continue"
            },
            "system_status": self.get_system_status(),
            "sync_sources": [asdict(source) for source in self.sync_sources],
            "update_history": [],
            "configuration": self.config
        }
        
        # Export de l'historique (derniers 100)
        recent_history = self.update_history[-100:]
        for result in recent_history:
            result_data = asdict(result)
            result_data["start_time"] = result.start_time.isoformat()
            if result.end_time:
                result_data["end_time"] = result.end_time.isoformat()
            export_data["update_history"].append(result_data)
            
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
                
            return {
                "success": True,
                "file_path": output_path,
                "records_exported": len(export_data["update_history"])
            }
            
        except Exception as e:
            logger.error(f"Erreur export: {e}")
            return {
                "success": False,
                "error": str(e)
            }

def main():
    """Fonction principale de démonstration"""
    print("🔄 Continuous Updater - Objectif 2")
    print("Système de mise à jour continue")
    print("=" * 50)
    
    # Initialisation
    updater = ContinuousUpdater({
        "update_frequency": "hourly",
        "max_concurrent_updates": 2,
        "retry_attempts": 3,
        "backup_before_update": True,
        "validation_required": True
    })
    
    # Ajout de sources de synchronisation
    print("\n📡 Configuration des sources de sync...")
    
    sources = [
        SyncSource(
            id="pubmed_api",
            name="PubMed API",
            type="api",
            url="https://api.pubmed.gov",
            credentials={"api_key": "demo_key"},
            sync_frequency="daily"
        ),
        SyncSource(
            id="who_guidelines",
            name="WHO Guidelines",
            type="api",
            url="https://who.int/api/guidelines",
            credentials={},
            sync_frequency="weekly"
        ),
        SyncSource(
            id="local_docs",
            name="Documents Locaux",
            type="file",
            url="/data/medical_docs",
            credentials={},
            sync_frequency="hourly"
        )
    ]
    
    for source in sources:
        updater.add_sync_source(source)
        
    print(f"Sources configurées: {len(updater.sync_sources)}")
    
    # Démarrage du système
    print("\n🚀 Démarrage du système de mise à jour...")
    if updater.start_continuous_updates():
        print("Système démarré avec succès")
    else:
        print("Erreur démarrage système")
        return
        
    # Création de requêtes de test
    print("\n📝 Création de requêtes de mise à jour...")
    
    requests_created = []
    
    # Mise à jour de contenu
    req1 = updater.create_update_request(
        UpdateType.CONTENT,
        "pubmed_api",
        "knowledge_base",
        {"item_count": 150, "domain": "cardiologie"},
        UpdatePriority.HIGH
    )
    requests_created.append(req1)
    
    # Mise à jour d'index
    req2 = updater.create_update_request(
        UpdateType.INDEX,
        "system",
        "vector_index",
        {"rebuild": True},
        UpdatePriority.NORMAL
    )
    requests_created.append(req2)
    
    # Validation
    req3 = updater.create_update_request(
        UpdateType.VALIDATION,
        "expert_system",
        "knowledge_base",
        {"validation_level": "expert"},
        UpdatePriority.CRITICAL
    )
    requests_created.append(req3)
    
    print(f"Requêtes créées: {len(requests_created)}")
    
    # Monitoring des mises à jour
    print("\n📊 Monitoring des mises à jour...")
    
    monitoring_duration = 15  # secondes
    start_monitoring = time.time()
    
    while time.time() - start_monitoring < monitoring_duration:
        status = updater.get_system_status()
        print(f"\rActives: {status['active_updates']}, Queue: {status['queued_updates']}, Total: {status['metrics']['total_updates']}", end="")
        time.sleep(1)
        
    print("\n")
    
    # Statut final
    print("\n📈 Statut final du système...")
    final_status = updater.get_system_status()
    print(f"Mises à jour totales: {final_status['metrics']['total_updates']}")
    print(f"Succès: {final_status['metrics']['successful_updates']}")
    print(f"Échecs: {final_status['metrics']['failed_updates']}")
    print(f"Temps moyen: {final_status['metrics']['average_update_time']:.2f}s")
    
    # Vérification des requêtes
    print("\n🔍 Vérification des requêtes...")
    for req_id in requests_created:
        status = updater.get_update_status(req_id)
        if status:
            print(f"Requête {req_id}: {status['status']}")
            
    # Export des données
    print("\n💾 Export des données...")
    export_result = updater.export_data("continuous_updater_export.json")
    if export_result["success"]:
        print(f"Données exportées: {export_result['records_exported']} enregistrements")
        
    # Arrêt du système
    print("\n🛑 Arrêt du système...")
    updater.stop_continuous_updates()
    
    print("\n✅ Objectif 2 - Système de mise à jour continue implémenté!")
    print(f"📊 {final_status['metrics']['total_updates']} mises à jour traitées")

if __name__ == "__main__":
    main()