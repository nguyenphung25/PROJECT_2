-- =====================================================
-- SMART PARKING SYSTEM - Supabase Database Setup
-- Chay script nay trong Supabase Dashboard > SQL Editor
-- =====================================================

-- 1. Tao bang parking_sessions
CREATE TABLE IF NOT EXISTS parking_sessions (
    id TEXT PRIMARY KEY,
    plate_text TEXT NOT NULL,
    entry_time TEXT NOT NULL,
    exit_time TEXT,
    entry_image_path TEXT,
    exit_image_path TEXT,
    status TEXT NOT NULL DEFAULT 'inside',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 2. Tao bang detections
CREATE TABLE IF NOT EXISTS detections (
    id TEXT PRIMARY KEY,
    parking_session_id TEXT,
    action TEXT NOT NULL,
    plate_text TEXT,
    image_path TEXT,
    image_url TEXT,
    confidence REAL DEFAULT 0,
    detection_status TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (parking_session_id) REFERENCES parking_sessions(id)
);

-- 3. Tao indexes de query nhanh hon
CREATE INDEX IF NOT EXISTS idx_parking_sessions_plate
    ON parking_sessions(plate_text);

CREATE INDEX IF NOT EXISTS idx_parking_sessions_status
    ON parking_sessions(status);

CREATE INDEX IF NOT EXISTS idx_parking_sessions_updated
    ON parking_sessions(updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_detections_created
    ON detections(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_detections_session
    ON detections(parking_session_id);

-- 4. Cap nhat RLS (Row Level Security) - cho phep service_role full access
ALTER TABLE parking_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE detections ENABLE ROW LEVEL SECURITY;

-- Policy cho service_role (full access)
CREATE POLICY "Service role full access" ON parking_sessions
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access" ON detections
    FOR ALL USING (auth.role() = 'service_role');

-- Policy cho anon (read only)
CREATE POLICY "Anon read access" ON parking_sessions
    FOR SELECT USING (true);

CREATE POLICY "Anon read access" ON detections
    FOR SELECT USING (true);

-- =====================================================
-- Xong! Kiem tra bang da tao trong Table Editor
-- =====================================================
