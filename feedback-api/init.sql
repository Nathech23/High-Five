-- Initialize DGH Feedback Database
-- This script creates initial data for the system

-- Insert default departments
INSERT INTO departments (name, code, created_at) VALUES
('Urgences', 'URG', NOW()),
('Cardiologie', 'CARD', NOW()),
('Pédiatrie', 'PED', NOW()),
('Médecine Générale', 'MED', NOW()),
('Chirurgie', 'CHIR', NOW())
ON CONFLICT (code) DO NOTHING;

-- Insert default reminder types
INSERT INTO reminder_types (
    name, 
    description, 
    template_fr, 
    template_en, 
    template_douala,
    is_active, 
    created_at
) VALUES
(
    'appointment_reminder',
    'Rappel de rendez-vous médical',
    'Bonjour {patient_name}, vous avez un rendez-vous le {date} à {time} au département {department}. Merci de confirmer votre présence.',
    'Hello {patient_name}, you have an appointment on {date} at {time} in {department} department. Please confirm your attendance.',
    'Mbolo {patient_name}, o teni rendez-vous na {date} na {time} na département {department}. Boya confirm attendance na wo.',
    true,
    NOW()
),
(
    'medication_reminder',
    'Rappel de prise de médicament',
    'Bonjour {patient_name}, n''oubliez pas de prendre votre médicament {medication} à {time}.',
    'Hello {patient_name}, don''t forget to take your medication {medication} at {time}.',
    'Mbolo {patient_name}, boya oubli te prendre médicament {medication} na {time}.',
    true,
    NOW()
),
(
    'follow_up_reminder',
    'Rappel de suivi médical',
    'Bonjour {patient_name}, il est temps de programmer votre suivi médical. Contactez-nous au +237 XXX XXX XXX.',
    'Hello {patient_name}, it''s time to schedule your medical follow-up. Contact us at +237 XXX XXX XXX.',
    'Mbolo {patient_name}, temps don reach weh o doit programmer suivi médical na wo. Téléphone nous na +237 XXX XXX XXX.',
    true,
    NOW()
)
ON CONFLICT (name) DO NOTHING;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_patients_department ON patients(department_id);
CREATE INDEX IF NOT EXISTS idx_patients_language ON patients(preferred_language);
CREATE INDEX IF NOT EXISTS idx_feedbacks_patient ON feedbacks(patient_id);
CREATE INDEX IF NOT EXISTS idx_feedbacks_department ON feedbacks(department_id);
CREATE INDEX IF NOT EXISTS idx_feedbacks_created_at ON feedbacks(created_at);
CREATE INDEX IF NOT EXISTS idx_feedbacks_rating ON feedbacks(rating);
CREATE INDEX IF NOT EXISTS idx_feedbacks_urgent ON feedbacks(is_urgent);
CREATE INDEX IF NOT EXISTS idx_feedbacks_status ON feedbacks(status);
CREATE INDEX IF NOT EXISTS idx_feedbacks_language ON feedbacks(language);
CREATE INDEX IF NOT EXISTS idx_feedback_analysis_feedback ON feedback_analysis(feedback_id);
CREATE INDEX IF NOT EXISTS idx_reminders_patient ON reminders(patient_id);
CREATE INDEX IF NOT EXISTS idx_reminders_scheduled_date ON reminders(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_reminders_status ON reminders(status);

-- Insert sample patients (20 patients)
INSERT INTO patients (first_name, last_name, phone, email, preferred_language, department_id, created_at) VALUES
('Marie', 'Nguema', '+237670123456', 'marie.nguema@email.cm', 'fr', 1, NOW()),
('Jean', 'Mballa', '+237680234567', 'jean.mballa@email.cm', 'fr', 2, NOW()),
('Sarah', 'Eto''o', '+237690345678', 'sarah.etoo@email.cm', 'en', 3, NOW()),
('Paul', 'Ndoumbe', '+237650456789', 'paul.ndoumbe@email.cm', 'fr', 4, NOW()),
('Grace', 'Kom', '+237675567890', 'grace.kom@email.cm', 'douala', 5, NOW()),
('Michel', 'Biya', '+237685678901', 'michel.biya@email.cm', 'fr', 1, NOW()),
('Fatima', 'Ahidjo', '+237695789012', 'fatima.ahidjo@email.cm', 'en', 2, NOW()),
('André', 'Fouda', '+237655890123', 'andre.fouda@email.cm', 'fr', 3, NOW()),
('Claire', 'Muna', '+237676901234', 'claire.muna@email.cm', 'bassa', 4, NOW()),
('Joseph', 'Oyono', '+237687012345', 'joseph.oyono@email.cm', 'fr', 5, NOW()),
('Aminata', 'Ba', '+237698123456', 'aminata.ba@email.cm', 'fr', 1, NOW()),
('Pierre', 'Tchoungui', '+237659234567', 'pierre.tchoungui@email.cm', 'ewondo', 2, NOW()),
('Lydie', 'Ebogo', '+237679345678', 'lydie.ebogo@email.cm', 'fr', 3, NOW()),
('Roger', 'Milla', '+237689456789', 'roger.milla@email.cm', 'en', 4, NOW()),
('Esther', 'Achu', '+237699567890', 'esther.achu@email.cm', 'fr', 5, NOW()),
('Samuel', 'Kotto', '+237651678901', 'samuel.kotto@email.cm', 'douala', 1, NOW()),
('Nadège', 'Mbondo', '+237681789012', 'nadege.mbondo@email.cm', 'fr', 2, NOW()),
('Francis', 'Nkea', '+237691890123', 'francis.nkea@email.cm', 'bassa', 3, NOW()),
('Berthe', 'Abena', '+237652901234', 'berthe.abena@email.cm', 'fr', 4, NOW()),
('Honoré', 'Essomba', '+237682012345', 'honore.essomba@email.cm', 'ewondo', 5, NOW())
ON CONFLICT DO NOTHING;

-- Insert sample feedbacks (20 feedbacks)
INSERT INTO feedbacks (patient_id, department_id, rating, feedback_text, language, wait_time_min, resolution_time_min, is_urgent, status, created_at) VALUES
(1, 1, 4.5, 'Service très rapide aux urgences. Le personnel était très professionnel et attentionné.', 'fr', 15, 45, false, 'reviewed', NOW() - INTERVAL '2 days'),
(2, 2, 5.0, 'Excellent suivi en cardiologie. Le docteur a pris le temps de bien expliquer mon état.', 'fr', 10, 60, false, 'resolved', NOW() - INTERVAL '1 day'),
(3, 3, 3.0, 'The pediatric department was okay but the waiting time was too long for my child.', 'en', 120, 30, false, 'pending', NOW() - INTERVAL '3 hours'),
(4, 4, 4.0, 'Bonne consultation en médecine générale. Le médecin était à l''écoute.', 'fr', 30, 45, false, 'reviewed', NOW() - INTERVAL '5 days'),
(5, 5, 2.0, 'Ma mbele na service na chirurgie. Ba nye te mboki te nga na mokolo mua surgery.', 'douala', 180, 15, true, 'pending', NOW() - INTERVAL '1 hour'),
(6, 1, 1.5, 'Très déçu du service. Personnel impoli et temps d''attente excessif. Situation inacceptable!', 'fr', 240, 20, true, 'pending', NOW() - INTERVAL '30 minutes'),
(7, 2, 4.5, 'Great cardiac care. The staff was very professional and the equipment is modern.', 'en', 25, 90, false, 'resolved', NOW() - INTERVAL '6 days'),
(8, 3, 5.0, 'Parfait pour les enfants. L''équipe pédiatrique est formidable avec les petits.', 'fr', 20, 40, false, 'resolved', NOW() - INTERVAL '4 days'),
(9, 4, 3.5, 'Makuku ma service ma bon petit, kasi ba ndjoni te na temps.', 'bassa', 90, 35, false, 'reviewed', NOW() - INTERVAL '2 days'),
(10, 5, 4.0, 'Chirurgie bien réalisée. Suivi post-opératoire satisfaisant.', 'fr', 45, 120, false, 'resolved', NOW() - INTERVAL '7 days'),
(11, 1, 2.5, 'Service acceptable mais peut être amélioré. Manque de communication.', 'fr', 60, 25, false, 'pending', NOW() - INTERVAL '1 day'),
(12, 2, 5.0, 'Minga mbele te na cardiologie. Ba salongo ba nye te professionnels mingi.', 'ewondo', 15, 75, false, 'resolved', NOW() - INTERVAL '3 days'),
(13, 3, 4.0, 'Bon service en pédiatrie. Ma fille était bien prise en charge.', 'fr', 35, 50, false, 'reviewed', NOW() - INTERVAL '8 hours'),
(14, 4, 3.0, 'Average service in general medicine. Could be better organized.', 'en', 75, 40, false, 'pending', NOW() - INTERVAL '2 hours'),
(15, 5, 4.5, 'Très satisfaite de l''intervention chirurgicale. Équipe compétente.', 'fr', 30, 180, false, 'resolved', NOW() - INTERVAL '10 days'),
(16, 1, 1.0, 'Urgence ma nye te catastrophe! Ba nye te na retard mingi, nga na douleur terrible!', 'douala', 300, 10, true, 'pending', NOW() - INTERVAL '15 minutes'),
(17, 2, 4.0, 'Bon diagnostic en cardiologie. Médecin compétent et équipement moderne.', 'fr', 40, 80, false, 'reviewed', NOW() - INTERVAL '5 days'),
(18, 3, 3.5, 'Hihi bana ba nye te ba bon, kasi service na nye te petit retard.', 'bassa', 50, 45, false, 'pending', NOW() - INTERVAL '6 hours'),
(19, 4, 5.0, 'Excellente consultation. Médecin très professionnel et diagnostic précis.', 'fr', 20, 55, false, 'resolved', NOW() - INTERVAL '9 days'),
(20, 5, 4.0, 'Surgery na nye te mboa. Ba doctor ba salongo ba nye te na mbele.', 'ewondo', 60, 150, false, 'resolved', NOW() - INTERVAL '12 days')
ON CONFLICT DO NOTHING;