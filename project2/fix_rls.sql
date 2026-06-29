-- Chay script nay de fix RLS
-- Vao Supabase Dashboard > SQL Editor > Paste vao > Run

-- Xoa policies cu neu co
DROP POLICY IF EXISTS "Service role full access" ON parking_sessions;
DROP POLICY IF EXISTS "Service role full access" ON detections;
DROP POLICY IF EXISTS "Anon read access" ON parking_sessions;
DROP POLICY IF EXISTS "Anon read access" ON detections;

-- Tao policy moi cho service_role (full access)
CREATE POLICY "Allow all for service_role" ON parking_sessions
    FOR ALL USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Allow all for service_role" ON detections
    FOR ALL USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Cho phep anon read
CREATE POLICY "Allow select for anon" ON parking_sessions
    FOR SELECT USING (true);

CREATE POLICY "Allow select for anon" ON detections
    FOR SELECT USING (true);
