-- Migration: Add invitation code expiration fields to kerabat_ibu_hamil table
-- Date: 2026-01-09
-- Description: 
--   - Add invite_code_created_at and invite_code_expires_at columns
--   - Make kerabat_user_id nullable (untuk support invitation code flow)
--   - Make relation_type nullable (akan diisi setelah kerabat complete profile)

-- Step 1: Drop existing unique constraint if exists (karena kerabat_user_id akan nullable)
ALTER TABLE kerabat_ibu_hamil DROP CONSTRAINT IF EXISTS uq_kerabat_ibu;

-- Step 2: Make kerabat_user_id nullable
ALTER TABLE kerabat_ibu_hamil ALTER COLUMN kerabat_user_id DROP NOT NULL;

-- Step 3: Make relation_type nullable
ALTER TABLE kerabat_ibu_hamil ALTER COLUMN relation_type DROP NOT NULL;

-- Step 4: Add invitation code timestamp columns
ALTER TABLE kerabat_ibu_hamil 
ADD COLUMN IF NOT EXISTS invite_code_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE kerabat_ibu_hamil 
ADD COLUMN IF NOT EXISTS invite_code_expires_at TIMESTAMP;

-- Step 5: Create partial unique index untuk mencegah duplicate kerabat-user relationship
-- (hanya berlaku jika kerabat_user_id tidak null)
CREATE UNIQUE INDEX IF NOT EXISTS uq_kerabat_ibu_active 
ON kerabat_ibu_hamil (kerabat_user_id, ibu_hamil_id) 
WHERE kerabat_user_id IS NOT NULL;

-- Step 6: Update existing records yang sudah ada (set expiration untuk invite code yang sudah ada)
-- Jika invite_code ada tapi expires_at null, set expires_at = created_at + 24 jam
UPDATE kerabat_ibu_hamil 
SET invite_code_expires_at = created_at + INTERVAL '24 hours'
WHERE invite_code IS NOT NULL 
  AND invite_code_expires_at IS NULL;

-- Step 7: Set invite_code_created_at untuk existing records
UPDATE kerabat_ibu_hamil 
SET invite_code_created_at = created_at
WHERE invite_code IS NOT NULL 
  AND invite_code_created_at IS NULL;
