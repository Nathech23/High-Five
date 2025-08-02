from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class Department(Base):
    """Department model"""
    __tablename__ = "departments"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    code = Column(String(10), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    patients = relationship("Patient", back_populates="department")
    feedbacks = relationship("Feedback", back_populates="department")

class Patient(Base):
    """Patient model"""
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False, index=True)
    last_name = Column(String(50), nullable=False, index=True)
    phone = Column(String(20), index=True)
    email = Column(String(100), index=True)
    preferred_language = Column(String(10), default="fr", index=True)  # fr, en, douala, bassa, ewondo
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    department = relationship("Department", back_populates="patients")
    feedbacks = relationship("Feedback", back_populates="patient")
    contact_preferences = relationship("ContactPreference", back_populates="patient")

class Feedback(Base):
    """Feedback model"""
    __tablename__ = "feedbacks"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    rating = Column(Float, nullable=False, index=True)  # 1-5 stars
    feedback_text = Column(Text, nullable=False)
    language = Column(String(10), nullable=False, index=True)
    wait_time_min = Column(Float)
    resolution_time_min = Column(Float)
    is_urgent = Column(Boolean, default=False, index=True)
    status = Column(String(20), default="pending", index=True)  # pending, reviewed, resolved
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    patient = relationship("Patient", back_populates="feedbacks")
    department = relationship("Department", back_populates="feedbacks")
    analysis = relationship("FeedbackAnalysis", back_populates="feedback", uselist=False)

class FeedbackAnalysis(Base):
    """Feedback analysis model for NLP results"""
    __tablename__ = "feedback_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    feedback_id = Column(Integer, ForeignKey("feedbacks.id"), unique=True, nullable=False)
    sentiment = Column(String(20), index=True)  # positive, negative, neutral
    sentiment_score = Column(Float)  # -1 to 1
    themes = Column(Text)  # JSON array of detected themes
    keywords = Column(Text)  # JSON array of important keywords
    urgency_score = Column(Float, default=0.0, index=True)  # 0-1
    confidence_score = Column(Float)  # 0-1
    processed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    feedback = relationship("Feedback", back_populates="analysis")

class ContactPreference(Base):
    """Contact preferences for patients"""
    __tablename__ = "contact_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    preferred_method = Column(String(20), default="sms")  # sms, call, email, whatsapp
    preferred_time_start = Column(String(5), default="09:00")  # HH:MM format
    preferred_time_end = Column(String(5), default="17:00")  # HH:MM format
    preferred_language = Column(String(10), default="fr")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    patient = relationship("Patient", back_populates="contact_preferences")

class ReminderType(Base):
    """Reminder types with multilingual templates"""
    __tablename__ = "reminder_types"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True, index=True)
    description = Column(Text)
    template_fr = Column(Text, nullable=False)  # French template
    template_en = Column(Text, nullable=False)  # English template
    template_douala = Column(Text)  # Douala template
    template_bassa = Column(Text)  # Bassa template
    template_ewondo = Column(Text)  # Ewondo template
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    reminders = relationship("Reminder", back_populates="reminder_type")

class Reminder(Base):
    """Reminder scheduling model"""
    __tablename__ = "reminders"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    reminder_type_id = Column(Integer, ForeignKey("reminder_types.id"), nullable=False)
    scheduled_date = Column(DateTime(timezone=True), nullable=False, index=True)
    message_content = Column(Text, nullable=False)
    delivery_method = Column(String(20), nullable=False)  # sms, call, email, whatsapp
    status = Column(String(20), default="scheduled", index=True)  # scheduled, sent, failed, cancelled
    sent_at = Column(DateTime(timezone=True))
    delivery_status = Column(String(20))  # delivered, failed, pending
    error_message = Column(Text)
    cost = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    patient = relationship("Patient")
    reminder_type = relationship("ReminderType", back_populates="reminders")