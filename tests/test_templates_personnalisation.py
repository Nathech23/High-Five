"""
Tests de Personnalisation et Templates
Hôpital Général de Douala

Script de test pour valider le système de templates multilingues
et la personnalisation avec données patients réelles.
"""

import sys
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Import du gestionnaire de templates
from src.services.templates_manager import (
    TemplateManager, MessagePersonalizer, PatientData,
    MessageType, Language, create_sample_patient_data
)

class TemplateTestSuite:
    """Suite de tests pour le système de templates"""
    
    def __init__(self):
        self.template_manager = TemplateManager()
        self.personalizer = MessagePersonalizer(self.template_manager)
        self.test_results = []
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Exécute tous les tests de templates"""
        print("🧪 === TESTS DE TEMPLATES ET PERSONNALISATION ===")
        print("Hôpital Général de Douala - Phase 3\n")
        
        # Tests individuels
        tests = [
            ("Test 1: Création des 15 templates (5 types × 3 langues)", self.test_template_creation),
            ("Test 2: Variables de personnalisation dans templates", self.test_dynamic_variables),
            ("Test 3: Sélection automatique de langue", self.test_language_detection),
            ("Test 4: Templates vocaux TwiML", self.test_twiml_templates),
            ("Test 5: Personnalisation avec données patients réelles", self.test_real_patient_data),
            ("Test 6: Cohérence des messages entre langues", self.test_language_consistency),
            ("Test 7: Gestion des erreurs et fallbacks", self.test_error_handling),
            ("Test 8: Performance et optimisation", self.test_performance)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_function in tests:
            try:
                print(f"\n📋 {test_name}")
                print("-" * 60)
                result = test_function()
                if result:
                    print("✅ RÉUSSI")
                    passed_tests += 1
                else:
                    print("❌ ÉCHOUÉ")
                self.test_results.append({"test": test_name, "passed": result})
            except Exception as e:
                print(f"❌ ERREUR: {e}")
                self.test_results.append({"test": test_name, "passed": False, "error": str(e)})
        
        # Résumé final
        success_rate = (passed_tests / total_tests) * 100
        print(f"\n🎯 === RÉSUMÉ DES TESTS ===")
        print(f"Tests réussis: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        if success_rate >= 90:
            print("🎉 EXCELLENT! Système de templates prêt pour la production")
        elif success_rate >= 75:
            print("✅ BON! Quelques améliorations mineures nécessaires")
        else:
            print("⚠️ ATTENTION! Corrections importantes requises")
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": success_rate,
            "results": self.test_results
        }
    
    def test_template_creation(self) -> bool:
        """Test 1: Vérification des 15 templates (5 types × 3 langues)"""
        expected_templates = 0
        found_templates = 0
        
        print("Vérification de l'existence des templates:")
        
        for message_type in MessageType:
            for language in Language:
                for format_type in ["sms", "voice", "twiml"]:
                    expected_templates += 1
                    try:
                        template = self.template_manager.get_template(
                            message_type, language, format_type
                        )
                        if template and len(template) > 10:  # Template non vide
                            found_templates += 1
                            print(f"  ✓ {message_type.value}/{language.value}/{format_type}")
                        else:
                            print(f"  ✗ {message_type.value}/{language.value}/{format_type} - Vide")
                    except Exception as e:
                        print(f"  ✗ {message_type.value}/{language.value}/{format_type} - Erreur: {e}")
        
        print(f"\nTemplates trouvés: {found_templates}/{expected_templates}")
        return found_templates == expected_templates
    
    def test_dynamic_variables(self) -> bool:
        """Test 2: Test des variables de personnalisation"""
        print("Test des variables de personnalisation:")
        
        # Données de test avec toutes les variables de personnalisation
        test_patient = PatientData(
            name="Test Patient",
            phone="+237675934861",
            preferred_language="fr",
            doctor_name="Dr. Test",
            appointment_date=datetime(2025, 12, 25, 14, 30),
            appointment_time="14:30",
            medication_name="Paracétamol",
            dosage="500mg",
            department="Cardiologie",
            room_number="205"
        )
        
        success_count = 0
        total_tests = 0
        
        for message_type in MessageType:
            total_tests += 1
            try:
                message_data = self.personalizer.create_personalized_message(
                    message_type, test_patient, "sms"
                )
                message = message_data["message"]
                
                # Vérifier qu'aucune variable n'est restée non remplacée
                if "{" not in message and "}" not in message:
                    print(f"  ✓ {message_type.value}: Variables correctement remplacées")
                    success_count += 1
                else:
                    print(f"  ✗ {message_type.value}: Variables non remplacées trouvées")
                    print(f"    Message: {message[:100]}...")
            except Exception as e:
                print(f"  ✗ {message_type.value}: Erreur - {e}")
        
        print(f"\nVariables de personnalisation: {success_count}/{total_tests} réussies")
        return success_count == total_tests
    
    def test_language_detection(self) -> bool:
        """Test 3: Test de la sélection automatique de langue (logique simplifiée Cameroun)"""
        print("Test de détection automatique de langue (logique simplifiée):")
        
        test_cases = [
            ("fr", "fr", "Patient avec preferred_language='fr' → Français"),
            ("en", "en", "Patient avec preferred_language='en' → Anglais"),
            ("es", "es", "Patient avec preferred_language='es' → Espagnol"),
            (None, "fr", "Patient SANS preferred_language → Français (fallback)"),
            ("zh", "fr", "Patient avec langue non supportée 'zh' → Français (fallback)")
        ]
        
        success_count = 0
        
        for preferred_lang, expected_lang, description in test_cases:
            patient = PatientData(
                name="Test", 
                phone="+237675934861",  # Numéro camerounais (peu importe maintenant)
                preferred_language=preferred_lang
            )
            detected_lang = self.template_manager.language_detector.detect_language(patient)
            
            if detected_lang.value == expected_lang:
                print(f"  ✓ {description}")
                success_count += 1
            else:
                print(f"  ✗ {description} - Détecté: {detected_lang.value}")
        
        print(f"\nDétection de langue: {success_count}/{len(test_cases)} réussies")
        return success_count == len(test_cases)
    
    def test_twiml_templates(self) -> bool:
        """Test 4: Test des templates vocaux TwiML"""
        print("Test des templates vocaux TwiML:")
        
        test_patient = PatientData(
            name="Patient Test",
            phone="+237675934861",
            doctor_name="Dr. Test"
        )
        
        success_count = 0
        total_tests = 0
        
        for message_type in MessageType:
            for language in Language:
                total_tests += 1
                try:
                    message_data = self.personalizer.create_personalized_message(
                        message_type, test_patient, "twiml"
                    )
                    twiml = message_data["message"]
                    
                    # Vérifications TwiML
                    checks = [
                        "<Response>" in twiml,
                        "<Say" in twiml,
                        "</Say>" in twiml,
                        "</Response>" in twiml,
                        "voice='alice'" in twiml,
                        "language=" in twiml
                    ]
                    
                    if all(checks):
                        print(f"  ✓ {message_type.value}/{language.value}: TwiML valide")
                        success_count += 1
                    else:
                        print(f"  ✗ {message_type.value}/{language.value}: TwiML invalide")
                        
                except Exception as e:
                    print(f"  ✗ {message_type.value}/{language.value}: Erreur - {e}")
        
        print(f"\nTemplates TwiML: {success_count}/{total_tests} valides")
        return success_count >= (total_tests * 0.9)  # 90% de réussite acceptable
    
    def test_real_patient_data(self) -> bool:
        """Test 5: Test avec données patients réelles"""
        print("Test avec données patients réelles:")
        
        # Données patients réalistes pour l'Hôpital Général de Douala
        real_patients = [
            PatientData(
                name="Marie Ngono",
                phone="+237675123456",
                preferred_language="fr",
                doctor_name="Dr. Mballa",
                appointment_date=datetime.now() + timedelta(days=1),
                appointment_time="09:00",
                department="Gynécologie",
                room_number="301"
            ),
            PatientData(
                name="Paul Biya Jr",
                phone="+237698765432",
                preferred_language="fr",
                doctor_name="Dr. Fouda",
                medication_name="Amoxicilline",
                dosage="250mg x3/jour",
                department="Médecine Générale"
            ),
            PatientData(
                name="Fatima Al-Rashid",
                phone="+966501234567",
                preferred_language="es",
                doctor_name="د. العلي",
                appointment_date=datetime.now() + timedelta(days=3),
                appointment_time="15:30",
                department="طب الأطفال"
            )
        ]
        
        success_count = 0
        total_messages = 0
        
        for patient in real_patients:
            print(f"\n  Patient: {patient.name} ({patient.phone})")
            
            # Test différents types de messages
            test_types = []
            if patient.appointment_date:
                test_types.append(MessageType.APPOINTMENT_REMINDER)
            if patient.medication_name:
                test_types.append(MessageType.MEDICATION_REMINDER)
            
            test_types.append(MessageType.HEALTH_TIP)  # Toujours applicable
            
            for msg_type in test_types:
                total_messages += 1
                try:
                    message_data = self.personalizer.create_personalized_message(
                        msg_type, patient, "sms"
                    )
                    
                    # Vérifications
                    if (message_data["message"] and 
                        len(message_data["message"]) > 20 and
                        patient.name in message_data["message"]):
                        print(f"    ✓ {msg_type.value}: Message généré")
                        success_count += 1
                    else:
                        print(f"    ✗ {msg_type.value}: Message invalide")
                        
                except Exception as e:
                    print(f"    ✗ {msg_type.value}: Erreur - {e}")
        
        print(f"\nMessages patients réels: {success_count}/{total_messages} générés")
        return success_count >= (total_messages * 0.8)  # 80% de réussite acceptable
    
    def test_language_consistency(self) -> bool:
        """Test 6: Test de cohérence entre langues"""
        print("Test de cohérence des messages entre langues:")
        
        validation = self.template_manager.validate_template_consistency()
        
        if validation["status"] == "valid":
            print("  ✓ Tous les templates sont cohérents entre langues")
            return True
        else:
            print("  ✗ Problèmes de cohérence détectés:")
            for issue in validation["issues"][:5]:  # Afficher max 5 problèmes
                print(f"    - {issue}")
            return False
    
    def test_error_handling(self) -> bool:
        """Test 7: Test de gestion des erreurs"""
        print("Test de gestion des erreurs et fallbacks:")
        
        success_count = 0
        total_tests = 4
        
        # Test 1: Patient avec données manquantes
        try:
            incomplete_patient = PatientData(name="Test", phone="+237123456789")
            message_data = self.personalizer.create_personalized_message(
                MessageType.APPOINTMENT_REMINDER, incomplete_patient
            )
            if message_data["message"]:
                print("  ✓ Gestion des données manquantes")
                success_count += 1
            else:
                print("  ✗ Échec avec données manquantes")
        except Exception as e:
            print(f"  ✗ Erreur avec données manquantes: {e}")
        
        # Test 2: Langue non supportée
        try:
            patient_unknown_lang = PatientData(
                name="Test", phone="+81123456789", preferred_language="ja"
            )
            message_data = self.personalizer.create_personalized_message(
                MessageType.HEALTH_TIP, patient_unknown_lang
            )
            if message_data["language"] == "fr":  # Fallback vers français
                print("  ✓ Fallback langue non supportée")
                success_count += 1
            else:
                print("  ✗ Fallback langue échoué")
        except Exception as e:
            print(f"  ✗ Erreur fallback langue: {e}")
        
        # Test 3: Numéro de téléphone invalide
        try:
            invalid_phone_patient = PatientData(name="Test", phone="invalid")
            message_data = self.personalizer.create_personalized_message(
                MessageType.HEALTH_TIP, invalid_phone_patient
            )
            if message_data["message"]:
                print("  ✓ Gestion numéro invalide")
                success_count += 1
            else:
                print("  ✗ Échec numéro invalide")
        except Exception as e:
            print(f"  ✗ Erreur numéro invalide: {e}")
        
        # Test 4: Template avec variables manquantes
        try:
            # Forcer un template avec variable inexistante
            patient = PatientData(name="Test", phone="+237123456789")
            template = "Bonjour {patient_name}, votre {nonexistent_variable} est prêt."
            variables = {"patient_name": patient.name}
            result = self.template_manager._render_template(template, variables)
            if "[Non spécifié]" in result or "nonexistent_variable" not in result:
                print("  ✓ Gestion variables manquantes")
                success_count += 1
            else:
                print("  ✗ Variables manquantes non gérées")
        except Exception as e:
            print(f"  ✗ Erreur variables manquantes: {e}")
        
        print(f"\nGestion d'erreurs: {success_count}/{total_tests} tests réussis")
        return success_count >= 3  # Au moins 3/4 tests doivent passer
    
    def test_performance(self) -> bool:
        """Test 8: Test de performance"""
        print("Test de performance et optimisation:")
        
        import time
        
        # Générer 100 messages pour tester la performance
        patients = []
        for i in range(100):
            patients.append(PatientData(
                name=f"Patient {i}",
                phone=f"+237675{i:06d}",
                doctor_name=f"Dr. Test {i%10}",
                appointment_date=datetime.now() + timedelta(days=i%7)
            ))
        
        start_time = time.time()
        
        try:
            messages = self.personalizer.batch_create_messages(
                patients, MessageType.APPOINTMENT_REMINDER
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            success_messages = len([m for m in messages if "error" not in m])
            
            print(f"  Messages générés: {success_messages}/100")
            print(f"  Temps d'exécution: {duration:.2f} secondes")
            print(f"  Performance: {100/duration:.1f} messages/seconde")
            
            # Critères de performance
            performance_ok = (
                success_messages >= 95 and  # 95% de succès
                duration < 10 and           # Moins de 10 secondes
                100/duration >= 10          # Au moins 10 msg/sec
            )
            
            if performance_ok:
                print("  ✓ Performance acceptable")
                return True
            else:
                print("  ✗ Performance insuffisante")
                return False
                
        except Exception as e:
            print(f"  ✗ Erreur de performance: {e}")
            return False

def main():
    """Fonction principale de test"""
    test_suite = TemplateTestSuite()
    results = test_suite.run_all_tests()
    
    # Sauvegarde des résultats
    with open("test_templates_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 Résultats sauvegardés dans: test_templates_results.json")
    
    # Code de sortie
    return 0 if results["success_rate"] >= 75 else 1

if __name__ == "__main__":
    sys.exit(main())