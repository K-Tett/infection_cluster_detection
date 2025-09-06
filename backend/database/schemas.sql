-- =============================================
-- Infection Cluster Detection Database Schema
-- PostgreSQL DDL for medical data with ACID compliance
-- =============================================

-- Create database schema
CREATE SCHEMA IF NOT EXISTS infection_cluster;
SET search_path TO infection_cluster, public;

-- =============================================
-- PATIENTS TABLE (Reference table for foreign keys)
-- =============================================
CREATE TABLE patients (
    patient_id VARCHAR(50) PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE patients IS 'Reference table for patient identifiers to ensure referential integrity';
COMMENT ON COLUMN patients.patient_id IS 'Unique patient identifier used across transfers and microbiology data';

-- =============================================
-- TRANSFERS TABLE (from transfers.csv)
-- =============================================
CREATE TABLE transfers (
    transfer_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL,
    ward_in_time DATE NOT NULL,
    ward_out_time DATE,
    location VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT fk_transfers_patient FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    CONSTRAINT chk_transfer_dates CHECK (ward_out_time IS NULL OR ward_out_time >= ward_in_time),
    CONSTRAINT chk_transfer_id_not_empty CHECK (LENGTH(TRIM(transfer_id)) > 0),
    CONSTRAINT chk_patient_id_not_empty CHECK (LENGTH(TRIM(patient_id)) > 0),
    CONSTRAINT chk_location_not_empty CHECK (LENGTH(TRIM(location)) > 0)
);

COMMENT ON TABLE transfers IS 'Patient ward transfers data for spatial-temporal cluster analysis';
COMMENT ON COLUMN transfers.transfer_id IS 'Unique transfer identifier (primary key)';
COMMENT ON COLUMN transfers.patient_id IS 'Patient identifier (foreign key to patients table)';
COMMENT ON COLUMN transfers.ward_in_time IS 'Date of admission to ward';
COMMENT ON COLUMN transfers.ward_out_time IS 'Date of discharge from ward (NULL if still admitted)';
COMMENT ON COLUMN transfers.location IS 'Ward or location name where patient was admitted';

-- =============================================
-- MICROBIOLOGY TABLE (from microbiology.csv)
-- =============================================
CREATE TABLE microbiology (
    test_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL,
    collection_date DATE NOT NULL,
    infection VARCHAR(100) NOT NULL,
    result VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT fk_microbiology_patient FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    CONSTRAINT chk_test_result CHECK (result IN ('positive', 'negative')),
    CONSTRAINT chk_test_id_not_empty CHECK (LENGTH(TRIM(test_id)) > 0),
    CONSTRAINT chk_patient_id_not_empty CHECK (LENGTH(TRIM(patient_id)) > 0),
    CONSTRAINT chk_infection_not_empty CHECK (LENGTH(TRIM(infection)) > 0),
    CONSTRAINT chk_collection_date_not_future CHECK (collection_date <= CURRENT_DATE)
);

COMMENT ON TABLE microbiology IS 'Microbiology test results for infection detection and cluster analysis';
COMMENT ON COLUMN microbiology.test_id IS 'Unique test identifier (primary key)';
COMMENT ON COLUMN microbiology.patient_id IS 'Patient identifier (foreign key to patients table)';
COMMENT ON COLUMN microbiology.collection_date IS 'Date when the test sample was collected';
COMMENT ON COLUMN microbiology.infection IS 'Type of infection being tested (e.g., CRE, MRSA, CDI)';
COMMENT ON COLUMN microbiology.result IS 'Test result: positive or negative';

-- =============================================
-- PERFORMANCE INDEXES FOR CLUSTER DETECTION
-- =============================================

-- Transfers table indexes
CREATE INDEX idx_transfers_patient_id ON transfers(patient_id);
CREATE INDEX idx_transfers_location ON transfers(location);
CREATE INDEX idx_transfers_ward_in_time ON transfers(ward_in_time);
CREATE INDEX idx_transfers_ward_out_time ON transfers(ward_out_time) WHERE ward_out_time IS NOT NULL;
CREATE INDEX idx_transfers_date_range ON transfers(ward_in_time, ward_out_time);
CREATE INDEX idx_transfers_location_dates ON transfers(location, ward_in_time, ward_out_time);

-- Microbiology table indexes
CREATE INDEX idx_microbiology_patient_id ON microbiology(patient_id);
CREATE INDEX idx_microbiology_collection_date ON microbiology(collection_date);
CREATE INDEX idx_microbiology_infection ON microbiology(infection);
CREATE INDEX idx_microbiology_result ON microbiology(result);
CREATE INDEX idx_microbiology_positive_tests ON microbiology(infection, collection_date) WHERE result = 'positive';
CREATE INDEX idx_microbiology_patient_infection ON microbiology(patient_id, infection, result);

-- Composite indexes for common cluster detection queries
CREATE INDEX idx_transfers_spatial_temporal ON transfers(location, patient_id, ward_in_time, ward_out_time);
CREATE INDEX idx_microbiology_temporal_infection ON microbiology(collection_date, infection, patient_id) WHERE result = 'positive';

-- =============================================
-- MATERIALIZED VIEW FOR CLUSTER DETECTION
-- =============================================
CREATE MATERIALIZED VIEW patient_infection_timeline AS
SELECT 
    m.patient_id,
    m.infection,
    m.collection_date as infection_date,
    t.location,
    t.ward_in_time,
    t.ward_out_time,
    -- Calculate if infection occurred during transfer
    CASE 
        WHEN m.collection_date >= t.ward_in_time 
        AND (t.ward_out_time IS NULL OR m.collection_date <= t.ward_out_time)
        THEN true 
        ELSE false 
    END as infection_during_stay
FROM microbiology m
JOIN transfers t ON m.patient_id = t.patient_id
WHERE m.result = 'positive'
ORDER BY m.collection_date, m.infection, t.location;

COMMENT ON MATERIALIZED VIEW patient_infection_timeline IS 'Optimized view combining positive infections with patient location data for cluster detection';

-- Create index on materialized view
CREATE INDEX idx_patient_infection_timeline_infection_date ON patient_infection_timeline(infection, infection_date);
CREATE INDEX idx_patient_infection_timeline_location ON patient_infection_timeline(location, infection_date);
CREATE INDEX idx_patient_infection_timeline_during_stay ON patient_infection_timeline(infection, location, infection_date) WHERE infection_during_stay = true;

-- =============================================
-- REFRESH FUNCTION FOR MATERIALIZED VIEW
-- =============================================
CREATE OR REPLACE FUNCTION refresh_patient_infection_timeline()
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY patient_infection_timeline;
    
    -- Log refresh activity
    INSERT INTO system_logs (action, timestamp, details) 
    VALUES ('materialized_view_refresh', CURRENT_TIMESTAMP, 'patient_infection_timeline refreshed')
    ON CONFLICT DO NOTHING;
END;
$$;

-- =============================================
-- SYSTEM LOGS TABLE (for audit trail)
-- =============================================
CREATE TABLE system_logs (
    log_id BIGSERIAL PRIMARY KEY,
    action VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    details TEXT,
    user_id VARCHAR(50),
    
    CONSTRAINT chk_action_not_empty CHECK (LENGTH(TRIM(action)) > 0)
);

COMMENT ON TABLE system_logs IS 'System activity logs for audit trail in medical environment';

CREATE INDEX idx_system_logs_timestamp ON system_logs(timestamp);
CREATE INDEX idx_system_logs_action ON system_logs(action);

-- =============================================
-- UPDATE TRIGGERS FOR AUDIT TRAIL
-- =============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to tables
CREATE TRIGGER update_patients_updated_at BEFORE UPDATE ON patients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_transfers_updated_at BEFORE UPDATE ON transfers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_microbiology_updated_at BEFORE UPDATE ON microbiology
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================
-- HELPER FUNCTIONS FOR CLUSTER DETECTION
-- =============================================

-- Function to find spatial-temporal overlaps
CREATE OR REPLACE FUNCTION find_location_overlaps(
    target_location VARCHAR(100),
    start_date DATE,
    end_date DATE
)
RETURNS TABLE (
    patient_id VARCHAR(50),
    location VARCHAR(100),
    overlap_start DATE,
    overlap_end DATE,
    overlap_days INTEGER
)
LANGUAGE sql
AS $$
    SELECT 
        t.patient_id,
        t.location,
        GREATEST(t.ward_in_time, start_date) as overlap_start,
        LEAST(COALESCE(t.ward_out_time, CURRENT_DATE), end_date) as overlap_end,
        LEAST(COALESCE(t.ward_out_time, CURRENT_DATE), end_date) - GREATEST(t.ward_in_time, start_date) + 1 as overlap_days
    FROM transfers t
    WHERE t.location = target_location
    AND t.ward_in_time <= end_date
    AND (t.ward_out_time IS NULL OR t.ward_out_time >= start_date)
    AND GREATEST(t.ward_in_time, start_date) <= LEAST(COALESCE(t.ward_out_time, CURRENT_DATE), end_date);
$$;

COMMENT ON FUNCTION find_location_overlaps IS 'Find all patients with overlapping stays in a specific location during a date range';

-- Function to get infection statistics by location
CREATE OR REPLACE FUNCTION get_infection_stats_by_location(
    infection_type VARCHAR(100) DEFAULT NULL,
    start_date DATE DEFAULT NULL,
    end_date DATE DEFAULT NULL
)
RETURNS TABLE (
    location VARCHAR(100),
    total_patients BIGINT,
    positive_cases BIGINT,
    infection_rate NUMERIC(5,2)
)
LANGUAGE sql
AS $$
    SELECT 
        pit.location,
        COUNT(DISTINCT pit.patient_id) as total_patients,
        COUNT(DISTINCT CASE WHEN pit.infection_during_stay THEN pit.patient_id END) as positive_cases,
        ROUND(
            (COUNT(DISTINCT CASE WHEN pit.infection_during_stay THEN pit.patient_id END)::NUMERIC / 
             NULLIF(COUNT(DISTINCT pit.patient_id), 0)) * 100, 2
        ) as infection_rate
    FROM patient_infection_timeline pit
    WHERE (infection_type IS NULL OR pit.infection = infection_type)
    AND (start_date IS NULL OR pit.infection_date >= start_date)
    AND (end_date IS NULL OR pit.infection_date <= end_date)
    GROUP BY pit.location
    ORDER BY infection_rate DESC, positive_cases DESC;
$$;

COMMENT ON FUNCTION get_infection_stats_by_location IS 'Get infection statistics grouped by location with optional filtering';

-- =============================================
-- SAMPLE DATA VALIDATION QUERIES
-- =============================================

-- View to validate data integrity
CREATE VIEW data_validation AS
SELECT 
    'transfers' as table_name,
    COUNT(*) as total_records,
    COUNT(DISTINCT patient_id) as unique_patients,
    COUNT(DISTINCT transfer_id) as unique_transfers,
    MIN(ward_in_time) as earliest_date,
    MAX(COALESCE(ward_out_time, ward_in_time)) as latest_date
FROM transfers
UNION ALL
SELECT 
    'microbiology' as table_name,
    COUNT(*) as total_records,
    COUNT(DISTINCT patient_id) as unique_patients,
    COUNT(DISTINCT test_id) as unique_tests,
    MIN(collection_date) as earliest_date,
    MAX(collection_date) as latest_date
FROM microbiology;

COMMENT ON VIEW data_validation IS 'Data validation summary for quality assurance';

-- =============================================
-- GRANT PERMISSIONS (adjust as needed)
-- =============================================

-- Create roles for different access levels
CREATE ROLE infection_cluster_read;
CREATE ROLE infection_cluster_write;
CREATE ROLE infection_cluster_admin;

-- Grant permissions
GRANT USAGE ON SCHEMA infection_cluster TO infection_cluster_read, infection_cluster_write, infection_cluster_admin;
GRANT SELECT ON ALL TABLES IN SCHEMA infection_cluster TO infection_cluster_read;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA infection_cluster TO infection_cluster_write;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA infection_cluster TO infection_cluster_admin;

-- Grant permissions on sequences
GRANT USAGE ON ALL SEQUENCES IN SCHEMA infection_cluster TO infection_cluster_write, infection_cluster_admin;

-- NOTE: Schema optimized for cluster detection with spatial-temporal indexing
-- NOTE: Materialized view provides pre-computed joins for performance
-- NOTE: Helper functions encapsulate common cluster detection queries