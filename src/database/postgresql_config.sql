-- Requêtes de vérification:
SELECT COUNT(*) FROM reminder_types; -- Devrait retourner 3
SELECT name, description FROM reminder_types;
SELECT tablename FROM pg_tables WHERE schemaname = 'public';
