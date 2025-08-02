from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from contextlib import contextmanager
from typing import Generator
import logging
from config.settings import settings
from .models import Base

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gestionnaire de base de données PostgreSQL"""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialise la connexion à la base de données"""
        try:
            # Créer le moteur de base de données
            self.engine = create_engine(
                settings.postgres_url,
                pool_pre_ping=True,
                pool_recycle=300,
                echo=False  # Set to True for SQL debugging
            )
            
            # Créer la session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            logger.info("Database engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def create_tables(self):
        """Crée toutes les tables définies dans les modèles"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("All tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def drop_tables(self):
        """Supprime toutes les tables (ATTENTION: destructif!)"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.warning("All tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Context manager pour les sessions de base de données"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def get_session_sync(self) -> Session:
        """Obtient une session synchrone (à fermer manuellement)"""
        return self.SessionLocal()
    
    def test_connection(self) -> bool:
        """Teste la connexion à la base de données"""
        try:
            with self.get_session() as session:
                session.execute("SELECT 1")
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def get_table_info(self) -> dict:
        """Retourne des informations sur les tables"""
        try:
            metadata = MetaData()
            metadata.reflect(bind=self.engine)
            
            table_info = {}
            for table_name in metadata.tables.keys():
                table = metadata.tables[table_name]
                table_info[table_name] = {
                    'columns': [col.name for col in table.columns],
                    'primary_keys': [col.name for col in table.primary_key.columns],
                    'foreign_keys': [
                        {
                            'column': fk.parent.name,
                            'references': f"{fk.column.table.name}.{fk.column.name}"
                        }
                        for fk in table.foreign_keys
                    ]
                }
            
            return table_info
            
        except Exception as e:
            logger.error(f"Failed to get table info: {e}")
            return {}

# Instance globale du gestionnaire de base de données
db_manager = DatabaseManager()

# Fonctions utilitaires
def get_db_session():
    """Dependency pour FastAPI"""
    session = db_manager.get_session_sync()
    try:
        yield session
    finally:
        session.close()

def init_database():
    """Initialise la base de données avec les tables"""
    logger.info("Initializing database...")
    db_manager.create_tables()
    
    # Insérer des données de base si nécessaire
    _insert_default_specialties()
    
    logger.info("Database initialization completed")

def _insert_default_specialties():
    """Insère les spécialités médicales par défaut"""
    from .models import MedicalSpecialty
    
    default_specialties = [
        {"name": "Cardiologie", "code": "CARDIO", "description": "Spécialité des maladies cardiovasculaires"},
        {"name": "Neurologie", "code": "NEURO", "description": "Spécialité des maladies du système nerveux"},
        {"name": "Pédiatrie", "code": "PEDIATR", "description": "Médecine des enfants"},
        {"name": "Gynécologie", "code": "GYNECO", "description": "Médecine de la femme"},
        {"name": "Chirurgie", "code": "CHIR", "description": "Spécialité chirurgicale"},
        {"name": "Médecine Interne", "code": "MEDINT", "description": "Médecine générale hospitalière"},
        {"name": "Urgences", "code": "URGENCE", "description": "Médecine d'urgence"},
        {"name": "Radiologie", "code": "RADIO", "description": "Imagerie médicale"},
        {"name": "Anesthésie", "code": "ANESTH", "description": "Anesthésie et réanimation"},
        {"name": "Psychiatrie", "code": "PSYCHI", "description": "Santé mentale"}
    ]
    
    try:
        with db_manager.get_session() as session:
            # Vérifier si les spécialités existent déjà
            existing_count = session.query(MedicalSpecialty).count()
            
            if existing_count == 0:
                for specialty_data in default_specialties:
                    specialty = MedicalSpecialty(**specialty_data)
                    session.add(specialty)
                
                logger.info(f"Inserted {len(default_specialties)} default medical specialties")
            else:
                logger.info(f"Medical specialties already exist ({existing_count} found)")
                
    except Exception as e:
        logger.error(f"Failed to insert default specialties: {e}")