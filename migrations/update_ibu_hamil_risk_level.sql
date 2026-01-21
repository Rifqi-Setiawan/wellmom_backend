-- Migration: Update ibu_hamil risk_level to use Indonesian values and add tracking fields
-- Date: 2026-01-21
-- Description:
--   1. Update risk_level constraint to use 'rendah', 'sedang', 'tinggi' instead of 'low', 'normal', 'high'
--   2. Make risk_level nullable (null means belum ditentukan)
--   3. Add risk_level_set_by (FK to perawat.id) to track who set the risk level
--   4. Add risk_level_set_at (TIMESTAMP) to track when the risk level was set
--   5. Convert existing risk_level values to Indonesian

-- Step 1: Add new columns for tracking risk level assessment
ALTER TABLE ibu_hamil ADD COLUMN IF NOT EXISTS risk_level_set_by INTEGER;
ALTER TABLE ibu_hamil ADD COLUMN IF NOT EXISTS risk_level_set_at TIMESTAMP;

-- Step 2: Add foreign key constraint for risk_level_set_by
ALTER TABLE ibu_hamil
    ADD CONSTRAINT fk_risk_level_set_by
    FOREIGN KEY (risk_level_set_by)
    REFERENCES perawat(id)
    ON DELETE SET NULL;

-- Step 3: Convert existing risk_level values from English to Indonesian
UPDATE ibu_hamil SET risk_level = 'rendah' WHERE risk_level = 'low';
UPDATE ibu_hamil SET risk_level = 'sedang' WHERE risk_level = 'normal';
UPDATE ibu_hamil SET risk_level = 'tinggi' WHERE risk_level = 'high';

-- Step 4: Drop the existing constraint
ALTER TABLE ibu_hamil DROP CONSTRAINT IF EXISTS check_risk_level;

-- Step 5: Add new constraint with Indonesian values and allow NULL
ALTER TABLE ibu_hamil ADD CONSTRAINT check_risk_level
    CHECK (risk_level IS NULL OR risk_level IN ('rendah', 'sedang', 'tinggi'));

-- Step 6: Make risk_level column nullable (if not already)
ALTER TABLE ibu_hamil ALTER COLUMN risk_level DROP NOT NULL;
ALTER TABLE ibu_hamil ALTER COLUMN risk_level DROP DEFAULT;
