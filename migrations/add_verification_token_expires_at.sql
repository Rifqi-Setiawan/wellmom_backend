-- Migration: Add verification_token_expires_at to users table
-- Date: 2025-01-19
-- Description: Adds expiration timestamp for verification tokens

-- Add new column
ALTER TABLE users
ADD COLUMN IF NOT EXISTS verification_token_expires_at TIMESTAMP NULL;

-- Create index for faster lookups of expired tokens
CREATE INDEX IF NOT EXISTS idx_users_verification_token_expires
ON users (verification_token_expires_at)
WHERE verification_token IS NOT NULL;

-- Optional: Clear any existing tokens that don't have expiration
-- (they will need to be regenerated)
-- UPDATE users SET verification_token = NULL WHERE verification_token IS NOT NULL;
