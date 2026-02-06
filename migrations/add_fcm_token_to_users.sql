-- Migration: Add FCM token columns to users table
-- Date: 2026-02-06
-- Description: Add Firebase Cloud Messaging device token for push notifications

ALTER TABLE users ADD COLUMN IF NOT EXISTS fcm_token VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS fcm_token_updated_at TIMESTAMP;
CREATE INDEX IF NOT EXISTS idx_users_fcm_token ON users(fcm_token);
