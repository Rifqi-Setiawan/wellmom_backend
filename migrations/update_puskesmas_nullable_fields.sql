-- Migration: Update Puskesmas nullable fields for multi-step registration flow
-- Date: 2026-01-19
-- Description:
--   Mengubah field sk_document_url dan building_photo_url menjadi nullable
--   untuk mendukung flow registrasi multi-step:
--   - Step 1: Create draft puskesmas (tanpa dokumen)
--   - Step 2: Upload dokumen
--   - Step 3: Submit untuk approval

-- Make sk_document_url nullable (untuk draft registration)
ALTER TABLE puskesmas ALTER COLUMN sk_document_url DROP NOT NULL;

-- Make building_photo_url nullable (untuk draft registration)
ALTER TABLE puskesmas ALTER COLUMN building_photo_url DROP NOT NULL;

-- Verify changes
SELECT
    column_name,
    is_nullable,
    data_type
FROM information_schema.columns
WHERE table_name = 'puskesmas'
AND column_name IN ('sk_document_url', 'building_photo_url', 'latitude', 'longitude');
