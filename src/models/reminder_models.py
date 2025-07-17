"""
Modèles de données pour le système de rappels
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from dataclasses import dataclass

class ReminderType(Enum):
    """Types de rappels disponibles"""
    APPOINTMENT = "appointment_reminder"
    MEDICATION = "medication_reminder"
    HEALTH_TIP = "health_tip"
    EMERGENCY_ALERT = "emergency_alert"
    FOLLOW_UP = "follow_up"

class ReminderStatus(Enum):
    """Statuts des rappels"""
    PENDING = "pending"          # En attente d'envoi
    SCHEDULED = "scheduled"      # Programmé
    SENT = "sent"               # Envoyé avec succès
    DELIVERED = "delivered"      # Livré (confirmé par Twilio)
    FAILED = "failed"           # Échec d'envoi
    CANCELLED = "cancelled"      # Annulé
    RETRY = "retry"             # En cours de retry

class DeliveryMethod(Enum):
    """Méthodes de livraison"""
    SMS = "sms"
    VOICE = "voice"
    BOTH = "both"

class Priority(Enum):
    """Niveaux de priorité"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

# Modèles Pydantic pour l'API

class ReminderCreate(BaseModel):
    """Modèle pour créer un nouveau rappel"""
    patient_id: int = Field(..., description="ID du patient")
    reminder_type: ReminderType = Field(..., description="Type de rappel")
    delivery_method: DeliveryMethod = Field(default=DeliveryMethod.SMS, description="Méthode de livraison")
    scheduled_time: datetime = Field(..., description="Heure programmée d'envoi")
    priority: Priority = Field(default=Priority.NORMAL, description="Priorité du rappel")
    custom_message: Optional[str] = Field(None, description="Message personnalisé (optionnel)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Métadonnées additionnelles")
    max_retries: int = Field(default=3, ge=0, le=10, description="Nombre maximum de tentatives")
    retry_interval: int = Field(default=300, ge=60, description="Intervalle entre les tentatives (secondes)")
    
    @validator('scheduled_time')
    def validate_scheduled_time(cls, v):
        if v <= datetime.now():
            raise ValueError('La date programmée doit être dans le futur')
        return v

class ReminderUpdate(BaseModel):
    """Modèle pour mettre à jour un rappel"""
    scheduled_time: Optional[datetime] = None
    priority: Optional[Priority] = None
    custom_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    max_retries: Optional[int] = Field(None, ge=0, le=10)
    retry_interval: Optional[int] = Field(None, ge=60)
    
    @validator('scheduled_time')
    def validate_scheduled_time(cls, v):
        if v and v <= datetime.now():
            raise ValueError('La date programmée doit être dans le futur')
        return v

class ReminderResponse(BaseModel):
    """Modèle de réponse pour un rappel"""
    id: int
    patient_id: int
    reminder_type: ReminderType
    delivery_method: DeliveryMethod
    status: ReminderStatus
    scheduled_time: datetime
    priority: Priority
    custom_message: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    retry_count: int
    max_retries: int
    retry_interval: int
    twilio_sid: Optional[str]
    error_message: Optional[str]
    
    class Config:
        from_attributes = True

class DeliveryStatus(BaseModel):
    """Statut de livraison d'un rappel"""
    reminder_id: int
    twilio_sid: str
    status: str
    delivered_at: Optional[datetime]
    error_code: Optional[str]
    error_message: Optional[str]

class ReminderBatch(BaseModel):
    """Modèle pour l'envoi en lot"""
    patient_ids: List[int] = Field(..., description="Liste des IDs patients")
    reminder_type: ReminderType = Field(..., description="Type de rappel")
    delivery_method: DeliveryMethod = Field(default=DeliveryMethod.SMS)
    scheduled_time: datetime = Field(..., description="Heure programmée d'envoi")
    priority: Priority = Field(default=Priority.NORMAL)
    custom_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @validator('patient_ids')
    def validate_patient_ids(cls, v):
        if len(v) == 0:
            raise ValueError('Au moins un patient doit être spécifié')
        if len(v) > 1000:
            raise ValueError('Maximum 1000 patients par lot')
        return v

class ReminderStats(BaseModel):
    """Statistiques des rappels"""
    total_reminders: int
    pending: int
    scheduled: int
    sent: int
    delivered: int
    failed: int
    cancelled: int
    delivery_rate: float
    average_delivery_time: Optional[float]  # en secondes

# Modèles de base de données (dataclasses)

@dataclass
class ReminderData:
    """Données complètes d'un rappel pour la base de données"""
    id: Optional[int] = None
    patient_id: int = None
    reminder_type: str = None
    delivery_method: str = None
    status: str = ReminderStatus.PENDING.value
    scheduled_time: Optional[datetime] = None
    priority: str = Priority.NORMAL.value
    custom_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    retry_interval: int = 300
    twilio_sid: Optional[str] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

class ScheduleRequest(BaseModel):
    """Requête pour programmer un rappel immédiat (test)"""
    patient_id: int
    reminder_type: ReminderType
    delivery_method: DeliveryMethod = DeliveryMethod.SMS
    delay_seconds: int = Field(default=10, ge=0, le=3600, description="Délai avant envoi (0 = immédiat)")
    custom_message: Optional[str] = None

class RetryRequest(BaseModel):
    """Requête pour relancer un rappel échoué"""
    reminder_id: int
    force_retry: bool = Field(default=False, description="Forcer le retry même si max_retries atteint")
    new_scheduled_time: Optional[datetime] = Field(None, description="Nouvelle heure programmée")