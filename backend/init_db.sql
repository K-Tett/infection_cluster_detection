-- Database initialization script for infection cluster detection
-- NOTE: Docker PostgreSQL initialization with medical data security

-- Create application user with limited privileges
CREATE USER infection_app WITH PASSWORD 'secure_password_here';

-- Grant basic connection privileges
GRANT CONNECT ON DATABASE infection_clusters TO infection_app;
GRANT USAGE ON SCHEMA public TO infection_app;

-- Grant table privileges (tables will be created by SQLAlchemy)
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO infection_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE ON SEQUENCES TO infection_app;

-- Create schema version table for tracking migrations
CREATE TABLE IF NOT EXISTS schema_version (
    version VARCHAR(10) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- Grant privileges on schema_version table
GRANT SELECT, INSERT, UPDATE, DELETE ON schema_version TO infection_app;