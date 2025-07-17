import os
import sys
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, List, Tuple

# Charger les variables d'environnement
load_dotenv()

# Imports des services
try:
    from communication_service import CommunicationManager, TwilioService, TemplateService
    from twiml_service import TwiMLService, WebhookService
    from templates_manager import TemplateManager, MessagePersonalizer, PatientData, MessageType, Language
    from database import DatabaseManager
    from models import Patient, Reminder, ReminderType
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
    print("Assurez-vous que tous les modules sont présents")
    sys.exit(1)

class TestResults:
    """Classe pour gérer les résultats de tests"""
    
    def __init__(self):
        self.tests = []
        self.start_time = datetime.now()
    
    def add_test(self, name: str, success: bool, details: str = ""):
        """Ajouter un résultat de test"""
        self.tests.append({
            'name': name,
            'success': success,
            'details': details,
            'timestamp': datetime.now()
        })
    
    def get_summary(self) -> Dict:
        """Obtenir le résumé des tests"""
        total = len(self.tests)
        passed = sum(1 for test in self.tests if test['success'])
        failed = total - passed
        success_rate = (passed / total * 100) if total > 0 else 0
        
        return {
            'total': total,
            'passed': passed,
            'failed': failed,
            'success_rate': success_rate,
            'duration': (datetime.now() - self.start_time).total_seconds()
        }
    
    def print_report(self):
        """Afficher le rapport complet"""
        summary = self.get_summary()
        
        print("\n" + "="*60)
        print("📊 RAPPORT FINAL - TESTS SYSTÈME COMPLET")
        print("="*60)
        
        print(f"\n📈 RÉSULTATS GLOBAUX")
        print(f"   Tests réussis: {summary['passed']}/{summary['total']}")
        print(f"   Taux de réussite: {summary['success_rate']:.1f}%")
        print(f"   Durée: {summary['duration']:.1f}s")
        
        print(f"\n📋 DÉTAIL DES TESTS")
        for test in self.tests:
            status = "✅ RÉUSSI" if test['success'] else "❌ ÉCHOUÉ"
            print(f"   {test['name']}: {status}")
            if test['details'] and not test['success']:
                print(f"      → {test['details']}")
        
        if summary['success_rate'] == 100:
            print("\n🎉 FÉLICITATIONS !")
            print("   Tous les tests sont réussis")
            print("   Le système est prêt pour la production")
        else:
            print("\n⚠️  ATTENTION")
            print("   Certains tests ont échoué")
            print("   Vérifiez la configuration avant la production")
        
        print("\n🔗 RESSOURCES UTILES:")
        print("   - Console Twilio: https://console.twilio.com")
        print("   - Logs Twilio: https://console.twilio.com/us1/monitor/logs")
        print("   - Documentation: ./DOCUMENTATION_COMPLETE.md")

def print_header():
    """Afficher l'en-tête des tests"""
    print("\n" + "="*60)
    print("🏥 TESTS COMPLETS - HÔPITAL GÉNÉRAL DOUALA")
    print("="*60)
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🔍 Validation complète du système de rappels médicaux")
    print("="*60)

