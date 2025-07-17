# Configuration du système de rappels
# Paramètres de base de données et environnement

import os
from typing import Optional

class DatabaseConfig:
    """Configuration PostgreSQL"""
    
    # Paramètres PostgreSQL par défaut
    DEFAULT_HOST = "192.168.1.101"
    DEFAULT_PORT = "5432"
    DEFAULT_USER = "postgres"
    DEFAULT_PASSWORD = "12345"
    DEFAULT_DATABASE = "hospital_reminders"
    
    @classmethod
    def get_database_url(cls, 
                        host: Optional[str] = None,
                        port: Optional[str] = None,
                        user: Optional[str] = None,
                        password: Optional[str] = None,
                        database: Optional[str] = None) -> str:
        """Génère l'URL de connexion PostgreSQL"""
        # Utiliser les variables d'environnement si disponibles, sinon les valeurs par défaut
        host = host or os.getenv('DB_HOST', cls.DEFAULT_HOST)
        port = port or os.getenv('DB_PORT', cls.DEFAULT_PORT)
        user = user or os.getenv('DB_USER', cls.DEFAULT_USER)
        password = password or os.getenv('DB_PASSWORD', cls.DEFAULT_PASSWORD)
        database = database or os.getenv('DB_NAME', cls.DEFAULT_DATABASE)
        
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    @classmethod
    def get_test_database_url(cls) -> str:
        """Retourne l'URL pour la base de données de test (en mémoire)"""
        return "sqlite:///:memory:"

class AppConfig:
    """Configuration application"""
    
    SUPPORTED_LANGUAGES = ['fr', 'en', 'es']
    DEFAULT_LANGUAGE = 'fr'
    DEFAULT_TIMEZONE = 'Africa/Douala'
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_PRIORITY_LEVEL = 1
    DEFAULT_CONTACT_START_TIME = "08:00:00"
    DEFAULT_CONTACT_END_TIME = "18:00:00"
    REMINDER_STATUSES = ['pending', 'sent', 'delivered', 'failed', 'cancelled']
    PRIORITY_LEVELS = {
        1: 'Faible',
        2: 'Normal', 
        3: 'Élevé',
        4: 'Urgent',
        5: 'Critique'
    }
    COMMUNICATION_CHANNELS = ['sms', 'email', 'call', 'whatsapp']

ENVIRONMENT_VARIABLES = {
    'DB_HOST': 'Adresse IP du serveur PostgreSQL',
    'DB_PORT': 'Port de connexion PostgreSQL',
    'DB_USER': 'Nom d\'utilisateur PostgreSQL',
    'DB_PASSWORD': 'Mot de passe PostgreSQL',
    'DB_NAME': 'Nom de la base de données',
    'APP_ENV': 'Environnement (development, production, test)',
    'LOG_LEVEL': 'Niveau de logging (DEBUG, INFO, WARNING, ERROR)'
}

def create_env_file():
    """Génère .env.example"""
    env_content = "# Configuration d'environnement\n"
    env_content += "# Copiez vers .env\n\n"
    env_content += "# Base de données\n"
    env_content += f"DB_HOST={DatabaseConfig.DEFAULT_HOST}\n"
    env_content += f"DB_PORT={DatabaseConfig.DEFAULT_PORT}\n"
    env_content += f"DB_USER={DatabaseConfig.DEFAULT_USER}\n"
    env_content += f"DB_PASSWORD={DatabaseConfig.DEFAULT_PASSWORD}\n"
    env_content += f"DB_NAME={DatabaseConfig.DEFAULT_DATABASE}\n\n"
    
    env_content += "# App\n"
    env_content += "APP_ENV=development\n"
    env_content += "LOG_LEVEL=INFO\n"
    
    return env_content

if __name__ == "__main__":
    # Créer le fichier .env.example
    env_content = create_env_file()
    with open('.env.example', 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("Configuration du système de rappels")
    print("=" * 40)
    print(f"URL de base de données: {DatabaseConfig.get_database_url()}")
    print(f"Langues supportées: {AppConfig.SUPPORTED_LANGUAGES}")
    print(f"Timezone par défaut: {AppConfig.DEFAULT_TIMEZONE}")
    print("\nFichier .env.example créé pour la configuration d'environnement")
    print("Copiez-le vers .env et modifiez les valeurs selon vos besoins.")