-- Migration: Update health_records table structure
-- Date: 2025-01-21
-- Description: Revisi struktur tabel health_records
--   - Parameter wajib: systolic, diastolic, heart_rate, body_temperature, weight, checked_by, complaints
--   - Parameter opsional: hemoglobin, blood_glucose, protein_urin, upper_arm_circumference, fundal_height, fetal_heart_rate
--   - Hapus: checkup_type, supplements, treatment_plan, physical_examination, referral_needed,
--           next_checkup_date, next_checkup_notes, diagnosis, data_source, medications, referral_notes

-- Step 1: Add checked_by column if not exists (dicek oleh perawat atau mandiri)
ALTER TABLE health_records
ADD COLUMN IF NOT EXISTS checked_by VARCHAR(20) DEFAULT 'mandiri';

-- Step 2: Update checked_by to NOT NULL after setting default
UPDATE health_records SET checked_by = 'mandiri' WHERE checked_by IS NULL;
ALTER TABLE health_records ALTER COLUMN checked_by SET NOT NULL;

-- Step 3: Add check constraint for checked_by values
ALTER TABLE health_records DROP CONSTRAINT IF EXISTS check_checked_by;
ALTER TABLE health_records ADD CONSTRAINT check_checked_by CHECK (checked_by IN ('perawat', 'mandiri'));

-- Step 4: Add weight column if not exists (berat badan)
ALTER TABLE health_records
ADD COLUMN IF NOT EXISTS weight FLOAT;

-- Step 5: Add complaints column if not exists (keluhan)
ALTER TABLE health_records
ADD COLUMN IF NOT EXISTS complaints TEXT;

-- Step 6: Add hemoglobin column if not exists
ALTER TABLE health_records
ADD COLUMN IF NOT EXISTS hemoglobin FLOAT;

-- Step 7: Add blood_glucose column if not exists (gula darah)
ALTER TABLE health_records
ADD COLUMN IF NOT EXISTS blood_glucose FLOAT;

-- Step 8: Add protein_urin column if not exists
ALTER TABLE health_records
ADD COLUMN IF NOT EXISTS protein_urin VARCHAR(20);

-- Step 9: Add upper_arm_circumference column if not exists (lingkar lengan atas/LILA)
ALTER TABLE health_records
ADD COLUMN IF NOT EXISTS upper_arm_circumference FLOAT;

-- Step 10: Add fundal_height column if not exists (fundus uteri)
ALTER TABLE health_records
ADD COLUMN IF NOT EXISTS fundal_height FLOAT;

-- Step 11: Add fetal_heart_rate column if not exists (denyut jantung janin)
ALTER TABLE health_records
ADD COLUMN IF NOT EXISTS fetal_heart_rate INTEGER;

-- Step 12: Drop columns that are no longer needed
-- Note: Use IF EXISTS to avoid errors if columns don't exist
ALTER TABLE health_records DROP COLUMN IF EXISTS checkup_type;
ALTER TABLE health_records DROP COLUMN IF EXISTS supplements;
ALTER TABLE health_records DROP COLUMN IF EXISTS treatment_plan;
ALTER TABLE health_records DROP COLUMN IF EXISTS physical_examination;
ALTER TABLE health_records DROP COLUMN IF EXISTS referral_needed;
ALTER TABLE health_records DROP COLUMN IF EXISTS next_checkup_date;
ALTER TABLE health_records DROP COLUMN IF EXISTS next_checkup_notes;
ALTER TABLE health_records DROP COLUMN IF EXISTS diagnosis;
ALTER TABLE health_records DROP COLUMN IF EXISTS data_source;
ALTER TABLE health_records DROP COLUMN IF EXISTS medications;
ALTER TABLE health_records DROP COLUMN IF EXISTS referral_notes;

-- Step 13: Rename fundal_height_cm to fundal_height if exists (standardize naming)
-- First check if old column exists and new doesn't
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='health_records' AND column_name='fundal_height_cm')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='health_records' AND column_name='fundal_height') THEN
        ALTER TABLE health_records RENAME COLUMN fundal_height_cm TO fundal_height;
    END IF;
END $$;

-- Step 14: Set required columns (update existing null values first before making NOT NULL)
-- For existing records, set default values for required columns that might be NULL
UPDATE health_records SET blood_pressure_systolic = 0 WHERE blood_pressure_systolic IS NULL;
UPDATE health_records SET blood_pressure_diastolic = 0 WHERE blood_pressure_diastolic IS NULL;
UPDATE health_records SET heart_rate = 0 WHERE heart_rate IS NULL;
UPDATE health_records SET body_temperature = 0 WHERE body_temperature IS NULL;
UPDATE health_records SET weight = 0 WHERE weight IS NULL;
UPDATE health_records SET complaints = '' WHERE complaints IS NULL;

-- Step 15: Make required columns NOT NULL
ALTER TABLE health_records ALTER COLUMN blood_pressure_systolic SET NOT NULL;
ALTER TABLE health_records ALTER COLUMN blood_pressure_diastolic SET NOT NULL;
ALTER TABLE health_records ALTER COLUMN heart_rate SET NOT NULL;
ALTER TABLE health_records ALTER COLUMN body_temperature SET NOT NULL;
ALTER TABLE health_records ALTER COLUMN weight SET NOT NULL;
ALTER TABLE health_records ALTER COLUMN complaints SET NOT NULL;
