-- Schéma de base de données pour le système de rappels de l'Hôpital Général de Douala
-- Phase 1: Modèles données rappels

-- Table des types de rappels avec templates multilingues
CREATE TABLE reminder_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    template_fr TEXT NOT NULL,
    template_en TEXT NOT NULL,
    template_es TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des rappels avec 12 champs pour planification
CREATE TABLE reminders (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    reminder_type_id INTEGER NOT NULL REFERENCES reminder_types(id),
    title VARCHAR(200) NOT NULL,
    message TEXT,
    scheduled_date DATE NOT NULL,
    scheduled_time TIME NOT NULL,
    timezone VARCHAR(50) DEFAULT 'Africa/Douala',
    priority_level INTEGER DEFAULT 1 CHECK (priority_level BETWEEN 1 AND 5),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'delivered', 'failed', 'cancelled')),
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    last_attempt_at TIMESTAMP,
    sent_at TIMESTAMP,
    delivered_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des préférences de contact pour les patients
CREATE TABLE contact_preferences (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL UNIQUE,
    preferred_language VARCHAR(5) DEFAULT 'fr' CHECK (preferred_language IN ('fr', 'en', 'es')),
    sms_enabled BOOLEAN DEFAULT TRUE,
    email_enabled BOOLEAN DEFAULT FALSE,
    call_enabled BOOLEAN DEFAULT FALSE,
    whatsapp_enabled BOOLEAN DEFAULT FALSE,
    preferred_time_start TIME DEFAULT '08:00:00',
    preferred_time_end TIME DEFAULT '18:00:00',
    timezone VARCHAR(50) DEFAULT 'Africa/Douala',
    do_not_disturb_days TEXT, -- JSON array des jours à éviter
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table des patients (référence)
CREATE TABLE patients (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20),
    email VARCHAR(150),
    date_of_birth DATE,
    gender VARCHAR(10),
    address TEXT,
    emergency_contact VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ajout des contraintes de clés étrangères
ALTER TABLE reminders ADD CONSTRAINT fk_reminders_patient 
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE;

ALTER TABLE contact_preferences ADD CONSTRAINT fk_contact_preferences_patient 
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE;

-- Insertion des 3 types de rappels prédéfinis
INSERT INTO reminder_types (name, description, template_fr, template_en, template_es) VALUES
(
    'appointment',
    'Rappel de rendez-vous médical',
    'Bonjour {patient_name}, nous vous rappelons votre rendez-vous le {date} à {time} avec le Dr {doctor_name}. Merci de confirmer votre présence.',
    'Hello {patient_name}, this is a reminder of your appointment on {date} at {time} with Dr {doctor_name}. Please confirm your attendance.',
    'Hola {patient_name}, le recordamos su cita el {date} a las {time} con el Dr {doctor_name}. Por favor confirme su asistencia.'
),
(
    'medication',
    'Rappel de prise de médicaments',
    'Bonjour {patient_name}, il est temps de prendre votre médicament: {medication_name}. Dosage: {dosage}. N\'oubliez pas de suivre les instructions de votre médecin.',
    'Hello {patient_name}, it\'s time to take your medication: {medication_name}. Dosage: {dosage}. Don\'t forget to follow your doctor\'s instructions.',
    'Hola {patient_name}, es hora de tomar su medicamento: {medication_name}. Dosis: {dosage}. No olvide seguir las instrucciones de su médico.'
),
(
    'follow_up',
    'Rappel de suivi médical',
    'Bonjour {patient_name}, votre suivi médical est prévu le {date}. Veuillez contacter l\'hôpital pour confirmer ou reprogrammer si nécessaire.',
    'Hello {patient_name}, your medical follow-up is scheduled for {date}. Please contact the hospital to confirm or reschedule if necessary.',
    'Hola {patient_name}, su seguimiento médico está programado para el {date}. Por favor contacte al hospital para confirmar o reprogramar si es necesario.'
);

-- Création des index pour optimiser les requêtes de planification
CREATE INDEX idx_reminders_scheduled_date ON reminders(scheduled_date);
CREATE INDEX idx_reminders_status ON reminders(status);
CREATE INDEX idx_reminders_patient_id ON reminders(patient_id);
CREATE INDEX idx_reminders_type_id ON reminders(reminder_type_id);
CREATE INDEX idx_reminders_scheduled_datetime ON reminders(scheduled_date, scheduled_time);
CREATE INDEX idx_reminders_priority_status ON reminders(priority_level, status);
CREATE INDEX idx_contact_preferences_patient ON contact_preferences(patient_id);
CREATE INDEX idx_patients_phone ON patients(phone_number);
CREATE INDEX idx_patients_email ON patients(email);

-- Index composé pour les requêtes de planification complexes
CREATE INDEX idx_reminders_planning ON reminders(scheduled_date, scheduled_time, status, priority_level);

-- Triggers pour mettre à jour automatiquement updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_reminder_types_updated_at BEFORE UPDATE ON reminder_types
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_reminders_updated_at BEFORE UPDATE ON reminders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_contact_preferences_updated_at BEFORE UPDATE ON contact_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_patients_updated_at BEFORE UPDATE ON patients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();