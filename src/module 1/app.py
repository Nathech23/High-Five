# -*- coding: utf-8 -*-
"""
Serveur Flask pour les webhooks et TwiML
Phase 3: Intégration des Templates et Personnalisation
"""

from flask import Flask, request, jsonify
from dotenv import load_dotenv
from src.services.twiml_service import TwiMLService, WebhookService
from src.services.communication_service import CommunicationManager
from src.services.templates_manager import (
    TemplateManager, MessagePersonalizer, PatientData,
    MessageType, Language
)
import os
import logging
from datetime import datetime, timedelta

# Charger les variables d'environnement
load_dotenv()

# Configuration Flask
app = Flask(__name__)
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialiser les services
webhook_service = WebhookService()
communication_manager = CommunicationManager()
template_manager = TemplateManager()
personalizer = MessagePersonalizer(template_manager)

@app.route('/')
def index():
    """Page d'accueil avec nouveaux endpoints Phase 3"""
    return jsonify({
        'service': 'Hospital Reminders API - Phase 3',
        'status': 'active',
        'version': '3.0.0',
        'features': {
            'templates': '15 templates (5 types × 3 langues)',
            'personalization': 'Variables dynamiques',
            'auto_language': 'Détection automatique',
            'twiml_voice': 'Templates vocaux TwiML'
        },
        'endpoints': {
            'twiml_voice': '/twiml/voice',
            'webhook_sms': '/webhook/sms',
            'webhook_voice': '/webhook/voice',
            'test_twiml': '/test/twiml',
            'test_communication': '/test/communication',
            'templates': {
                'send_personalized_sms': '/api/templates/sms',
                'send_personalized_call': '/api/templates/call',
                'validate_templates': '/api/templates/validate',
                'test_templates': '/api/templates/test'
            }
        }
    })

@app.route('/twiml/voice', methods=['GET', 'POST'])
def twiml_voice():
    """Endpoint pour les messages vocaux TwiML avec support templates"""
    try:
        # Support GET et POST pour compatibilité
        if request.method == 'GET':
            message = request.args.get('message', 'Message de test')
            language = request.args.get('lang', 'fr')
            twiml_content = request.args.get('twiml')  # Template TwiML pré-généré
        else:
            message = request.form.get('message', 'Message de test')
            language = request.form.get('language', 'fr')
            twiml_content = request.form.get('twiml')
        
        logger.info(f"Génération TwiML: {message} ({language})")
        
        # Si TwiML pré-généré fourni (Phase 3), l'utiliser directement
        if twiml_content:
            logger.info("Utilisation template TwiML pré-généré")
            return twiml_content, 200, {'Content-Type': 'text/xml'}
        
        # Sinon, génération classique
        twiml_response = TwiMLService.generate_voice_message(message, language)
        
        return twiml_response, 200, {'Content-Type': 'text/xml'}
        
    except Exception as e:
        logger.error(f"Erreur TwiML: {e}")
        return TwiMLService.generate_voice_message("Erreur du service", 'fr'), 500, {'Content-Type': 'text/xml'}

