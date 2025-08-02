from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse
import logging
from urllib.parse import unquote
from src.models.models import Reminder
from src.database.database import DatabaseManager

logger = logging.getLogger(__name__)

app = Flask(__name__)

class TwiMLService:
    """Service pour générer les réponses TwiML"""
    
    @staticmethod
    def generate_voice_message(message: str, language: str = 'fr') -> str:
        """Génère une réponse TwiML pour message vocal"""
        response = VoiceResponse()
        
        # Configuration de la voix selon la langue
        voice_config = {
            'fr': 'alice',
            'en': 'alice', 
            'es': 'alice'
        }
        
        voice = voice_config.get(language, 'alice')
        
        # Message de bienvenue
        greeting = {
            'fr': "Bonjour, voici votre rappel médical:",
            'en': "Hello, here is your medical reminder:",
            'es': "Hola, aquí está su recordatorio médico:"
        }
        
        response.say(greeting.get(language, greeting['fr']), voice=voice, language=language)
        response.pause(length=1)
        response.say(message, voice=voice, language=language)
        response.pause(length=2)
        
        # Message de fin
        ending = {
            'fr': "Merci et bonne journée.",
            'en': "Thank you and have a good day.",
            'es': "Gracias y que tenga un buen día."
        }
        
        response.say(ending.get(language, ending['fr']), voice=voice, language=language)
        
        return str(response)

class WebhookService:
    """Service pour traiter les webhooks Twilio"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def handle_sms_status(self, webhook_data: dict) -> bool:
        """Traite les webhooks de statut SMS"""
        try:
            message_sid = webhook_data.get('MessageSid')
            status = webhook_data.get('MessageStatus')
            
            if not message_sid or not status:
                logger.warning("Données webhook incomplètes")
                return False
            
            # Mettre à jour le statut dans la base
            self._update_reminder_status(message_sid, status, 'sms')
            
            logger.info(f"Statut SMS mis à jour: {message_sid} -> {status}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur webhook SMS: {e}")
            return False
    
    def handle_call_status(self, webhook_data: dict) -> bool:
        """Traite les webhooks de statut d'appel"""
        try:
            call_sid = webhook_data.get('CallSid')
            status = webhook_data.get('CallStatus')
            duration = webhook_data.get('CallDuration', 0)
            
            if not call_sid or not status:
                logger.warning("Données webhook incomplètes")
                return False
            
            # Mettre à jour le statut dans la base
            self._update_reminder_status(call_sid, status, 'call', duration)
            
            logger.info(f"Statut appel mis à jour: {call_sid} -> {status}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur webhook appel: {e}")
            return False
    
    def _update_reminder_status(self, external_id: str, status: str, channel: str, duration: int = 0):
        """Met à jour le statut d'un rappel"""
        session = self.db_manager.get_session()
        
        try:
            # Mapper les statuts Twilio vers nos statuts
            status_mapping = {
                'queued': 'pending',
                'sending': 'pending', 
                'sent': 'sent',
                'delivered': 'delivered',
                'failed': 'failed',
                'undelivered': 'failed',
                'ringing': 'pending',
                'in-progress': 'sent',
                'completed': 'delivered',
                'busy': 'failed',
                'no-answer': 'failed'
            }
            
            mapped_status = status_mapping.get(status, 'pending')
            
            # Trouver le rappel par external_id (à implémenter selon votre logique)
            # Pour l'instant, on log juste l'information
            logger.info(f"Statut {channel}: {external_id} -> {mapped_status} (durée: {duration}s)")
            
        except Exception as e:
            logger.error(f"Erreur mise à jour statut: {e}")
        finally:
            session.close()

# Routes Flask pour les webhooks
@app.route('/twiml/voice', methods=['GET', 'POST'])
def voice_twiml():
    """Endpoint pour générer TwiML vocal"""
    message = request.args.get('message', 'Message de test')
    language = request.args.get('lang', 'fr')
    
    # Décoder le message
    message = unquote(message)
    
    twiml = TwiMLService.generate_voice_message(message, language)
    
    return Response(twiml, mimetype='text/xml')

@app.route('/webhook/sms', methods=['POST'])
def sms_webhook():
    """Webhook pour statuts SMS"""
    webhook_service = WebhookService()
    
    webhook_data = request.form.to_dict()
    success = webhook_service.handle_sms_status(webhook_data)
    
    if success:
        return 'OK', 200
    else:
        return 'Error', 400

@app.route('/webhook/voice', methods=['POST'])
def voice_webhook():
    """Webhook pour statuts d'appel"""
    webhook_service = WebhookService()
    
    webhook_data = request.form.to_dict()
    success = webhook_service.handle_call_status(webhook_data)
    
    if success:
        return 'OK', 200
    else:
        return 'Error', 400

@app.route('/test/twiml', methods=['GET'])
def test_twiml():
    """Test de génération TwiML"""
    test_messages = {
        'fr': 'Vous avez un rendez-vous médical demain à 14h.',
        'en': 'You have a medical appointment tomorrow at 2 PM.',
        'es': 'Tiene una cita médica mañana a las 2 PM.'
    }
    
    results = {}
    for lang, message in test_messages.items():
        twiml = TwiMLService.generate_voice_message(message, lang)
        results[lang] = twiml
    
    return results

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)