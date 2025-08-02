"""Configuration pour l'API de rappels et Redis
Hôpital Général de Douala"""

import os
from typing import Optional
from dataclasses import dataclass

@dataclass
class RedisConfig:
    """Configuration Redis"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    decode_responses: bool = True
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    
    @classmethod
    def from_env(cls):
        """Créer la configuration depuis les variables d'environnement"""
        return cls(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            password=os.getenv("REDIS_PASSWORD"),
            decode_responses=True,
            socket_timeout=int(os.getenv("REDIS_SOCKET_TIMEOUT", "5")),
            socket_connect_timeout=int(os.getenv("REDIS_CONNECT_TIMEOUT", "5")),
            retry_on_timeout=True,
            health_check_interval=int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL", "30"))
        )

@dataclass
class APIConfig:
    """Configuration de l'API FastAPI"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    reload: bool = False
    workers: int = 1
    log_level: str = "info"
    cors_origins: list = None
    
    # Paramètres de l'API
    max_reminders_per_batch: int = 100
    default_page_size: int = 20
    max_page_size: int = 100
    
    # Paramètres de retry
    default_max_retries: int = 3
    default_retry_interval: int = 300  # 5 minutes
    max_retry_interval: int = 3600     # 1 heure
    
    # Paramètres de sécurité
    api_key_header: str = "X-API-Key"
    api_key: Optional[str] = None
    
    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["*"] if self.debug else []
    
    @classmethod
    def from_env(cls):
        """Créer la configuration depuis les variables d'environnement"""
        return cls(
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "8000")),
            debug=os.getenv("API_DEBUG", "false").lower() == "true",
            reload=os.getenv("API_RELOAD", "false").lower() == "true",
            workers=int(os.getenv("API_WORKERS", "1")),
            log_level=os.getenv("API_LOG_LEVEL", "info"),
            max_reminders_per_batch=int(os.getenv("MAX_REMINDERS_PER_BATCH", "100")),
            default_page_size=int(os.getenv("DEFAULT_PAGE_SIZE", "20")),
            max_page_size=int(os.getenv("MAX_PAGE_SIZE", "100")),
            default_max_retries=int(os.getenv("DEFAULT_MAX_RETRIES", "3")),
            default_retry_interval=int(os.getenv("DEFAULT_RETRY_INTERVAL", "300")),
            max_retry_interval=int(os.getenv("MAX_RETRY_INTERVAL", "3600")),
            api_key=os.getenv("API_KEY")
        )

@dataclass
class SchedulerConfig:
    """Configuration du planificateur de rappels"""
    check_interval: int = 60  # Vérifier toutes les 60 secondes
    batch_size: int = 50      # Traiter 50 rappels à la fois
    worker_threads: int = 4   # Nombre de threads pour l'envoi
    max_queue_size: int = 1000
    
    # Paramètres de retry
    retry_delays: list = None  # [300, 900, 1800] = 5min, 15min, 30min
    max_retry_attempts: int = 3
    
    # Paramètres de monitoring
    metrics_interval: int = 300  # Calculer les métriques toutes les 5 minutes
    cleanup_interval: int = 86400  # Nettoyer une fois par jour
    
    def __post_init__(self):
        if self.retry_delays is None:
            self.retry_delays = [300, 900, 1800]  # 5min, 15min, 30min
    
    @classmethod
    def from_env(cls):
        """Créer la configuration depuis les variables d'environnement"""
        retry_delays_str = os.getenv("SCHEDULER_RETRY_DELAYS", "300,900,1800")
        retry_delays = [int(x.strip()) for x in retry_delays_str.split(",")]
        
        return cls(
            check_interval=int(os.getenv("SCHEDULER_CHECK_INTERVAL", "60")),
            batch_size=int(os.getenv("SCHEDULER_BATCH_SIZE", "50")),
            worker_threads=int(os.getenv("SCHEDULER_WORKER_THREADS", "4")),
            max_queue_size=int(os.getenv("SCHEDULER_MAX_QUEUE_SIZE", "1000")),
            retry_delays=retry_delays,
            max_retry_attempts=int(os.getenv("SCHEDULER_MAX_RETRY_ATTEMPTS", "3")),
            metrics_interval=int(os.getenv("SCHEDULER_METRICS_INTERVAL", "300")),
            cleanup_interval=int(os.getenv("SCHEDULER_CLEANUP_INTERVAL", "86400"))
        )

@dataclass
class AppConfig:
    """Configuration globale de l'application"""
    redis: RedisConfig
    api: APIConfig
    scheduler: SchedulerConfig
    
    # Environnement
    environment: str = "development"
    timezone: str = "Africa/Douala"
    
    @classmethod
    def from_env(cls):
        """Créer la configuration complète depuis les variables d'environnement"""
        return cls(
            redis=RedisConfig.from_env(),
            api=APIConfig.from_env(),
            scheduler=SchedulerConfig.from_env(),
            environment=os.getenv("ENVIRONMENT", "development"),
            timezone=os.getenv("TIMEZONE", "Africa/Douala")
        )
    
    @property
    def is_production(self) -> bool:
        """Vérifier si on est en production"""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Vérifier si on est en développement"""
        return self.environment.lower() == "development"

# Instance globale de configuration
config = AppConfig.from_env()

# Constantes pour les queues Redis
class RedisQueues:
    """Noms des queues Redis"""
    SCHEDULED_REMINDERS = "reminders:scheduled"
    IMMEDIATE_REMINDERS = "reminders:immediate"
    RETRY_REMINDERS = "reminders:retry"
    FAILED_REMINDERS = "reminders:failed"
    PROCESSING = "reminders:processing"
    
    # Clés pour les métriques
    METRICS_DAILY = "metrics:daily:{date}"
    METRICS_HOURLY = "metrics:hourly:{date}:{hour}"
    
    # Clés pour les locks
    SCHEDULER_LOCK = "locks:scheduler"
    METRICS_LOCK = "locks:metrics"
    CLEANUP_LOCK = "locks:cleanup"

class RedisKeys:
    """Clés Redis pour le cache et les données temporaires"""
    REMINDER_STATUS = "reminder:status:{reminder_id}"
    PATIENT_REMINDERS = "patient:reminders:{patient_id}"
    DELIVERY_STATUS = "delivery:status:{twilio_sid}"
    RATE_LIMIT = "rate_limit:{identifier}:{window}"
    
    # Statistiques en temps réel
    STATS_COUNTERS = "stats:counters"
    STATS_GAUGES = "stats:gauges"
    STATS_TIMERS = "stats:timers"