@app.route('/webhook/sms', methods=['POST'])
def webhook_sms():
    """Webhook pour le statut des SMS"""
    try:
        # Récupérer les données du webhook
        webhook_data = request.form.to_dict()
        
        logger.info(f"Webhook SMS reçu: {webhook_data}")
        
        # Traiter le webhook
        result = webhook_service.handle_sms_status(webhook_data)
        
        return jsonify({
            'status': 'success',
            'processed': result
        })
        
    except Exception as e:
        logger.error(f"Erreur webhook SMS: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/webhook/voice', methods=['POST'])
def webhook_voice():
    """Webhook pour le statut des appels"""
    try:
        # Récupérer les données du webhook
        webhook_data = request.form.to_dict()
        
        logger.info(f"Webhook appel reçu: {webhook_data}")
        
        # Traiter le webhook
        result = webhook_service.handle_call_status(webhook_data)
        
        return jsonify({
            'status': 'success',
            'processed': result
        })
        
    except Exception as e:
        logger.error(f"Erreur webhook appel: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/test/twiml', methods=['GET', 'POST'])
def test_twiml():
    """Endpoint de test pour TwiML"""
    try:
        # Messages de test dans différentes langues
        test_messages = {
            'fr': 'Bonjour, ceci est un test de message vocal en français.',
            'en': 'Hello, this is a voice message test in English.',
            'es': 'Hola, esta es una prueba de mensaje de voz en español.'
        }
        
        # Récupérer la langue demandée
        language = request.args.get('lang', 'fr')
        
        if language not in test_messages:
            language = 'fr'
        
        message = test_messages[language]
        
        logger.info(f"Test TwiML: {message} ({language})")
        
        # Générer la réponse TwiML
        twiml_response = TwiMLService.generate_voice_message(message, language)
        
        return twiml_response, 200, {'Content-Type': 'text/xml'}
        
    except Exception as e:
        logger.error(f"Erreur test TwiML: {e}")
        return TwiMLService.generate_voice_message("Erreur du service de test", 'fr'), 500, {'Content-Type': 'text/xml'}

@app.route('/test/communication', methods=['POST'])
def test_communication():
    """Endpoint pour tester la communication avec templates"""
    try:
        data = request.get_json()
        
        if not data or 'phone' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Numéro de téléphone requis'
            }), 400
        
        phone = data['phone']
        language = data.get('language', 'fr')
        message = data.get('message', 'Test de communication')
        use_templates = data.get('use_templates', True)
        simulate_only = data.get('simulate_only', True)  # Mode simulation par défaut
        
        logger.info(f"Test communication: {phone} ({language}) - Templates: {use_templates} - Simulation: {simulate_only}")
        
        if simulate_only:
            # Mode simulation - génère les messages sans envoyer
            result = communication_manager.test_communication_simulation(phone)
        elif use_templates:
            # Test avec nouveaux templates (appels réels)
            result = communication_manager.test_communication_templates(phone)
        else:
            # Test legacy (appels réels)
            result = communication_manager.test_communication(phone)
        
        return jsonify({
            'status': 'success',
            'message': 'Test de communication exécuté',
            'phone': phone,
            'language': language,
            'use_templates': use_templates,
            'simulate_only': simulate_only,
            'results': result
        })
        
    except Exception as e:
        logger.error(f"Erreur test communication: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# === NOUVEAUX ENDPOINTS PHASE 3: TEMPLATES ===

@app.route('/api/templates/sms', methods=['POST'])
def send_personalized_sms():
    """Envoie un SMS personnalisé avec templates"""
    try:
        data = request.get_json()
        
        # Validation des données requises
        if 'patient_data' not in data or 'message_type' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Champs requis: patient_data, message_type'
            }), 400
        
        patient_info = data['patient_data']
        
        # Création des données patient
        patient_data = PatientData(
            name=patient_info.get('name', ''),
            phone=patient_info.get('phone', ''),
            preferred_language=patient_info.get('preferred_language', 'fr'),
            doctor_name=patient_info.get('doctor_name', ''),
            appointment_date=datetime.fromisoformat(patient_info['appointment_date']) if patient_info.get('appointment_date') else None,
            appointment_time=patient_info.get('appointment_time', ''),
            medication_name=patient_info.get('medication_name', ''),
            dosage=patient_info.get('dosage', ''),
            department=patient_info.get('department', ''),
            room_number=patient_info.get('room_number', ''),
            emergency_contact=patient_info.get('emergency_contact', '')
        )
        
        # Conversion du type de message
        try:
            message_type = MessageType(data['message_type'])
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': f'Type de message invalide: {data["message_type"]}'
            }), 400
        
        # Envoi du SMS personnalisé
        result = communication_manager.send_personalized_sms(patient_data, message_type)
        
        return jsonify({
            'status': 'success' if result['success'] else 'error',
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Erreur SMS personnalisé: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/templates/call', methods=['POST'])
def send_personalized_call():
    """Lance un appel personnalisé avec templates TwiML"""
    try:
        data = request.get_json()
        
        # Validation des données requises
        if 'patient_data' not in data or 'message_type' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Champs requis: patient_data, message_type'
            }), 400
        
        patient_info = data['patient_data']
        
        # Création des données patient
        patient_data = PatientData(
            name=patient_info.get('name', ''),
            phone=patient_info.get('phone', ''),
            preferred_language=patient_info.get('preferred_language', 'fr'),
            doctor_name=patient_info.get('doctor_name', ''),
            appointment_date=datetime.fromisoformat(patient_info['appointment_date']) if patient_info.get('appointment_date') else None,
            appointment_time=patient_info.get('appointment_time', ''),
            medication_name=patient_info.get('medication_name', ''),
            dosage=patient_info.get('dosage', ''),
            department=patient_info.get('department', ''),
            room_number=patient_info.get('room_number', ''),
            emergency_contact=patient_info.get('emergency_contact', '')
        )
        
        # Conversion du type de message
        try:
            message_type = MessageType(data['message_type'])
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': f'Type de message invalide: {data["message_type"]}'
            }), 400
        
        # Lancement de l'appel personnalisé
        result = communication_manager.send_personalized_call(patient_data, message_type)
        
        return jsonify({
            'status': 'success' if result['success'] else 'error',
            'result': result
        })
        
    except Exception as e:
        logger.error(f"Erreur appel personnalisé: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/templates/validate', methods=['GET'])
def validate_templates():
    """Valide la cohérence des templates"""
    try:
        validation_result = communication_manager.get_template_validation()
        
        return jsonify({
            'status': 'success',
            'validation': validation_result
        })
        
    except Exception as e:
        logger.error(f"Erreur validation templates: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/templates/test', methods=['POST'])
def test_templates():
    """Test complet du système de templates"""
    try:
        data = request.get_json() or {}
        test_phone = data.get('phone', os.getenv('TEST_PHONE_NUMBER', '+237675934861'))
        
        logger.info(f"Test complet templates pour: {test_phone}")
        
        # Test avec données patient réalistes
        test_patient = PatientData(
            name="Patient Test Phase 3",
            phone=test_phone,
            preferred_language="fr",
            doctor_name="Dr. Test",
            appointment_date=datetime.now() + timedelta(days=1),
            appointment_time="14:30",
            medication_name="Paracétamol",
            dosage="500mg",
            department="Médecine Générale"
        )
        
        results = {}
        
        # Test pour chaque type de message
        for message_type in MessageType:
            try:
                # Test SMS
                sms_result = communication_manager.send_personalized_sms(
                    test_patient, message_type
                )
                
                results[message_type.value] = {
                    'sms': sms_result
                }
                
            except Exception as e:
                results[message_type.value] = {
                    'error': str(e)
                }
        
        # Validation des templates
        validation = communication_manager.get_template_validation()
        
        return jsonify({
            'status': 'success',
            'test_phone': test_phone,
            'results': results,
            'template_validation': validation
        })
        
    except Exception as e:
        logger.error(f"Erreur test templates: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Vérification de santé du service Phase 3"""
    try:
        # Vérification des templates
        template_validation = communication_manager.get_template_validation()
        
        return jsonify({
            'status': 'healthy',
            'service': 'Hospital Reminders API - Phase 3',
            'version': '3.0.0',
            'features': {
                'templates_count': 15,
                'languages': ['fr', 'en', 'es'],
                'message_types': [t.value for t in MessageType],
                'templates_valid': template_validation['status'] == 'valid'
            },
            'template_validation': template_validation
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'service': 'Hospital Reminders API - Phase 3',
            'version': '3.0.0',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Configuration du serveur
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    
    logger.info(f"Démarrage serveur Flask sur {host}:{port}")
    logger.info(f"Mode debug: {app.config['DEBUG']}")
    
    app.run(
        host=host,
        port=port,
        debug=app.config['DEBUG']
    )