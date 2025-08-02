import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

class MessageType(Enum):
    """Types de messages supportés"""
    APPOINTMENT_REMINDER = "appointment_reminder"
    MEDICATION_REMINDER = "medication_reminder"
    FOLLOW_UP = "follow_up"
    EMERGENCY_ALERT = "emergency_alert"
    HEALTH_TIP = "health_tip"

class Language(Enum):
    """Langues supportées"""
    FRENCH = "fr"
    ENGLISH = "en"
    SPANISH = "es"

@dataclass
class PatientData:
    """Données patient pour personnalisation"""
    name: str
    phone: str
    preferred_language: str = "fr"
    doctor_name: str = ""
    appointment_date: Optional[datetime] = None
    appointment_time: Optional[str] = None
    medication_name: str = ""
    dosage: str = ""
    department: str = ""
    room_number: str = ""
    emergency_contact: str = ""

class TemplateManager:
    """Gestionnaire principal des templates"""
    
    def __init__(self):
        self.templates = self._load_templates()
        self.language_detector = LanguageDetector()
    
    def _load_templates(self) -> Dict[str, Dict[str, Dict[str, str]]]:
        """Charge tous les templates (5 types × 3 langues)"""
        templates = {}
        
        # Templates personnalisés pour rendez-vous (APPOINTMENT_REMINDER)
        templates[MessageType.APPOINTMENT_REMINDER.value] = {
            Language.FRENCH.value: {
                "sms": "Bonjour {patient_name}, votre rendez-vous avec {doctor_name} est prévu le {appointment_date} à {appointment_time} au service {department} de {hospital_name}. Merci de vous présenter 15 minutes avant l'heure. Contact: {contact_phone}",
                "voice": "Bonjour {patient_name}. Votre rendez-vous médical avec le docteur {doctor_name} est programmé pour le {appointment_date_spoken} à {appointment_time}. Veuillez vous présenter au service {department} de {hospital_name}. Contact: {contact_phone}. Merci.",
                "twiml": "<Response><Say voice='alice' language='fr-FR'>Bonjour {patient_name}. Votre rendez-vous médical avec le docteur {doctor_name} est programmé pour le {appointment_date_spoken} à {appointment_time}. Veuillez vous présenter au service {department} de {hospital_name}. Contact: {contact_phone}. Merci.</Say></Response>"
            },
            Language.ENGLISH.value: {
                "sms": "Hello {patient_name}, your appointment with Dr. {doctor_name} is scheduled for {appointment_date} at {appointment_time} in {department} department at {hospital_name}. Please arrive 15 minutes early. Contact: {contact_phone}",
                "voice": "Hello {patient_name}. Your medical appointment with Doctor {doctor_name} is scheduled for {appointment_date_spoken} at {appointment_time}. Please report to the {department} department at {hospital_name}. Contact: {contact_phone}. Thank you.",
                "twiml": "<Response><Say voice='alice' language='en-US'>Hello {patient_name}. Your medical appointment with Doctor {doctor_name} is scheduled for {appointment_date_spoken} at {appointment_time}. Please report to the {department} department at {hospital_name}. Contact: {contact_phone}. Thank you.</Say></Response>"
            },
            Language.SPANISH.value: {
                "sms": "Hola {patient_name}, su cita con el Dr. {doctor_name} está programada para el {appointment_date} a las {appointment_time} en el departamento de {department} en {hospital_name}. Por favor llegue 15 minutos antes. Contacto: {contact_phone}",
                "voice": "Hola {patient_name}. Su cita médica con el Doctor {doctor_name} está programada para el {appointment_date_spoken} a las {appointment_time}. Por favor diríjase al departamento de {department} en {hospital_name}. Contacto: {contact_phone}. Gracias.",
                "twiml": "<Response><Say voice='alice' language='es-ES'>Hola {patient_name}. Su cita médica con el Doctor {doctor_name} está programada para el {appointment_date_spoken} a las {appointment_time}. Por favor diríjase al departamento de {department} en {hospital_name}. Contacto: {contact_phone}. Gracias.</Say></Response>"
            }
        }
        
        return {
            # APPOINTMENT_REMINDER
            MessageType.APPOINTMENT_REMINDER.value: {
                Language.FRENCH.value: {
                    "sms": "Bonjour {patient_name}, rappel de votre rendez-vous avec {doctor_name} le {appointment_date} à {appointment_time} au service {department} de {hospital_name}. Merci de vous présenter 15 minutes avant l'heure. Contact: {contact_phone}",
                    "voice": "Bonjour {patient_name}. Ceci est un rappel de votre rendez-vous médical avec le docteur {doctor_name}, prévu le {appointment_date_spoken} à {appointment_time}. Veuillez vous présenter au service {department} de {hospital_name}. Contact: {contact_phone}. Merci.",
                    "twiml": "<Response><Say voice='alice' language='fr-FR'>Bonjour {patient_name}. Ceci est un rappel de votre rendez-vous médical avec le docteur {doctor_name}, prévu le {appointment_date_spoken} à {appointment_time}. Veuillez vous présenter au service {department} de {hospital_name}. Contact: {contact_phone}. Merci.</Say></Response>"
                },
                Language.ENGLISH.value: {
                    "sms": "Hello {patient_name}, reminder of your appointment with Dr. {doctor_name} on {appointment_date} at {appointment_time} in {department} department at {hospital_name}. Please arrive 15 minutes early. Contact: {contact_phone}",
                    "voice": "Hello {patient_name}. This is a reminder of your medical appointment with Doctor {doctor_name}, scheduled for {appointment_date_spoken} at {appointment_time}. Please report to the {department} department at {hospital_name}. Contact: {contact_phone}. Thank you.",
                    "twiml": "<Response><Say voice='alice' language='en-US'>Hello {patient_name}. This is a reminder of your medical appointment with Doctor {doctor_name}, scheduled for {appointment_date_spoken} at {appointment_time}. Please report to the {department} department at {hospital_name}. Contact: {contact_phone}. Thank you.</Say></Response>"
                },
                Language.SPANISH.value: {
                    "sms": "Hola {patient_name}, recordatorio de su cita con el Dr. {doctor_name} el {appointment_date} a las {appointment_time} en el departamento de {department} en {hospital_name}. Por favor llegue 15 minutos antes. Contacto: {contact_phone}",
                    "voice": "Hola {patient_name}. Este es un recordatorio de su cita médica con el Doctor {doctor_name}, programada para el {appointment_date_spoken} a las {appointment_time}. Por favor diríjase al departamento de {department} en {hospital_name}. Contacto: {contact_phone}. Gracias.",
                    "twiml": "<Response><Say voice='alice' language='es-ES'>Hola {patient_name}. Este es un recordatorio de su cita médica con el Doctor {doctor_name}, programada para el {appointment_date_spoken} a las {appointment_time}. Por favor diríjase al departamento de {department} en {hospital_name}. Contacto: {contact_phone}. Gracias.</Say></Response>"
                }
            },
            
            # MEDICATION_REMINDER
            MessageType.MEDICATION_REMINDER.value: {
                Language.FRENCH.value: {
                    "sms": "Bonjour {patient_name}, il est temps de prendre votre médicament {medication_name} - {dosage}. N'oubliez pas votre traitement. Hôpital Général de Douala.",
                    "voice": "Bonjour {patient_name}. Ceci est un rappel pour prendre votre médicament {medication_name}, dosage {dosage}. Il est important de respecter votre traitement médical. Hôpital Général de Douala.",
                    "twiml": "<Response><Say voice='alice' language='fr-FR'>Bonjour {patient_name}. Ceci est un rappel pour prendre votre médicament {medication_name}, dosage {dosage}. Il est important de respecter votre traitement médical. Hôpital Général de Douala.</Say></Response>"
                },
                Language.ENGLISH.value: {
                    "sms": "Hello {patient_name}, time to take your medication {medication_name} - {dosage}. Don't forget your treatment. Douala General Hospital.",
                    "voice": "Hello {patient_name}. This is a reminder to take your medication {medication_name}, dosage {dosage}. It is important to follow your medical treatment. Douala General Hospital.",
                    "twiml": "<Response><Say voice='alice' language='en-US'>Hello {patient_name}. This is a reminder to take your medication {medication_name}, dosage {dosage}. It is important to follow your medical treatment. Douala General Hospital.</Say></Response>"
                },
                Language.SPANISH.value: {
                    "sms": "Hola {patient_name}, es hora de tomar su medicamento {medication_name} - {dosage}. No olvide su tratamiento. Hospital General de Douala.",
                    "voice": "Hola {patient_name}. Este es un recordatorio para tomar su medicamento {medication_name}, dosis {dosage}. Es importante seguir su tratamiento médico. Hospital General de Douala.",
                    "twiml": "<Response><Say voice='alice' language='es-ES'>Hola {patient_name}. Este es un recordatorio para tomar su medicamento {medication_name}, dosis {dosage}. Es importante seguir su tratamiento médico. Hospital General de Douala.</Say></Response>"
                }
            },
            
            # FOLLOW_UP
            MessageType.FOLLOW_UP.value: {
                Language.FRENCH.value: {
                    "sms": "Bonjour {patient_name}, votre suivi médical avec {doctor_name} est prévu le {appointment_date}. Merci de confirmer votre présence. Hôpital Général de Douala.",
                    "voice": "Bonjour {patient_name}. Votre rendez-vous de suivi médical avec le docteur {doctor_name} est programmé pour le {appointment_date_spoken}. Merci de confirmer votre présence auprès de l'Hôpital Général de Douala.",
                    "twiml": "<Response><Say voice='alice' language='fr-FR'>Bonjour {patient_name}. Votre rendez-vous de suivi médical avec le docteur {doctor_name} est programmé pour le {appointment_date_spoken}. Merci de confirmer votre présence auprès de l'Hôpital Général de Douala.</Say></Response>"
                },
                Language.ENGLISH.value: {
                    "sms": "Hello {patient_name}, your medical follow-up with Dr. {doctor_name} is scheduled for {appointment_date}. Please confirm your attendance. Douala General Hospital.",
                    "voice": "Hello {patient_name}. Your medical follow-up appointment with Doctor {doctor_name} is scheduled for {appointment_date_spoken}. Please confirm your attendance with Douala General Hospital.",
                    "twiml": "<Response><Say voice='alice' language='en-US'>Hello {patient_name}. Your medical follow-up appointment with Doctor {doctor_name} is scheduled for {appointment_date_spoken}. Please confirm your attendance with Douala General Hospital.</Say></Response>"
                },
                Language.SPANISH.value: {
                    "sms": "Hola {patient_name}, su seguimiento médico con el Dr. {doctor_name} está programado para el {appointment_date}. Por favor confirme su asistencia. Hospital General de Douala.",
                    "voice": "Hola {patient_name}. Su cita de seguimiento médico con el Doctor {doctor_name} está programada para el {appointment_date_spoken}. Por favor confirme su asistencia con el Hospital General de Douala.",
                    "twiml": "<Response><Say voice='alice' language='es-ES'>Hola {patient_name}. Su cita de seguimiento médico con el Doctor {doctor_name} está programada para el {appointment_date_spoken}. Por favor confirme su asistencia con el Hospital General de Douala.</Say></Response>"
                }
            },
            
            # EMERGENCY_ALERT
            MessageType.EMERGENCY_ALERT.value: {
                Language.FRENCH.value: {
                    "sms": "URGENT - {patient_name}, veuillez contacter immédiatement l'Hôpital Général de Douala au +237-XXX ou vous rendre aux urgences. Votre médecin {doctor_name} vous attend.",
                    "voice": "Message urgent pour {patient_name}. Veuillez contacter immédiatement l'Hôpital Général de Douala ou vous rendre aux urgences. Votre médecin traitant {doctor_name} vous attend. Ceci est un message prioritaire.",
                    "twiml": "<Response><Say voice='alice' language='fr-FR'>Message urgent pour {patient_name}. Veuillez contacter immédiatement l'Hôpital Général de Douala ou vous rendre aux urgences. Votre médecin traitant {doctor_name} vous attend. Ceci est un message prioritaire.</Say></Response>"
                },
                Language.ENGLISH.value: {
                    "sms": "URGENT - {patient_name}, please immediately contact Douala General Hospital at +237-XXX or go to emergency. Your doctor {doctor_name} is waiting for you.",
                    "voice": "Urgent message for {patient_name}. Please immediately contact Douala General Hospital or go to the emergency department. Your attending physician {doctor_name} is waiting for you. This is a priority message.",
                    "twiml": "<Response><Say voice='alice' language='en-US'>Urgent message for {patient_name}. Please immediately contact Douala General Hospital or go to the emergency department. Your attending physician {doctor_name} is waiting for you. This is a priority message.</Say></Response>"
                },
                Language.SPANISH.value: {
                    "sms": "URGENTE - {patient_name}, por favor contacte inmediatamente al Hospital General de Douala al +237-XXX o diríjase a emergencias. Su doctor {doctor_name} le está esperando.",
                    "voice": "Mensaje urgente para {patient_name}. Por favor contacte inmediatamente al Hospital General de Douala o diríjase al departamento de emergencias. Su médico tratante {doctor_name} le está esperando. Este es un mensaje prioritario.",
                    "twiml": "<Response><Say voice='alice' language='es-ES'>Mensaje urgente para {patient_name}. Por favor contacte inmediatamente al Hospital General de Douala o diríjase al departamento de emergencias. Su médico tratante {doctor_name} le está esperando. Este es un mensaje prioritario.</Say></Response>"
                }
            },
            
            # HEALTH_TIP
            MessageType.HEALTH_TIP.value: {
                Language.FRENCH.value: {
                    "sms": "Bonjour {patient_name}, conseil santé du jour : Buvez au moins 8 verres d'eau par jour pour rester hydraté. Prenez soin de vous ! Hôpital Général de Douala.",
                    "voice": "Bonjour {patient_name}. Voici votre conseil santé du jour de l'Hôpital Général de Douala : Il est important de boire au moins huit verres d'eau par jour pour maintenir une bonne hydratation. Prenez soin de votre santé.",
                    "twiml": "<Response><Say voice='alice' language='fr-FR'>Bonjour {patient_name}. Voici votre conseil santé du jour de l'Hôpital Général de Douala : Il est important de boire au moins huit verres d'eau par jour pour maintenir une bonne hydratation. Prenez soin de votre santé.</Say></Response>"
                },
                Language.ENGLISH.value: {
                    "sms": "Hello {patient_name}, health tip of the day: Drink at least 8 glasses of water daily to stay hydrated. Take care of yourself! Douala General Hospital.",
                    "voice": "Hello {patient_name}. Here is your health tip of the day from Douala General Hospital: It is important to drink at least eight glasses of water daily to maintain good hydration. Take care of your health.",
                    "twiml": "<Response><Say voice='alice' language='en-US'>Hello {patient_name}. Here is your health tip of the day from Douala General Hospital: It is important to drink at least eight glasses of water daily to maintain good hydration. Take care of your health.</Say></Response>"
                },
                Language.SPANISH.value: {
                    "sms": "Hola {patient_name}, consejo de salud del día: Beba al menos 8 vasos de agua diarios para mantenerse hidratado. ¡Cuídese! Hospital General de Douala.",
                    "voice": "Hola {patient_name}. Aquí tiene su consejo de salud del día del Hospital General de Douala: Es importante beber al menos ocho vasos de agua diarios para mantener una buena hidratación. Cuide su salud.",
                    "twiml": "<Response><Say voice='alice' language='es-ES'>Hola {patient_name}. Aquí tiene su consejo de salud del día del Hospital General de Douala: Es importante beber al menos ocho vasos de agua diarios para mantener una buena hidratación. Cuide su salud.</Say></Response>"
                }
            }
        }
    
    def get_template(self, message_type: MessageType, language: Language, format_type: str = "sms") -> str:
        """Récupère un template spécifique"""
        try:
            return self.templates[message_type.value][language.value][format_type]
        except KeyError:
            # Fallback vers français si langue non trouvée
            return self.templates[message_type.value][Language.FRENCH.value][format_type]
    
    def render_message(self, message_type: MessageType, patient_data: PatientData, 
                      format_type: str = "sms") -> str:
        """Génère un message personnalisé avec variables dynamiques"""
        # Détection automatique de la langue
        language = self.language_detector.detect_language(patient_data)
        
        # Récupération du template
        template = self.get_template(message_type, language, format_type)
        
        # Préparation des variables dynamiques
        variables = self._prepare_variables(patient_data)
        
        # Rendu du template avec variables
        return self._render_template(template, variables)
    
    def _prepare_variables(self, patient_data: PatientData) -> Dict[str, str]:
        """Prépare toutes les variables dynamiques"""
        # Formatage de la date pour la voix
        appointment_date_spoken = ""
        if patient_data.appointment_date:
            appointment_date_spoken = patient_data.appointment_date.strftime('%A %d %B %Y')
        
        variables = {
            'patient_name': patient_data.name or 'Patient',
            'doctor_name': patient_data.doctor_name or "votre médecin",
            'appointment_date': patient_data.appointment_date.strftime('%d/%m/%Y') if patient_data.appointment_date else 'Date à confirmer',
            'appointment_date_spoken': appointment_date_spoken or 'Date à confirmer',
            'appointment_time': patient_data.appointment_time or 'Heure à confirmer',
            'medication_name': patient_data.medication_name or 'Médicament',
            'dosage': patient_data.dosage or 'Dosage à confirmer',
            'department': patient_data.department or "consultation",
            'room_number': getattr(patient_data, 'room_number', 'Salle à confirmer') or 'Salle à confirmer',
            'emergency_contact': getattr(patient_data, 'emergency_contact', 'Contact d\'urgence') or 'Contact d\'urgence',
            'hospital_name': 'Hôpital Général de Douala',
            'contact_phone': '+237 233 40 25 12'
        }
        
        # Formatage des dates
        if patient_data.appointment_date:
            variables['appointment_date'] = patient_data.appointment_date.strftime("%d/%m/%Y")
            variables['appointment_date_spoken'] = self._format_spoken_date(
                patient_data.appointment_date, patient_data.preferred_language
            )
        
        if patient_data.appointment_time:
            variables['appointment_time'] = patient_data.appointment_time
        
        return variables
    
    def _format_spoken_date(self, date: datetime, language: str) -> str:
        """Formate une date pour la synthèse vocale"""
        if language == "fr":
            months = [
                "janvier", "février", "mars", "avril", "mai", "juin",
                "juillet", "août", "septembre", "octobre", "novembre", "décembre"
            ]
            return f"{date.day} {months[date.month-1]} {date.year}"
        elif language == "en":
            return date.strftime("%B %d, %Y")
        elif language == "es":
            months = [
                "enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
            ]
            return f"{date.day} de {months[date.month-1]} de {date.year}"
        else:
            return date.strftime("%d/%m/%Y")
    
    def _render_template(self, template: str, variables: Dict[str, str]) -> str:
        """Effectue le rendu du template avec les variables"""
        try:
            return template.format(**variables)
        except KeyError as e:
            # Gestion des variables manquantes
            print(f"Variable manquante dans le template: {e}")
            # Remplacer les variables manquantes par des valeurs par défaut
            safe_variables = {k: v or "[Non spécifié]" for k, v in variables.items()}
            return template.format(**safe_variables)
    
    def validate_template_consistency(self) -> Dict[str, List[str]]:
        """Valide la cohérence des templates entre langues"""
        issues = []
        
        for message_type in MessageType:
            for format_type in ["sms", "voice", "twiml"]:
                # Vérifier que tous les templates existent
                for language in Language:
                    try:
                        template = self.get_template(message_type, language, format_type)
                        # Vérifier les variables dans le template
                        variables = re.findall(r'\{([^}]+)\}', template)
                        if not variables:
                            issues.append(f"{message_type.value}/{language.value}/{format_type}: Aucune variable trouvée")
                    except Exception as e:
                        issues.append(f"{message_type.value}/{language.value}/{format_type}: {str(e)}")
        
        return {"issues": issues, "status": "valid" if not issues else "invalid"}

