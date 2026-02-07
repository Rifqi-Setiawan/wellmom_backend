-- Migration: Add FCM token columns to users table
-- Date: 2025-02-14
-- Description: Add Firebase Cloud Messaging device token for push notifications
-- This migration adds fcm_token and fcm_token_updated_at columns to the users table

-- Step 1: Add fcm_token column (nullable, for storing FCM device token)
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS fcm_token VARCHAR(255) NULL;

-- Step 2: Add fcm_token_updated_at column (nullable, for tracking when token was last updated)
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS fcm_token_updated_at TIMESTAMP NULL;

-- Step 3: Create index on fcm_token for faster lookups when sending notifications
CREATE INDEX IF NOT EXISTS idx_users_fcm_token 
ON users(fcm_token) 
WHERE fcm_token IS NOT NULL;

-- Verification: Check if columns were added successfully
-- Uncomment the following line to verify:
-- SELECT column_name, data_type, is_nullable 
-- FROM information_schema.columns 
-- WHERE table_name = 'users' AND column_name IN ('fcm_token', 'fcm_token_updated_at');
