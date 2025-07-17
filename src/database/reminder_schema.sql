-- Schéma de base de données pour le système de rappels
-- Phase 4 - API rappels et planification

-- Table principale des rappels
CREATE TABLE IF NOT EXISTS reminders (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL,
    reminder_type VARCHAR(50) NOT NULL CHECK (reminder_type IN (
        'appointment_reminder', 'medication_reminder', 'health_tip', 
        'emergency_alert', 'follow_up'
    )),
    delivery_method VARCHAR(20) NOT NULL CHECK (delivery_method IN ('sms', 'voice', 'both')),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending', 'scheduled', 'sent', 'delivered', 'failed', 'cancelled', 'retry'
    )),
    priority VARCHAR(20) NOT NULL DEFAULT 'normal' CHECK (priority IN (
        'low', 'normal', 'high', 'urgent'
    )),
    scheduled_time TIMESTAMP NOT NULL,
    custom_message TEXT,
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP,
    delivered_at TIMESTAMP,
    
    -- Retry logic
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    retry_interval INTEGER DEFAULT 300, -- secondes
    
    -- Twilio integration
    twilio_sid VARCHAR(100),
    error_message TEXT,
    
    -- Contraintes
    CONSTRAINT fk_reminder_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    CONSTRAINT chk_scheduled_future CHECK (scheduled_time > created_at),
    CONSTRAINT chk_retry_count CHECK (retry_count >= 0),
    CONSTRAINT chk_max_retries CHECK (max_retries >= 0),
    CONSTRAINT chk_retry_interval CHECK (retry_interval > 0)
);

-- Index pour les performances
CREATE INDEX IF NOT EXISTS idx_reminders_patient_id ON reminders(patient_id);
CREATE INDEX IF NOT EXISTS idx_reminders_status ON reminders(status);
CREATE INDEX IF NOT EXISTS idx_reminders_scheduled_time ON reminders(scheduled_time);
CREATE INDEX IF NOT EXISTS idx_reminders_twilio_sid ON reminders(twilio_sid);
CREATE INDEX IF NOT EXISTS idx_reminders_created_at ON reminders(created_at);

-- Index composé pour les requêtes fréquentes
CREATE INDEX IF NOT EXISTS idx_reminders_status_scheduled ON reminders(status, scheduled_time);
CREATE INDEX IF NOT EXISTS idx_reminders_patient_status ON reminders(patient_id, status);