class LanguageDetector:
    """Détecteur de langue pour le Cameroun"""
    
    def __init__(self):
        # Application locale au Cameroun - pas besoin de mapping pays
        pass
    
    def detect_language(self, patient_data: PatientData) -> Language:
        """Détecte la langue préférée du patient"""
        # 1. Langue explicitement définie par le patient
        if patient_data.preferred_language:
            try:
                return Language(patient_data.preferred_language)
            except ValueError:
                # Si la langue n'est pas supportée, fallback vers français
                pass
        
        # 2. Fallback vers français (langue principale du Cameroun)
        return Language.FRENCH
    
    def detect_from_phone(self, phone_number: str) -> str:
        """Retourne la langue par défaut (français) pour le Cameroun"""
        return "fr"  # Défaut français pour le Cameroun

class MessagePersonalizer:
    """Personnalisateur avancé de messages"""
    
    def __init__(self, template_manager: TemplateManager):
        self.template_manager = template_manager
    
    def create_personalized_message(self, message_type: MessageType, 
                                   patient_data: PatientData, 
                                   format_type: str = "sms",
                                   custom_variables: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Crée un message personnalisé complet"""
        # Génération du message
        message = self.template_manager.render_message(message_type, patient_data, format_type)
        
        # Ajout de variables personnalisées
        if custom_variables:
            for key, value in custom_variables.items():
                message = message.replace(f"{{{key}}}", value)
        
        # Vérification et remplacement des variables manquantes
        import re
        remaining_vars = re.findall(r'\{([^}]+)\}', message)
        if remaining_vars:
            for var in remaining_vars:
                placeholder = f'{{{var}}}'
                message = message.replace(placeholder, '[Information non disponible]')
        
        # Détection de la langue
        language = self.template_manager.language_detector.detect_language(patient_data)
        
        return {
            "message": message,
            "language": language.value,
            "message_type": message_type.value,
            "format_type": format_type,
            "patient_phone": patient_data.phone,
            "timestamp": datetime.now().isoformat(),
            "character_count": len(message)
        }
    
    def batch_create_messages(self, patients_data: List[PatientData], 
                            message_type: MessageType,
                            format_type: str = "sms") -> List[Dict[str, Any]]:
        """Crée des messages en lot pour plusieurs patients"""
        messages = []
        for patient_data in patients_data:
            try:
                message_data = self.create_personalized_message(
                    message_type, patient_data, format_type
                )
                messages.append(message_data)
            except Exception as e:
                print(f"Erreur lors de la création du message pour {patient_data.name}: {e}")
                messages.append({
                    "error": str(e),
                    "patient_phone": patient_data.phone,
                    "message_type": message_type.value
                })
        return messages

# Fonction utilitaire pour tests
def create_sample_patient_data() -> List[PatientData]:
    """Crée des données patients d'exemple pour tests"""
    return [
        PatientData(
            name="Jean Dupont",
            phone="+237675934861",
            preferred_language="fr",
            doctor_name="Dr. Mballa",
            appointment_date=datetime.now() + timedelta(days=1),
            appointment_time="14:30",
            department="Cardiologie",
            room_number="205"
        ),
        PatientData(
            name="Sarah Johnson",
            phone="+19033647327",
            preferred_language="en",
            doctor_name="Dr. Smith",
            medication_name="Paracétamol",
            dosage="500mg",
            department="General Medicine"
        ),
        PatientData(
            name="أحمد محمد",
            phone="+966501234567",
            preferred_language="ar",
            doctor_name="د. العلي",
            appointment_date=datetime.now() + timedelta(days=2),
            appointment_time="10:00",
            department="طب الأطفال"
        )
    ]

if __name__ == "__main__":
    # Test du système de templates
    template_manager = TemplateManager()
    personalizer = MessagePersonalizer(template_manager)
    
    # Test avec données d'exemple
    sample_patients = create_sample_patient_data()
    
    print("=== Test du Système de Templates ===")
    
    for patient in sample_patients:
        print(f"\n--- Patient: {patient.name} ---")
        
        # Test message de rappel de rendez-vous
        if patient.appointment_date:
            message = personalizer.create_personalized_message(
                MessageType.APPOINTMENT_REMINDER, patient, "sms"
            )
            print(f"SMS: {message['message']}")
            print(f"Langue: {message['language']}")
        
        # Test message de médicament
        if patient.medication_name:
            message = personalizer.create_personalized_message(
                MessageType.MEDICATION_REMINDER, patient, "voice"
            )
            print(f"Voice: {message['message']}")
    
    # Validation de la cohérence
    validation = template_manager.validate_template_consistency()
    print(f"\n=== Validation des Templates ===")
    print(f"Statut: {validation['status']}")
    if validation['issues']:
        for issue in validation['issues']:
            print(f"- {issue}")
    else:
        print("✅ Tous les templates sont cohérents")