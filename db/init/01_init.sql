-- ============================================================
-- Lab 7 — PostgreSQL Initialization Script
-- Runs automatically on first container start
-- ============================================================

-- Create the main lab data table
CREATE TABLE IF NOT EXISTS lab_data (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    value       TEXT,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_lab_data_created_at ON lab_data(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_lab_data_name ON lab_data(name);

-- Create request log table (for audit trail)
CREATE TABLE IF NOT EXISTS request_log (
    id            SERIAL PRIMARY KEY,
    node_id       VARCHAR(50),
    method        VARCHAR(10),
    path          VARCHAR(500),
    status_code   INTEGER,
    latency_ms    INTEGER,
    remote_addr   VARCHAR(45),
    timestamp     TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_req_log_timestamp ON request_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_req_log_node ON request_log(node_id);

-- Insert seed data for testing
INSERT INTO lab_data (name, value) VALUES
    ('lab7-init',     'Database initialized by init script'),
    ('node-topology', 'nginx → api-1, api-2 → postgres, redis'),
    ('network-zones', 'frontend-dmz: 172.20.0.0/24 | backend-secure: 172.21.0.0/24'),
    ('test-record-1', 'Sample data entry 1'),
    ('test-record-2', 'Sample data entry 2'),
    ('test-record-3', 'Sample data entry 3')
ON CONFLICT DO NOTHING;

-- Create read-only role for reporting (security best practice)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'labreadonly') THEN
        CREATE ROLE labreadonly;
    END IF;
END
$$;

GRANT CONNECT ON DATABASE labdb TO labreadonly;
GRANT USAGE ON SCHEMA public TO labreadonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO labreadonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO labreadonly;

-- Log the initialization
INSERT INTO request_log (node_id, method, path, status_code, latency_ms, remote_addr)
VALUES ('db-init', 'SYSTEM', '/init', 200, 0, '127.0.0.1');

\echo '✅ Lab 7 Database initialized successfully'
\dt
