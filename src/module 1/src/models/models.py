"""
Modèles de données pour le système de rappels hospitaliers
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date, Time, ForeignKey, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, time
import json

Base = declarative_base()

class ReminderType(Base):
    """Types de rappels avec support multilingue"""
    __tablename__ = 'reminder_types'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    template_fr = Column(Text, nullable=False)
    template_en = Column(Text, nullable=False)
    template_es = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    reminders = relationship("Reminder", back_populates="reminder_type")
    
    def get_template(self, language='fr'):
        """Retourne le template dans la langue spécifiée"""
        templates = {
            'fr': self.template_fr,
            'en': self.template_en,
            'es': self.template_es
        }
        return templates.get(language, self.template_fr)
    
    def __repr__(self):
        return f"<ReminderType(name='{self.name}', active={self.is_active})>"

class Patient(Base):
    """Informations des patients"""
    __tablename__ = 'patients'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone_number = Column(String(20))
    email = Column(String(150))
    date_of_birth = Column(Date)
    gender = Column(String(10))
    address = Column(Text)
    emergency_contact = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    reminders = relationship("Reminder", back_populates="patient", cascade="all, delete-orphan")
    contact_preference = relationship("ContactPreference", back_populates="patient", uselist=False, cascade="all, delete-orphan")
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self):
        return f"<Patient(name='{self.full_name}', phone='{self.phone_number}')>"

class Reminder(Base):
    """Rappels planifiés"""
    __tablename__ = 'reminders'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey('patients.id'), nullable=False)
    reminder_type_id = Column(Integer, ForeignKey('reminder_types.id'), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text)
    scheduled_date = Column(Date, nullable=False)
    scheduled_time = Column(Time, nullable=False)
    timezone = Column(String(50), default='Africa/Douala')
    priority_level = Column(Integer, default=1)
    status = Column(String(20), default='pending')
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    last_attempt_at = Column(DateTime)
    sent_at = Column(DateTime)
    delivered_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Contraintes
    __table_args__ = (
        CheckConstraint('priority_level >= 1 AND priority_level <= 5', name='check_priority_level'),
        CheckConstraint("status IN ('pending', 'sent', 'delivered', 'failed', 'cancelled')", name='check_status'),
    )
    
    # Relations
    patient = relationship("Patient", back_populates="reminders")
    reminder_type = relationship("ReminderType", back_populates="reminders")
    
    @property
    def is_overdue(self):
        """Vérifie si le rappel est en retard"""
        from datetime import datetime, date, time as dt_time
        now = datetime.now()
        scheduled_datetime = datetime.combine(self.scheduled_date, self.scheduled_time)
        return scheduled_datetime < now and self.status == 'pending'
    
    @property
    def can_retry(self):
        """Vérifie si le rappel peut être retenté"""
        return self.retry_count < self.max_retries and self.status in ['failed', 'pending']
    
    def format_message(self, **kwargs):
        """Formate le message avec les variables fournies"""
        if self.message:
            return self.message.format(**kwargs)
        return None
    
    def __repr__(self):
        return f"<Reminder(title='{self.title}', date='{self.scheduled_date}', status='{self.status}')>"

class ContactPreference(Base):
    """Préférences de contact des patients"""
    __tablename__ = 'contact_preferences'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey('patients.id'), nullable=False, unique=True)
    preferred_language = Column(String(5), default='fr')
    sms_enabled = Column(Boolean, default=True)
    email_enabled = Column(Boolean, default=False)
    call_enabled = Column(Boolean, default=False)
    whatsapp_enabled = Column(Boolean, default=False)
    preferred_time_start = Column(Time, default=time(8, 0))
    preferred_time_end = Column(Time, default=time(18, 0))
    timezone = Column(String(50), default='Africa/Douala')
    do_not_disturb_days = Column(Text)  # JSON array des jours à éviter
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Contraintes
    __table_args__ = (
        CheckConstraint("preferred_language IN ('fr', 'en', 'es')", name='check_preferred_language'),
    )
    
    # Relations
    patient = relationship("Patient", back_populates="contact_preference")
    
    @property
    def do_not_disturb_days_list(self):
        """Retourne la liste des jours à éviter"""
        if self.do_not_disturb_days:
            try:
                return json.loads(self.do_not_disturb_days)
            except json.JSONDecodeError:
                return []
        return []
    
    @do_not_disturb_days_list.setter
    def do_not_disturb_days_list(self, days_list):
        """Définit la liste des jours à éviter"""
        self.do_not_disturb_days = json.dumps(days_list)
    
    def is_contact_time_valid(self, check_time=None):
        """Vérifie si l'heure actuelle est dans la plage de contact préférée"""
        if check_time is None:
            check_time = datetime.now().time()
        return self.preferred_time_start <= check_time <= self.preferred_time_end
    
    def get_enabled_channels(self):
        """Retourne la liste des canaux de communication activés"""
        channels = []
        if self.sms_enabled:
            channels.append('sms')
        if self.email_enabled:
            channels.append('email')
        if self.call_enabled:
            channels.append('call')
        if self.whatsapp_enabled:
            channels.append('whatsapp')
        return channels
    
    def __repr__(self):
        return f"<ContactPreference(patient_id={self.patient_id}, language='{self.preferred_language}', channels={self.get_enabled_channels()})>"

# Données prédéfinies pour les types de rappels
PREDEFINED_REMINDER_TYPES = [
    {
        'name': 'appointment',
        'description': 'Rappel de rendez-vous médical',
        'template_fr': 'Bonjour {patient_name}, nous vous rappelons votre rendez-vous le {date} à {time} avec le Dr {doctor_name}. Merci de confirmer votre présence.',
        'template_en': 'Hello {patient_name}, this is a reminder of your appointment on {date} at {time} with Dr {doctor_name}. Please confirm your attendance.',
        'template_es': 'Hola {patient_name}, le recordamos su cita el {date} a las {time} con el Dr {doctor_name}. Por favor confirme su asistencia.'
    },
    {
        'name': 'medication',
        'description': 'Rappel de prise de médicaments',
        'template_fr': 'Bonjour {patient_name}, il est temps de prendre votre médicament: {medication_name}. Dosage: {dosage}. N\'oubliez pas de suivre les instructions de votre médecin.',
        'template_en': 'Hello {patient_name}, it\'s time to take your medication: {medication_name}. Dosage: {dosage}. Don\'t forget to follow your doctor\'s instructions.',
        'template_es': 'Hola {patient_name}, es hora de tomar su medicamento: {medication_name}. Dosis: {dosage}. No olvide seguir las instrucciones de su médico.'
    },
    {
        'name': 'follow_up',
        'description': 'Rappel de suivi médical',
        'template_fr': 'Bonjour {patient_name}, votre suivi médical est prévu le {date}. Veuillez contacter l\'hôpital pour confirmer ou reprogrammer si nécessaire.',
        'template_en': 'Hello {patient_name}, your medical follow-up is scheduled for {date}. Please contact the hospital to confirm or reschedule if necessary.',
        'template_es': 'Hola {patient_name}, su seguimiento médico está programado para el {date}. Por favor contacte al hospital para confirmar o reprogramar si es necesario.'
    }
]