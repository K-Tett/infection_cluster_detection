-- =============================================
-- Database Initialization Script
-- Initialize infection cluster detection database
-- =============================================

-- Create database (if running as superuser)
-- CREATE DATABASE infection_cluster_db WITH ENCODING='UTF8';

-- Connect to the database
-- \c infection_cluster_db;

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Execute the main schema
\i schemas.sql

-- =============================================
-- SAMPLE DATA INSERTION (for testing)
-- =============================================

-- Insert sample patients
INSERT INTO infection_cluster.patients (patient_id) VALUES
('PAT001'), ('PAT002'), ('PAT003'), ('PAT004'), ('PAT005'),
('PAT006'), ('PAT007'), ('PAT008'), ('PAT009'), ('PAT010')
ON CONFLICT (patient_id) DO NOTHING;

-- Insert sample transfers
INSERT INTO infection_cluster.transfers (transfer_id, patient_id, ward_in_time, ward_out_time, location) VALUES
('TRF001', 'PAT001', '2025-01-01', '2025-01-05', 'ICU'),
('TRF002', 'PAT002', '2025-01-02', '2025-01-06', 'ICU'),
('TRF003', 'PAT003', '2025-01-03', '2025-01-07', 'Ward-A'),
('TRF004', 'PAT004', '2025-01-04', NULL, 'ICU'),
('TRF005', 'PAT005', '2025-01-05', '2025-01-10', 'Ward-B'),
('TRF006', 'PAT001', '2025-01-06', '2025-01-12', 'Ward-A'),
('TRF007', 'PAT002', '2025-01-07', '2025-01-11', 'Ward-A'),
('TRF008', 'PAT006', '2025-01-08', '2025-01-15', 'Emergency'),
('TRF009', 'PAT007', '2025-01-09', '2025-01-13', 'ICU'),
('TRF010', 'PAT008', '2025-01-10', NULL, 'Ward-B')
ON CONFLICT (transfer_id) DO NOTHING;

-- Insert sample microbiology tests
INSERT INTO infection_cluster.microbiology (test_id, patient_id, collection_date, infection, result) VALUES
('TST001', 'PAT001', '2025-01-03', 'CRE', 'positive'),
('TST002', 'PAT002', '2025-01-04', 'CRE', 'positive'),
('TST003', 'PAT003', '2025-01-05', 'MRSA', 'negative'),
('TST004', 'PAT004', '2025-01-06', 'CRE', 'positive'),
('TST005', 'PAT005', '2025-01-07', 'CDI', 'positive'),
('TST006', 'PAT001', '2025-01-09', 'MRSA', 'positive'),
('TST007', 'PAT002', '2025-01-10', 'CDI', 'negative'),
('TST008', 'PAT006', '2025-01-11', 'CRE', 'negative'),
('TST009', 'PAT007', '2025-01-12', 'CRE', 'positive'),
('TST010', 'PAT008', '2025-01-13', 'MRSA', 'positive')
ON CONFLICT (test_id) DO NOTHING;

-- Refresh materialized view with sample data
REFRESH MATERIALIZED VIEW infection_cluster.patient_infection_timeline;

-- =============================================
-- VERIFY INSTALLATION
-- =============================================

-- Insert verification log
INSERT INTO infection_cluster.system_logs (action, details) 
VALUES ('database_initialization', 'Database schema and sample data initialized successfully');

-- Display summary
SELECT 
    'Database initialized successfully' as status,
    (SELECT COUNT(*) FROM infection_cluster.patients) as patients_count,
    (SELECT COUNT(*) FROM infection_cluster.transfers) as transfers_count,
    (SELECT COUNT(*) FROM infection_cluster.microbiology) as tests_count,
    (SELECT COUNT(*) FROM infection_cluster.patient_infection_timeline) as timeline_records;

-- NOTE: Initialization script includes sample data for immediate testing
-- NOTE: Can be run in Docker container or standalone PostgreSQL instance