def test_configuration(results: TestResults):
    """Test de la configuration système"""
    print("\n🔧 TEST CONFIGURATION")
    print("-" * 30)
    
    required_vars = [
        'TWILIO_ACCOUNT_SID',
        'TWILIO_AUTH_TOKEN', 
        'TWILIO_PHONE_NUMBER',
        'BASE_URL',
        'TEST_PHONE_NUMBER'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            print(f"✅ {var}: {'*' * (len(value) - 4) + value[-4:]}")
    
    if missing_vars:
        error_msg = f"Variables manquantes: {', '.join(missing_vars)}"
        print(f"❌ {error_msg}")
        results.add_test("Configuration", False, error_msg)
    else:
        print("✅ Configuration complète")
        results.add_test("Configuration", True)

def test_twilio_connection(results: TestResults):
    """Test de la connexion Twilio"""
    print("\n📞 TEST CONNEXION TWILIO")
    print("-" * 30)
    
    try:
        twilio_service = TwilioService()
        account = twilio_service.client.api.accounts(twilio_service.account_sid).fetch()
        
        print(f"✅ Connexion réussie")
        print(f"   Compte: {account.friendly_name}")
        print(f"   Statut: {account.status}")
        print(f"   SID: {account.sid[:8]}...")
        
        results.add_test("Connexion Twilio", True)
        
    except Exception as e:
        error_msg = f"Erreur connexion: {str(e)}"
        print(f"❌ {error_msg}")
        results.add_test("Connexion Twilio", False, error_msg)

def test_template_service(results: TestResults):
    """Test du service de templates Phase 3"""
    print("\n🎨 TEST SERVICE TEMPLATES")
    print("-" * 30)
    
    try:
        template_service = TemplateService()
        
        # Test création patient de test
        test_patient = PatientData(
            name="Test Patient",
            phone="+237675934861",
            preferred_language="fr",
            doctor_name="Dr. Test",
            department="Médecine Générale"
        )
        
        # Test génération message avec template
        message = template_service.create_personalized_message(
            test_patient, MessageType.APPOINTMENT_REMINDER
        )
        
        print(f"✅ Message généré: '{str(message)[:50]}...'")
        
        # Test validation templates
        validation = template_service.validate_templates()
        print(f"✅ Validation templates: {validation['status']}")
        
        results.add_test("Service Templates", True)
        
    except Exception as e:
        error_msg = f"Erreur templates: {str(e)}"
        print(f"❌ {error_msg}")
        results.add_test("Service Templates", False, error_msg)

def test_twiml_service(results: TestResults):
    """Test du service TwiML"""
    print("\n📻 TEST SERVICE TWIML")
    print("-" * 30)
    
    try:
        # Test génération TwiML
        twiml_response = TwiMLService.generate_voice_message(
            "Bonjour, test de message vocal", 
            "fr"
        )
        
        if "<Say" in twiml_response and "voice=\"alice\"" in twiml_response:
            print("✅ TwiML généré correctement")
            print(f"   Contenu: {twiml_response[:100]}...")
            results.add_test("Service TwiML", True)
        else:
            raise ValueError("Format TwiML invalide")
            
    except Exception as e:
        error_msg = f"Erreur TwiML: {str(e)}"
        print(f"❌ {error_msg}")
        results.add_test("Service TwiML", False, error_msg)

def test_sms_real(results: TestResults):
    """Test d'envoi SMS réel"""
    print("\n📱 TEST SMS RÉEL")
    print("-" * 30)
    
    test_phone = os.getenv('TEST_PHONE_NUMBER')
    if not test_phone:
        print("❌ TEST_PHONE_NUMBER non configuré")
        results.add_test("SMS Réel", False, "Numéro de test manquant")
        return
    
    try:
        comm_manager = CommunicationManager()
        
        # Envoyer SMS de test
        test_message = f"Test SMS - {datetime.now().strftime('%H:%M:%S')}"
        result = comm_manager.send_reminder_sms(test_phone, test_message, 'fr')
        
        if result.get('success'):
            print(f"✅ SMS envoyé avec succès")
            print(f"   SID: {result.get('message_sid')}")
            print(f"   Destinataire: {test_phone}")
            results.add_test("SMS Réel", True)
        else:
            error_msg = result.get('error', 'Erreur inconnue')
            print(f"❌ Échec SMS: {error_msg}")
            results.add_test("SMS Réel", False, error_msg)
            
    except Exception as e:
        error_msg = f"Exception SMS: {str(e)}"
        print(f"❌ {error_msg}")
        results.add_test("SMS Réel", False, error_msg)

def test_voice_call(results: TestResults):
    """Test d'appel vocal réel"""
    print("\n📞 TEST APPEL VOCAL")
    print("-" * 30)
    
    test_phone = os.getenv('TEST_PHONE_NUMBER')
    if not test_phone:
        print("❌ TEST_PHONE_NUMBER non configuré")
        results.add_test("Appel Vocal", False, "Numéro de test manquant")
        return
    
    try:
        comm_manager = CommunicationManager()
        
        # Lancer appel de test
        test_message = "Test d'appel vocal automatisé"
        result = comm_manager.send_reminder_call(test_phone, test_message, 'fr')
        
        if result.get('success'):
            print(f"✅ Appel initié avec succès")
            print(f"   SID: {result.get('call_sid')}")
            print(f"   Status: {result.get('status')}")
            results.add_test("Appel Vocal", True)
        else:
            error_msg = result.get('error', 'Erreur inconnue')
            print(f"❌ Échec appel: {error_msg}")
            results.add_test("Appel Vocal", False, error_msg)
            
    except Exception as e:
        error_msg = f"Exception appel: {str(e)}"
        print(f"❌ {error_msg}")
        results.add_test("Appel Vocal", False, error_msg)

def test_flask_endpoints(results: TestResults):
    """Test des endpoints Flask"""
    print("\n🌐 TEST ENDPOINTS FLASK")
    print("-" * 30)
    
    base_url = "http://localhost:5000"
    
    endpoints = [
        ("/", "Health check", "GET"),
        ("/test/twiml", "Test TwiML", "GET"),
        ("/test/communication", "Test Communication", "POST")
    ]
    
    success_count = 0
    
    for endpoint, description, method in endpoints:
        try:
            if method == "POST":
                test_data = {
                    "phone": os.getenv('TEST_PHONE_NUMBER', '+237675934861'),
                    "language": "fr",
                    "message": "Test de communication"
                }
                response = requests.post(f"{base_url}{endpoint}", json=test_data, timeout=5)
            else:
                response = requests.get(f"{base_url}{endpoint}", timeout=5)
                
            if response.status_code == 200:
                print(f"✅ {endpoint} - {description}")
                success_count += 1
            else:
                print(f"❌ {endpoint} - Status: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ {endpoint} - Erreur: {str(e)}")
    
    if success_count == len(endpoints):
        results.add_test("Endpoints Flask", True)
    else:
        results.add_test("Endpoints Flask", False, f"{success_count}/{len(endpoints)} endpoints fonctionnels")

def test_webhooks_simulation(results: TestResults):
    """Test de simulation des webhooks"""
    print("\n🔗 TEST SIMULATION WEBHOOK")
    print("-" * 30)
    
    try:
        webhook_service = WebhookService()
        
        # Simuler webhook SMS
        sms_data = {
            'MessageSid': 'SM123456789',
            'MessageStatus': 'delivered',
            'From': '+19033647327',
            'To': '+237675934861'
        }
        
        sms_result = webhook_service.handle_sms_status(sms_data)
        if sms_result:
            print("✅ Webhook SMS simulé avec succès")
        else:
            print("❌ Échec simulation webhook SMS")
        
        # Simuler webhook Voice
        voice_data = {
            'CallSid': 'CA123456789',
            'CallStatus': 'completed',
            'From': '+19033647327',
            'To': '+237675934861'
        }
        
        voice_result = webhook_service.handle_call_status(voice_data)
        if voice_result:
            print("✅ Webhook Voice simulé avec succès")
        else:
            print("❌ Échec simulation webhook Voice")
        
        if sms_result and voice_result:
            results.add_test("Webhooks", True)
        else:
            results.add_test("Webhooks", False, "Simulation partielle")
            
    except Exception as e:
        error_msg = f"Erreur webhooks: {str(e)}"
        print(f"❌ {error_msg}")
        results.add_test("Webhooks", False, error_msg)

def test_database_operations(results: TestResults):
    """Test des opérations de base de données"""
    print("\n🗄️ TEST BASE DE DONNÉES")
    print("-" * 30)
    
    try:
        db_manager = DatabaseManager()
        session = db_manager.get_session()
        
        # Test création patient avec les bons attributs
        patient_data = {
            'first_name': 'Test',
            'last_name': 'Patient',
            'phone_number': '+237675934861',
            'email': 'test@example.com'
        }
        
        # Vérification que la classe Patient existe
        test_patient = Patient(**patient_data)
        
        # Ajouter le patient à la session
        session.add(test_patient)
        session.commit()
        patient_id = test_patient.id
        
        if patient_id:
            print(f"✅ Patient créé: ID {patient_id}")
            
            # Test récupération patient
            retrieved_patient = session.query(Patient).filter(Patient.id == patient_id).first()
            if retrieved_patient:
                print(f"✅ Patient récupéré: {retrieved_patient.first_name} {retrieved_patient.last_name}")
                
                # Nettoyer
                session.delete(retrieved_patient)
                session.commit()
                print("✅ Patient supprimé")
                
                results.add_test("Base de Données", True)
            else:
                results.add_test("Base de Données", False, "Échec récupération patient")
        else:
            results.add_test("Base de Données", False, "Échec création patient")
        
        session.close()
            
    except Exception as e:
        error_msg = f"Erreur DB: {str(e)}"
        print(f"❌ {error_msg}")
        results.add_test("Base de Données", False, error_msg)

def run_performance_tests(results: TestResults):
    """Tests de performance"""
    print("\n⚡ TEST PERFORMANCE")
    print("-" * 30)
    
    try:
        # Test temps de réponse API
        start_time = time.time()
        response = requests.get("http://localhost:5000/", timeout=5)
        response_time = (time.time() - start_time) * 1000
        
        print(f"✅ Temps réponse API: {response_time:.2f}ms")
        
        if response_time < 200:
            print("✅ Performance excellente (< 200ms)")
            results.add_test("Performance", True)
        elif response_time < 500:
            print("⚠️ Performance acceptable (< 500ms)")
            results.add_test("Performance", True, f"Temps réponse: {response_time:.2f}ms")
        else:
            print(f"❌ Performance dégradée ({response_time:.2f}ms)")
            results.add_test("Performance", False, f"Temps réponse trop élevé: {response_time:.2f}ms")
            
    except Exception as e:
        error_msg = f"Erreur performance: {str(e)}"
        print(f"❌ {error_msg}")
        results.add_test("Performance", False, error_msg)

def main():
    """Fonction principale des tests"""
    print_header()
    
    results = TestResults()
    
    # Exécuter tous les tests
    test_configuration(results)
    test_twilio_connection(results)
    test_template_service(results)
    test_twiml_service(results)
    test_sms_real(results)
    test_voice_call(results)
    test_flask_endpoints(results)
    test_webhooks_simulation(results)
    
    # Tests optionnels (si modules disponibles)
    try:
        test_database_operations(results)
        run_performance_tests(results)
    except Exception as e:
        print(f"\n⚠️ Tests optionnels ignorés: {e}")
    
    # Afficher le rapport final
    results.print_report()
    
    # Code de sortie
    summary = results.get_summary()
    if summary['success_rate'] == 100:
        print("\n🎯 Tous les tests sont réussis ! Système prêt pour la production.")
        return 0
    else:
        print(f"\n⚠️ {summary['failed']} test(s) échoué(s). Vérifiez la configuration.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️ Tests interrompus par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Erreur fatale: {e}")
        sys.exit(1)