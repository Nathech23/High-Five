"""
Gestion de la base de données PostgreSQL
"""

from sqlalchemy import create_engine, Index
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError, OperationalError
from src.models.models import Base, ReminderType, Patient, Reminder, ContactPreference, PREDEFINED_REMINDER_TYPES
from src.config.config import DatabaseConfig, AppConfig
import os
from typing import Optional
import logging
import time

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gestionnaire de base de données pour le système de rappels"""
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialise le gestionnaire de base de données
        
        Args:
            database_url: URL de connexion à la base de données
                         Par défaut utilise PostgreSQL avec la configuration
        """
        if database_url is None:
            database_url = DatabaseConfig.get_database_url()
        
        self.database_url = database_url
        
        # Configuration optimisée pour PostgreSQL
        self.engine = create_engine(
            database_url,
            echo=False,  # Désactive les logs SQL
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            pool_recycle=3600,  # Recycler les connexions après 1h
            connect_args={
                "connect_timeout": 10,
                "application_name": "hospital_reminders"
            }
        )
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
    
    def create_tables(self):
        """Crée toutes les tables dans la base de données"""
        try:
            # Vérifier la connexion avant de créer les tables
            self._test_connection()
            
            Base.metadata.create_all(bind=self.engine)
            self._create_indexes()
            logger.info("Tables créées")
        except OperationalError as e:
            logger.error(f"Erreur de connexion à PostgreSQL: {e}")
            logger.error("Vérifiez que PostgreSQL est démarré et accessible")
            raise
        except Exception as e:
            logger.error(f"Erreur lors de la création des tables: {e}")
            raise
    
    def _create_indexes(self):
        """Crée les index pour optimiser les requêtes de planification"""
        try:
            # Index pour les rappels
            Index('idx_reminders_scheduled_date', Reminder.scheduled_date).create(self.engine, checkfirst=True)
            Index('idx_reminders_status', Reminder.status).create(self.engine, checkfirst=True)
            Index('idx_reminders_patient_id', Reminder.patient_id).create(self.engine, checkfirst=True)
            Index('idx_reminders_type_id', Reminder.reminder_type_id).create(self.engine, checkfirst=True)
            Index('idx_reminders_scheduled_datetime', Reminder.scheduled_date, Reminder.scheduled_time).create(self.engine, checkfirst=True)
            Index('idx_reminders_priority_status', Reminder.priority_level, Reminder.status).create(self.engine, checkfirst=True)
            Index('idx_reminders_planning', Reminder.scheduled_date, Reminder.scheduled_time, Reminder.status, Reminder.priority_level).create(self.engine, checkfirst=True)
            
            # Index pour les patients
            Index('idx_patients_phone', Patient.phone_number).create(self.engine, checkfirst=True)
            Index('idx_patients_email', Patient.email).create(self.engine, checkfirst=True)
            
            # Index pour les préférences de contact
            Index('idx_contact_preferences_patient', ContactPreference.patient_id).create(self.engine, checkfirst=True)
            
            logger.info("Index créés")
        except Exception as e:
            logger.warning(f"Certains index n'ont pas pu être créés: {e}")
    
    def get_session(self) -> Session:
        """Retourne une nouvelle session de base de données"""
        return self.SessionLocal()
    
    def init_predefined_data(self):
        """Initialise les données prédéfinies (types de rappels)"""
        session = self.get_session()
        try:
            # Vérifier si les types de rappels existent déjà
            existing_types = session.query(ReminderType).count()
            if existing_types > 0:
                logger.info("Les types de rappels prédéfinis existent déjà")
                return
            
            # Insérer les types de rappels prédéfinis
            for reminder_type_data in PREDEFINED_REMINDER_TYPES:
                reminder_type = ReminderType(**reminder_type_data)
                session.add(reminder_type)
            
            session.commit()
            logger.info(f"Données initialisées: {len(PREDEFINED_REMINDER_TYPES)} types")
            
        except IntegrityError as e:
            session.rollback()
            logger.warning(f"Les types de rappels existent déjà: {e}")
        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de l'insertion des données prédéfinies: {e}")
            raise
        finally:
            session.close()
    
    def reset_database(self):
        """Supprime et recrée toutes les tables (ATTENTION: perte de données)"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.info("Tables supprimées")
            self.create_tables()
            self.init_predefined_data()
            logger.info("Base de données réinitialisée avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de la réinitialisation: {e}")
            raise

    def _test_connection(self):
        """Teste la connexion à la base de données"""
        try:
            with self.engine.connect() as conn:
                from sqlalchemy import text
                conn.execute(text("SELECT 1"))
            logger.info("Connexion PostgreSQL établie")
        except OperationalError as e:
            logger.error(f"Impossible de se connecter à PostgreSQL: {e}")
            logger.error(f"URL de connexion: {self.database_url.replace(self.database_url.split('@')[0].split('//')[1], '***')}")
            raise
    
    def create_database_if_not_exists(self):
        """Crée la base de données si elle n'existe pas"""
        try:
            # Extraire les paramètres de connexion
            import re
            match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):([^/]+)/(.+)', self.database_url)
            if not match:
                raise ValueError("Format d'URL de base de données invalide")
            
            user, password, host, port, db_name = match.groups()
            
            # Se connecter à la base postgres par défaut
            admin_url = f"postgresql://{user}:{password}@{host}:{port}/postgres"
            admin_engine = create_engine(admin_url)
            
            # Vérifier si la base de données existe
            with admin_engine.connect() as conn:
                from sqlalchemy import text
                conn.commit()  # Sortir de la transaction
                result = conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                    {"db_name": db_name}
                )
                
                if not result.fetchone():
                    # Créer la base de données
                    conn.execute(text(f"CREATE DATABASE {db_name}"))
                    logger.info(f"Base de données '{db_name}' créée avec succès")
                else:
                    logger.info(f"Base de données '{db_name}' existe déjà")
            
            admin_engine.dispose()
            
        except Exception as e:
            logger.warning(f"Impossible de créer la base de données automatiquement: {e}")
            logger.info("Assurez-vous que la base de données existe manuellement")

