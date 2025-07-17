"""Script de vérification des imports après réorganisation"""

import sys
from pathlib import Path

# Ajouter le répertoire racine au path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Teste tous les imports principaux du projet"""
    print("🔍 Vérification des imports après réorganisation...\n")
    
    tests = [
        # Modèles
        ("src.models.models", "Base, Patient, Reminder"),
        ("src.models.reminder_models", "ReminderCreate, ReminderStatus"),
        
        # Services
        ("src.services.scheduler", "ReminderScheduler"),
        ("src.services.communication_service", "CommunicationManager"),
        ("src.services.reminder_service", "ReminderService"),
        ("src.services.redis_service", "RedisService"),
        ("src.services.templates_manager", "TemplateManager"),
        ("src.services.twiml_service", "TwiMLService"),
        
        # Configuration
        ("src.config.config", "AppConfig"),
        ("src.config.config_api", "SchedulerConfig"),
        
        # Base de données
        ("src.database.database", "DatabaseManager"),
        
        # API
        ("src.api.reminder_api", "app"),
    ]
    
    success_count = 0
    total_count = len(tests)
    
    for module_name, imports in tests:
        try:
            exec(f"from {module_name} import {imports}")
            print(f"✅ {module_name} - {imports}")
            success_count += 1
        except ImportError as e:
            print(f"❌ {module_name} - {imports}")
            print(f"   Erreur: {e}")
        except Exception as e:
            print(f"⚠️  {module_name} - {imports}")
            print(f"   Erreur: {e}")
    
    print(f"\n📊 Résultats: {success_count}/{total_count} imports réussis")
    
    if success_count == total_count:
        print("🎉 Tous les imports fonctionnent correctement !")
        return True
    else:
        print("⚠️  Certains imports ont échoué")
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)