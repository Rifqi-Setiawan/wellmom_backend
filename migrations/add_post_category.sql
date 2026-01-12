-- Migration: Add Category Column to Posts Table
-- Date: 2025-01-09
-- Description: Add category field to forum posts with enum type

-- ============================================
-- 1. Create ENUM type for post categories
-- ============================================
DO $$ 
BEGIN
    -- Create enum type if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'post_category') THEN
        CREATE TYPE post_category AS ENUM (
            'kesehatan',
            'nutrisi',
            'persiapan',
            'curhat',
            'tips',
            'tanya_jawab'
        );
    END IF;
END $$;

-- ============================================
-- 2. Add category column to posts table
-- ============================================
-- Check if column already exists before adding
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'posts' 
        AND column_name = 'category'
    ) THEN
        ALTER TABLE posts 
        ADD COLUMN category post_category NOT NULL DEFAULT 'tanya_jawab';
    END IF;
END $$;

-- ============================================
-- 3. Create index for category column
-- ============================================
CREATE INDEX IF NOT EXISTS idx_posts_category ON posts(category);
CREATE INDEX IF NOT EXISTS idx_post_category_created ON posts(category, created_at);

-- ============================================
-- 4. Add comment for documentation
-- ============================================
COMMENT ON COLUMN posts.category IS 'Forum post category: kesehatan, nutrisi, persiapan, curhat, tips, tanya_jawab';

-- ============================================
-- 5. Verify the migration
-- ============================================
-- Uncomment the following line to verify the column was added:
-- SELECT column_name, data_type, column_default 
-- FROM information_schema.columns 
-- WHERE table_name = 'posts' AND column_name = 'category';
