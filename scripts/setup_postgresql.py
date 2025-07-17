"""
Script d'installation PostgreSQL
"""

import sys
import logging
from src.database import DatabaseManager
from src.config import DatabaseConfig, create_env_file
from sqlalchemy.exc import OperationalError, ProgrammingError
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_postgresql_connection():
    """Vérifie la connexion PostgreSQL"""
    print("Vérification connexion...")
    
    try:
        conn = psycopg2.connect(
            host=DatabaseConfig.DEFAULT_HOST,
            port=DatabaseConfig.DEFAULT_PORT,
            user=DatabaseConfig.DEFAULT_USER,
            password=DatabaseConfig.DEFAULT_PASSWORD,
            database='postgres'
        )
        conn.close()
        print("   Connexion OK")
        return True
    except psycopg2.OperationalError as e:
        print(f"   Erreur: {e}")
        return False

def create_database():
    """Crée la base de données"""
    print("Création base de données...")
    
    try:
        conn = psycopg2.connect(
            host=DatabaseConfig.DEFAULT_HOST,
            port=DatabaseConfig.DEFAULT_PORT,
            user=DatabaseConfig.DEFAULT_USER,
            password=DatabaseConfig.DEFAULT_PASSWORD,
            database='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (DatabaseConfig.DEFAULT_DATABASE,)
        )
        
        if cursor.fetchone():
            print(f"   Base '{DatabaseConfig.DEFAULT_DATABASE}' existe")
        else:
            cursor.execute(f"CREATE DATABASE {DatabaseConfig.DEFAULT_DATABASE}")
            print(f"   Base '{DatabaseConfig.DEFAULT_DATABASE}' créée")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.Error as e:
        print(f"   Erreur: {e}")
        return False

def setup_database_schema():
    """Configure le schéma"""
    print("Configuration schéma...")
    
    try:
        db_manager = DatabaseManager()
        
        print("   Création tables...")
        db_manager.create_tables()
        
        print("   Données prédéfinies...")
        db_manager.init_predefined_data()
        
        print("   Schéma OK")
        return True
        
    except Exception as e:
        print(f"   Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_configuration_files():
    """Génère fichiers config"""
    print("Génération config...")
    
    config_sql = f"""-- Requêtes de vérification:
\\dt
\\d reminder_types
\\d patients  
\\d reminders
\\d contact_preferences

SELECT COUNT(*) FROM reminder_types;
SELECT COUNT(*) FROM patients;
SELECT COUNT(*) FROM reminders;
SELECT COUNT(*) FROM contact_preferences;

SELECT id, name, description FROM reminder_types;

\\q
"""
    
    try:
        with open("postgresql_config.sql", "w", encoding="utf-8") as f:
            f.write(config_sql)
        print("   postgresql_config.sql créé")
    except Exception as e:
        print(f"   Erreur: {e}")

def verify_installation():
    """Vérifie l'installation"""
    print("Vérification...")
    
    try:
        db_manager = DatabaseManager()
        session = db_manager.get_session()
        
        from models import ReminderType
        reminder_types = session.query(ReminderType).all()
        print(f"   {len(reminder_types)} types de rappels")
        
        for rt in reminder_types:
            print(f"      - {rt.name}: {rt.description}")
        
        session.close()
        print("   Installation OK")
        return True
        
    except Exception as e:
        print(f"   Erreur: {e}")
        return False

def main():
    """Installation PostgreSQL"""
    print("Installation PostgreSQL")
    print("=" * 40)
    print(f"Serveur: {DatabaseConfig.DEFAULT_HOST}:{DatabaseConfig.DEFAULT_PORT}")
    print(f"Base: {DatabaseConfig.DEFAULT_DATABASE}")
    print("=" * 40)
    
    success = True
    
    if not check_postgresql_connection():
        success = False
    
    if success and not create_database():
        success = False
    
    if success and not setup_database_schema():
        success = False
    
    if success:
        create_configuration_files()
    
    if success and not verify_installation():
        success = False
    
    print("=" * 40)
    if success:
        print("Installation terminée!")
        print("\nTests: python test_models.py")
    else:
        print("Installation échouée")
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Installation interrompue par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Erreur inattendue: {e}")
        sys.exit(1)