# Instance globale du gestionnaire de base de données
db_manager = DatabaseManager()

def get_db_session() -> Session:
    """Fonction utilitaire pour obtenir une session de base de données"""
    return db_manager.get_session()

def init_database():
    """Initialise la base de données avec les tables et données prédéfinies"""
    logger.info("Initialisation de la base de données...")
    db_manager.create_tables()
    db_manager.init_predefined_data()
    logger.info("Base de données initialisée avec succès")

    def close(self):
        """Fermer la connexion à la base de données"""
        if hasattr(self, 'engine') and self.engine:
            self.engine.dispose()
            print("Connexion fermée")
    
    # MÉTHODES POUR LA GESTION DES RAPPELS (Phase 4)

    def create_reminder(self, reminder_data) -> int:
        """Créer un nouveau rappel et retourner son ID"""
        session = self.get_session()
        try:
            reminder = Reminder(
                patient_id=reminder_data.patient_id,
                reminder_type_id=reminder_data.reminder_type_id,
                scheduled_date=reminder_data.scheduled_date,
                scheduled_time=reminder_data.scheduled_time,
                status=reminder_data.status,
                priority_level=reminder_data.priority_level,
                delivery_method=reminder_data.delivery_method,
                custom_message=reminder_data.custom_message,
                metadata=reminder_data.metadata,
                max_retries=reminder_data.max_retries,
                retry_interval_minutes=reminder_data.retry_interval_minutes
            )
            session.add(reminder)
            session.commit()
            return reminder.id
        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de la création du rappel: {e}")
            raise
        finally:
            session.close()
    
    def get_reminder_by_id(self, reminder_id: int):
        """Récupérer un rappel par son ID"""
        session = self.get_session()
        try:
            reminder = session.query(Reminder).filter(Reminder.id == reminder_id).first()
            return reminder
        finally:
            session.close()
    
    def update_reminder(self, reminder_data):
        """Mettre à jour un rappel"""
        session = self.get_session()
        try:
            reminder = session.query(Reminder).filter(Reminder.id == reminder_data.id).first()
            if reminder:
                reminder.status = reminder_data.status
                reminder.priority_level = reminder_data.priority_level
                reminder.scheduled_date = reminder_data.scheduled_date
                reminder.scheduled_time = reminder_data.scheduled_time
                reminder.custom_message = reminder_data.custom_message
                reminder.metadata = reminder_data.metadata
                reminder.retry_count = reminder_data.retry_count
                reminder.max_retries = reminder_data.max_retries
                reminder.retry_interval_minutes = reminder_data.retry_interval_minutes
                reminder.sent_at = reminder_data.sent_at
                reminder.delivered_at = reminder_data.delivered_at
                reminder.twilio_sid = reminder_data.twilio_sid
                reminder.error_message = reminder_data.error_message
                session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors de la mise à jour du rappel: {e}")
            raise
        finally:
            session.close()
    
    def list_reminders(self, patient_id=None, status=None, limit=100, offset=0):
        """Lister les rappels avec filtres"""
        session = self.get_session()
        try:
            query = session.query(Reminder)
            
            if patient_id:
                query = query.filter(Reminder.patient_id == patient_id)
            
            if status:
                query = query.filter(Reminder.status == status)
            
            reminders = query.order_by(Reminder.created_at.desc()).limit(limit).offset(offset).all()
            return reminders
        finally:
            session.close()
    
    def get_reminder_by_twilio_sid(self, twilio_sid: str):
        """Récupérer un rappel par son SID Twilio"""
        session = self.get_session()
        try:
            reminder = session.query(Reminder).filter(Reminder.twilio_sid == twilio_sid).first()
            return reminder
        finally:
            session.close()
    
    def get_due_reminders(self):
        """Récupérer les rappels dus pour traitement"""
        session = self.get_session()
        try:
            from datetime import datetime
            now = datetime.now()
            
            reminders = session.query(Reminder).filter(
                Reminder.status.in_(['scheduled', 'retry']),
                Reminder.scheduled_date <= now.date(),
                Reminder.scheduled_time <= now.time(),
                Reminder.retry_count < Reminder.max_retries
            ).order_by(
                Reminder.priority_level.desc(),
                Reminder.scheduled_date,
                Reminder.scheduled_time
            ).limit(100).all()
            
            return reminders
        finally:
            session.close()
    
    def get_reminder_stats(self):
        """Récupérer les statistiques des rappels"""
        session = self.get_session()
        try:
            from sqlalchemy import func
            
            stats = session.query(
                func.count(Reminder.id).label('total'),
                func.sum(func.case([(Reminder.status == 'pending', 1)], else_=0)).label('pending'),
                func.sum(func.case([(Reminder.status == 'scheduled', 1)], else_=0)).label('scheduled'),
                func.sum(func.case([(Reminder.status == 'sent', 1)], else_=0)).label('sent'),
                func.sum(func.case([(Reminder.status == 'delivered', 1)], else_=0)).label('delivered'),
                func.sum(func.case([(Reminder.status == 'failed', 1)], else_=0)).label('failed'),
                func.sum(func.case([(Reminder.status == 'cancelled', 1)], else_=0)).label('cancelled'),
                func.sum(func.case([(Reminder.status == 'retry', 1)], else_=0)).label('retry')
            ).first()
            
            return {
                'total': stats.total or 0,
                'pending': stats.pending or 0,
                'scheduled': stats.scheduled or 0,
                'sent': stats.sent or 0,
                'delivered': stats.delivered or 0,
                'failed': stats.failed or 0,
                'cancelled': stats.cancelled or 0,
                'retry': stats.retry or 0,
                'delivery_rate': (stats.delivered / stats.total * 100) if stats.total > 0 else 0
            }
        finally:
            session.close()
    
    def cleanup_old_reminders(self, days_to_keep: int = 90) -> int:
        """Nettoyer les anciens rappels"""
        session = self.get_session()
        try:
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            deleted_count = session.query(Reminder).filter(
                Reminder.created_at < cutoff_date,
                Reminder.status.in_(['delivered', 'failed', 'cancelled'])
            ).delete()
            
            session.commit()
            return deleted_count
        except Exception as e:
            session.rollback()
            logger.error(f"Erreur lors du nettoyage: {e}")
            raise
        finally:
            session.close()

if __name__ == "__main__":
    # Script d'initialisation de la base de données
    print("=== Initialisation de la base de données ===")
    print("Système de rappels - Hôpital Général de Douala")
    print("Phase 1: Modèles données rappels")
    print()
    
    try:
        init_database()
        print("✅ Base de données initialisée avec succès!")
        print()
        print("Tables créées:")
        print("- reminder_types (types de rappels avec templates multilingues)")
        print("- reminders (rappels avec 12 champs pour planification)")
        print("- contact_preferences (préférences de contact des patients)")
        print("- patients (informations des patients)")
        print()
        print("Index créés pour optimiser les requêtes de planification")
        print("3 types de rappels prédéfinis insérés (RDV, médicaments, suivi)")
        print()
        print("La base de données est prête à être utilisée!")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation: {e}")
        exit(1)