-- Table pour l'historique des statuts (tracking détaillé)
CREATE TABLE IF NOT EXISTS reminder_status_history (
    id SERIAL PRIMARY KEY,
    reminder_id INTEGER NOT NULL,
    old_status VARCHAR(20),
    new_status VARCHAR(20) NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    changed_by VARCHAR(100), -- système, webhook, admin, etc.
    details JSONB DEFAULT '{}',
    
    CONSTRAINT fk_status_history_reminder FOREIGN KEY (reminder_id) REFERENCES reminders(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_status_history_reminder_id ON reminder_status_history(reminder_id);
CREATE INDEX IF NOT EXISTS idx_status_history_changed_at ON reminder_status_history(changed_at);

-- Table pour les métriques et statistiques
CREATE TABLE IF NOT EXISTS reminder_metrics (
    id SERIAL PRIMARY KEY,
    date_recorded DATE NOT NULL DEFAULT CURRENT_DATE,
    reminder_type VARCHAR(50) NOT NULL,
    delivery_method VARCHAR(20) NOT NULL,
    
    -- Compteurs
    total_created INTEGER DEFAULT 0,
    total_sent INTEGER DEFAULT 0,
    total_delivered INTEGER DEFAULT 0,
    total_failed INTEGER DEFAULT 0,
    total_cancelled INTEGER DEFAULT 0,
    
    -- Métriques de performance
    avg_delivery_time_seconds DECIMAL(10,2), -- temps moyen de livraison
    delivery_rate_percent DECIMAL(5,2), -- taux de livraison
    retry_rate_percent DECIMAL(5,2), -- taux de retry
    
    -- Métadonnées
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uk_metrics_date_type_method UNIQUE (date_recorded, reminder_type, delivery_method)
);

CREATE INDEX IF NOT EXISTS idx_metrics_date ON reminder_metrics(date_recorded);
CREATE INDEX IF NOT EXISTS idx_metrics_type ON reminder_metrics(reminder_type);

-- Vue pour les statistiques en temps réel
CREATE OR REPLACE VIEW reminder_stats_view AS
SELECT 
    COUNT(*) as total_reminders,
    COUNT(*) FILTER (WHERE status = 'pending') as pending,
    COUNT(*) FILTER (WHERE status = 'scheduled') as scheduled,
    COUNT(*) FILTER (WHERE status = 'sent') as sent,
    COUNT(*) FILTER (WHERE status = 'delivered') as delivered,
    COUNT(*) FILTER (WHERE status = 'failed') as failed,
    COUNT(*) FILTER (WHERE status = 'cancelled') as cancelled,
    COUNT(*) FILTER (WHERE status = 'retry') as retry,
    
    -- Taux de livraison
    CASE 
        WHEN COUNT(*) FILTER (WHERE status IN ('sent', 'delivered')) > 0 THEN
            ROUND(
                (COUNT(*) FILTER (WHERE status = 'delivered')::DECIMAL / 
                 COUNT(*) FILTER (WHERE status IN ('sent', 'delivered'))) * 100, 2
            )
        ELSE 0
    END as delivery_rate_percent,
    
    -- Temps moyen de livraison (en secondes)
    AVG(
        EXTRACT(EPOCH FROM (delivered_at - sent_at))
    ) FILTER (WHERE delivered_at IS NOT NULL AND sent_at IS NOT NULL) as avg_delivery_time_seconds
    
FROM reminders
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'; -- Stats des 30 derniers jours

-- Vue pour les rappels dus (pour le worker)
CREATE OR REPLACE VIEW due_reminders_view AS
SELECT 
    r.*,
    p.name as patient_name,
    p.phone as patient_phone,
    p.preferred_language as patient_language
FROM reminders r
JOIN patients p ON r.patient_id = p.id
WHERE 
    r.status IN ('scheduled', 'retry')
    AND r.scheduled_time <= CURRENT_TIMESTAMP
    AND (r.retry_count < r.max_retries OR r.status = 'scheduled')
ORDER BY 
    CASE r.priority 
        WHEN 'urgent' THEN 1
        WHEN 'high' THEN 2
        WHEN 'normal' THEN 3
        WHEN 'low' THEN 4
    END,
    r.scheduled_time ASC;

-- Fonction pour mettre à jour automatiquement updated_at
CREATE OR REPLACE FUNCTION update_reminder_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger pour updated_at
DROP TRIGGER IF EXISTS trigger_update_reminder_updated_at ON reminders;
CREATE TRIGGER trigger_update_reminder_updated_at
    BEFORE UPDATE ON reminders
    FOR EACH ROW
    EXECUTE FUNCTION update_reminder_updated_at();

-- Fonction pour enregistrer les changements de statut
CREATE OR REPLACE FUNCTION log_reminder_status_change()
RETURNS TRIGGER AS $$
BEGIN
    -- Enregistrer le changement de statut si différent
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO reminder_status_history (reminder_id, old_status, new_status, changed_by, details)
        VALUES (
            NEW.id, 
            OLD.status, 
            NEW.status, 
            'system',
            jsonb_build_object(
                'retry_count', NEW.retry_count,
                'twilio_sid', NEW.twilio_sid,
                'error_message', NEW.error_message
            )
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger pour l'historique des statuts
DROP TRIGGER IF EXISTS trigger_log_reminder_status_change ON reminders;
CREATE TRIGGER trigger_log_reminder_status_change
    AFTER UPDATE ON reminders
    FOR EACH ROW
    EXECUTE FUNCTION log_reminder_status_change();

-- Fonction pour nettoyer les anciens rappels (maintenance)
CREATE OR REPLACE FUNCTION cleanup_old_reminders(days_to_keep INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Supprimer les rappels terminés (delivered, failed, cancelled) plus anciens que X jours
    DELETE FROM reminders 
    WHERE 
        status IN ('delivered', 'failed', 'cancelled')
        AND updated_at < CURRENT_TIMESTAMP - (days_to_keep || ' days')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Nettoyer aussi l'historique des statuts orphelins
    DELETE FROM reminder_status_history 
    WHERE reminder_id NOT IN (SELECT id FROM reminders);
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Fonction pour calculer les métriques quotidiennes
CREATE OR REPLACE FUNCTION calculate_daily_metrics(target_date DATE DEFAULT CURRENT_DATE)
RETURNS VOID AS $$
DECLARE
    rec RECORD;
BEGIN
    -- Calculer les métriques pour chaque combinaison type/méthode
    FOR rec IN 
        SELECT DISTINCT reminder_type, delivery_method 
        FROM reminders 
        WHERE DATE(created_at) = target_date
    LOOP
        INSERT INTO reminder_metrics (
            date_recorded, reminder_type, delivery_method,
            total_created, total_sent, total_delivered, total_failed, total_cancelled,
            avg_delivery_time_seconds, delivery_rate_percent, retry_rate_percent
        )
        SELECT 
            target_date,
            rec.reminder_type,
            rec.delivery_method,
            COUNT(*) as total_created,
            COUNT(*) FILTER (WHERE status IN ('sent', 'delivered')) as total_sent,
            COUNT(*) FILTER (WHERE status = 'delivered') as total_delivered,
            COUNT(*) FILTER (WHERE status = 'failed') as total_failed,
            COUNT(*) FILTER (WHERE status = 'cancelled') as total_cancelled,
            AVG(EXTRACT(EPOCH FROM (delivered_at - sent_at))) FILTER (WHERE delivered_at IS NOT NULL AND sent_at IS NOT NULL),
            CASE 
                WHEN COUNT(*) FILTER (WHERE status IN ('sent', 'delivered')) > 0 THEN
                    (COUNT(*) FILTER (WHERE status = 'delivered')::DECIMAL / 
                     COUNT(*) FILTER (WHERE status IN ('sent', 'delivered'))) * 100
                ELSE 0
            END,
            CASE 
                WHEN COUNT(*) > 0 THEN
                    (COUNT(*) FILTER (WHERE retry_count > 0)::DECIMAL / COUNT(*)) * 100
                ELSE 0
            END
        FROM reminders 
        WHERE 
            DATE(created_at) = target_date
            AND reminder_type = rec.reminder_type
            AND delivery_method = rec.delivery_method
        ON CONFLICT (date_recorded, reminder_type, delivery_method) 
        DO UPDATE SET
            total_created = EXCLUDED.total_created,
            total_sent = EXCLUDED.total_sent,
            total_delivered = EXCLUDED.total_delivered,
            total_failed = EXCLUDED.total_failed,
            total_cancelled = EXCLUDED.total_cancelled,
            avg_delivery_time_seconds = EXCLUDED.avg_delivery_time_seconds,
            delivery_rate_percent = EXCLUDED.delivery_rate_percent,
            retry_rate_percent = EXCLUDED.retry_rate_percent,
            updated_at = CURRENT_TIMESTAMP;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Données de test pour les rappels
INSERT INTO reminders (patient_id, reminder_type, delivery_method, scheduled_time, priority, custom_message, metadata) VALUES
(1, 'appointment_reminder', 'sms', CURRENT_TIMESTAMP + INTERVAL '1 hour', 'normal', NULL, '{"test": true}'),
(2, 'medication_reminder', 'voice', CURRENT_TIMESTAMP + INTERVAL '2 hours', 'high', 'N''oubliez pas votre médicament', '{"medication": "Paracétamol"}'),
(3, 'health_tip', 'both', CURRENT_TIMESTAMP + INTERVAL '1 day', 'low', NULL, '{"tip_category": "nutrition"}'),
(1, 'follow_up', 'sms', CURRENT_TIMESTAMP + INTERVAL '3 days', 'normal', 'Contrôle post-consultation', '{"consultation_id": 123}');

-- Commentaires pour la documentation
COMMENT ON TABLE reminders IS 'Table principale des rappels programmés';
COMMENT ON COLUMN reminders.retry_interval IS 'Intervalle entre les tentatives de retry en secondes';
COMMENT ON COLUMN reminders.metadata IS 'Métadonnées JSON pour informations additionnelles';
COMMENT ON TABLE reminder_status_history IS 'Historique des changements de statut pour audit';
COMMENT ON TABLE reminder_metrics IS 'Métriques quotidiennes pour reporting et analyse';
COMMENT ON VIEW reminder_stats_view IS 'Vue temps réel des statistiques des rappels';
COMMENT ON VIEW due_reminders_view IS 'Vue des rappels dus pour le worker de traitement';