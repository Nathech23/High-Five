"""
Service de communication externe (Twilio + Templates Multilingues)
Intégration du système de templates personnalisés
"""

import os
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
from googletrans import Translator
import logging
from typing import Dict, List, Optional
from urllib.parse import quote_plus
from datetime import datetime
from src.config.config import AppConfig

# Import du nouveau système de templates
from src.services.templates_manager import (
    TemplateManager, MessagePersonalizer, PatientData,
    MessageType, Language
)

logger = logging.getLogger(__name__)

class TwilioService:
    """Service Twilio pour SMS et appels"""
    
    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.phone_number = os.getenv('TWILIO_PHONE_NUMBER')
        
        if not all([self.account_sid, self.auth_token, self.phone_number]):
            raise ValueError("Configuration Twilio manquante")
            
        self.client = Client(self.account_sid, self.auth_token)
        
    def send_sms(self, to_phone: str, message: str) -> Dict:
        """Envoie un SMS"""
        try:
            message = self.client.messages.create(
                body=message,
                from_=self.phone_number,
                to=to_phone,
                status_callback=os.getenv('TWILIO_WEBHOOK_URL')
            )
            
            logger.info(f"SMS envoyé: {message.sid}")
            return {
                'success': True,
                'message_sid': message.sid,
                'status': message.status
            }
            
        except Exception as e:
            logger.error(f"Erreur SMS: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def make_voice_call(self, to_phone: str, twiml_url: str) -> Dict:
        """Lance un appel vocal"""
        try:
            call = self.client.calls.create(
                url=twiml_url,
                to=to_phone,
                from_=self.phone_number,
                status_callback=os.getenv('TWILIO_WEBHOOK_URL')
            )
            
            logger.info(f"Appel lancé: {call.sid}")
            return {
                'success': True,
                'call_sid': call.sid,
                'status': call.status
            }
            
        except Exception as e:
            logger.error(f"Erreur appel: {e}")
            return {
                'success': False,
                'error': str(e)
            }

class TemplateService:
    """Service de templates multilingues - Phase 3"""
    
    def __init__(self):
        self.template_manager = TemplateManager()
        self.personalizer = MessagePersonalizer(self.template_manager)
        self.translator = Translator()  # Fallback pour traductions custom
        self.supported_languages = {
            'fr': 'français',
            'en': 'english', 
            'es': 'español'
        }
    
    def create_personalized_message(self, message_type: MessageType, 
                                   patient_data: PatientData,
                                   format_type: str = "sms") -> Dict:
        """Crée un message personnalisé avec templates"""
        try:
            message_data = self.personalizer.create_personalized_message(
                message_type, patient_data, format_type
            )
            logger.info(f"Message {message_type.value} généré en {message_data['language']}")
            return {
                'success': True,
                'message': message_data['message'],
                'language': message_data['language'],
                'format_type': format_type,
                'character_count': message_data['character_count']
            }
        except Exception as e:
            logger.error(f"Erreur génération message: {e}")
            return {
                'success': False,
                'error': str(e),
                'fallback_message': self._create_fallback_message(patient_data)
            }
    
    def _create_fallback_message(self, patient_data: PatientData) -> str:
        """Message de fallback en cas d'erreur"""
        return f"Bonjour {patient_data.name}, message de l'Hôpital Général de Douala."
    
    def translate_custom_message(self, text: str, target_language: str) -> str:
        """Traduit un message personnalisé (fallback)"""
        try:
            if target_language not in self.supported_languages:
                logger.warning(f"Langue non supportée: {target_language}")
                return text
                
            if target_language == 'fr':
                return text  # Texte source en français
                
            result = self.translator.translate(text, dest=target_language)
            logger.info(f"Traduction custom {target_language}: {result.text}")
            return result.text
            
        except Exception as e:
            logger.error(f"Erreur traduction custom: {e}")
            return text
    
    def get_supported_languages(self) -> List[str]:
        """Retourne les langues supportées"""
        return list(self.supported_languages.keys())
    
    def validate_templates(self) -> Dict:
        """Valide la cohérence des templates"""
        return self.template_manager.validate_template_consistency()

class CommunicationManager:
    """Gestionnaire principal de communication - Phase 3 avec Templates"""
    
    def __init__(self):
        self.twilio = TwilioService()
        self.template_service = TemplateService()
        
    def send_personalized_sms(self, patient_data: PatientData, 
                             message_type: MessageType) -> Dict:
        """Envoie un SMS personnalisé avec templates"""
        try:
            # Génération du message personnalisé
            message_result = self.template_service.create_personalized_message(
                message_type, patient_data, "sms"
            )
            
            if not message_result['success']:
                return message_result
            
            # Envoi du SMS
            sms_result = self.twilio.send_sms(
                patient_data.phone, 
                message_result['message']
            )
            
            # Combinaison des résultats
            return {
                'success': sms_result['success'],
                'message_sid': sms_result.get('message_sid'),
                'language': message_result['language'],
                'message_type': message_type.value,
                'character_count': message_result['character_count'],
                'error': sms_result.get('error')
            }
            
        except Exception as e:
            logger.error(f"Erreur SMS personnalisé: {e}")
            return {'success': False, 'error': str(e)}
    
    def send_personalized_call(self, patient_data: PatientData, 
                              message_type: MessageType) -> Dict:
        """Lance un appel personnalisé avec templates TwiML"""
        try:
            # Génération du message vocal TwiML
            message_result = self.template_service.create_personalized_message(
                message_type, patient_data, "twiml"
            )
            
            if not message_result['success']:
                return message_result
            
            # Génération de l'URL TwiML
            twiml_url = self._generate_twiml_url_with_template(
                message_result['message'], 
                message_result['language']
            )
            
            # Lancement de l'appel
            call_result = self.twilio.make_voice_call(patient_data.phone, twiml_url)
            
            return {
                'success': call_result['success'],
                'call_sid': call_result.get('call_sid'),
                'language': message_result['language'],
                'message_type': message_type.value,
                'twiml_url': twiml_url,
                'error': call_result.get('error')
            }
            
        except Exception as e:
            logger.error(f"Erreur appel personnalisé: {e}")
            return {'success': False, 'error': str(e)}
    
    def _generate_twiml_url_with_template(self, twiml_content: str, language: str) -> str:
        """Génère l'URL TwiML avec contenu pré-généré"""
        base_url = os.getenv('BASE_URL', 'http://localhost:5000')
        encoded_twiml = quote_plus(twiml_content)
        encoded_language = quote_plus(language)
        return f"{base_url}/twiml/voice?twiml={encoded_twiml}&lang={encoded_language}"
    
    def send_reminder_sms(self, phone: str, message: str, language: str = 'fr') -> Dict:
        """Méthode legacy - Envoie un rappel par SMS avec traduction"""
        translated_message = self.template_service.translate_custom_message(message, language)
        return self.twilio.send_sms(phone, translated_message)
    
    def send_reminder_call(self, phone: str, message: str, language: str = 'fr') -> Dict:
        """Méthode legacy - Lance un appel de rappel avec message vocal"""
        translated_message = self.template_service.translate_custom_message(message, language)
        twiml_url = self._generate_twiml_url(translated_message, language)
        return self.twilio.make_voice_call(phone, twiml_url)
    
    def _generate_twiml_url(self, message: str, language: str) -> str:
        """Génère l'URL TwiML legacy"""
        base_url = os.getenv('BASE_URL', 'http://localhost:5000')
        encoded_message = quote_plus(message)
        encoded_language = quote_plus(language)
        return f"{base_url}/twiml/voice?message={encoded_message}&lang={encoded_language}"
    
    def test_communication_templates(self, test_phone: str) -> Dict:
        """Test de communication avec nouveaux templates"""
        results = {}
        
        # Données patient de test
        test_patient = PatientData(
            name="Patient Test",
            phone=test_phone,
            doctor_name="Dr. Test",
            appointment_date=datetime.now(),
            appointment_time="14:30",
            department="Test"
        )
        
        # Test pour chaque langue supportée
        for lang in ['fr', 'en', 'es']:
            test_patient.preferred_language = lang
            logger.info(f"Test templates {lang}...")
            
            # Test SMS de rappel de rendez-vous
            sms_result = self.send_personalized_sms(
                test_patient, MessageType.APPOINTMENT_REMINDER
            )
            
            # Test conseil santé
            health_tip_result = self.send_personalized_sms(
                test_patient, MessageType.HEALTH_TIP
            )
            
            results[lang] = {
                'appointment_sms': sms_result,
                'health_tip_sms': health_tip_result
            }
            
        return results
    
    def test_communication(self, test_phone: str) -> Dict:
        """Test de communication legacy dans 3 langues"""
        test_message = "Test de rappel médical"
        results = {}
        
        for lang in ['fr', 'en', 'es']:
            logger.info(f"Test legacy {lang}...")
            
            # Test SMS
            sms_result = self.send_reminder_sms(test_phone, test_message, lang)
            
            results[lang] = {
                'sms': sms_result
            }
            
        return results
    
    def test_communication_simulation(self, test_phone: str) -> Dict:
        """Test de communication en mode simulation (sans appels Twilio réels)"""
        results = {}
        
        # Données patient de test
        test_patient = PatientData(
            name="Patient Test Simulation",
            phone=test_phone,
            doctor_name="Dr. Test",
            appointment_date=datetime.now(),
            appointment_time="14:30",
            department="Test"
        )
        
        # Test pour chaque langue supportée
        for lang in ['fr', 'en', 'es']:
            test_patient.preferred_language = lang
            logger.info(f"Simulation templates {lang}...")
            
            try:
                # Génération des messages sans envoi
                appointment_msg = self.template_service.create_personalized_message(
                    MessageType.APPOINTMENT_REMINDER, test_patient, "sms"
                )
                
                health_tip_msg = self.template_service.create_personalized_message(
                    MessageType.HEALTH_TIP, test_patient, "sms"
                )
                
                results[lang] = {
                    'appointment_sms': {
                        'success': True,
                        'simulated': True,
                        'message_preview': appointment_msg['message'][:100] + '...' if len(appointment_msg['message']) > 100 else appointment_msg['message'],
                        'language': appointment_msg['language'],
                        'character_count': appointment_msg['character_count']
                    },
                    'health_tip_sms': {
                        'success': True,
                        'simulated': True,
                        'message_preview': health_tip_msg['message'][:100] + '...' if len(health_tip_msg['message']) > 100 else health_tip_msg['message'],
                        'language': health_tip_msg['language'],
                        'character_count': health_tip_msg['character_count']
                    }
                }
                
            except Exception as e:
                logger.error(f"Erreur simulation {lang}: {e}")
                results[lang] = {
                    'appointment_sms': {'success': False, 'error': str(e)},
                    'health_tip_sms': {'success': False, 'error': str(e)}
                }
        
        return results
    
    def get_template_validation(self) -> Dict:
        """Retourne la validation des templates"""
        return self.template_service.validate_templates()

# Configuration par défaut
if __name__ == "__main__":
    # Test basique
    try:
        comm = CommunicationManager()
        print("Service de communication initialisé")
        print(f"Langues supportées: {comm.translator.get_supported_languages()}")
    except Exception as e:
        print(f"Erreur: {e}")