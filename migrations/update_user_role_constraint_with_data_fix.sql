-- Migration: Update user role constraint to include 'super_admin' and remove 'admin'
-- Date: 2026-01-08
-- Description: Update check_user_role constraint to allow 'super_admin' role and remove 'admin' role
-- IMPORTANT: This script also updates existing 'admin' users to 'super_admin'

-- Step 1: Update existing users with role 'admin' to 'super_admin'
-- (This must be done BEFORE dropping the constraint)
UPDATE users 
SET role = 'super_admin' 
WHERE role = 'admin';

-- Step 2: Drop the existing constraint
ALTER TABLE users DROP CONSTRAINT IF EXISTS check_user_role;

-- Step 3: Add the new constraint with updated roles
ALTER TABLE users ADD CONSTRAINT check_user_role 
    CHECK (role IN ('super_admin', 'puskesmas', 'perawat', 'ibu_hamil', 'kerabat'));
