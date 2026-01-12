-- Migration: Add PostCategory Table and Update Posts
-- Date: 2025-01-09
-- Description: Create post_categories table and update posts to use category_id

-- ============================================
-- 1. Create post_categories table
-- ============================================
CREATE TABLE IF NOT EXISTS post_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Indexes for post_categories table
CREATE INDEX IF NOT EXISTS idx_post_categories_name ON post_categories(name);
CREATE INDEX IF NOT EXISTS idx_post_categories_is_active ON post_categories(is_active);

-- ============================================
-- 2. Insert default categories
-- ============================================
INSERT INTO post_categories (name, display_name, description, is_active) VALUES
    ('kesehatan', 'Kesehatan', 'Diskusi tentang kesehatan ibu hamil', TRUE),
    ('nutrisi', 'Nutrisi', 'Diskusi tentang nutrisi dan makanan sehat untuk ibu hamil', TRUE),
    ('persiapan', 'Persiapan', 'Diskusi tentang persiapan kelahiran dan kehamilan', TRUE),
    ('curhat', 'Curhat', 'Ruang untuk berbagi cerita dan pengalaman', TRUE),
    ('tips', 'Tips', 'Tips dan saran untuk ibu hamil', TRUE),
    ('tanya_jawab', 'Tanya Jawab', 'Tanya jawab seputar kehamilan', TRUE)
ON CONFLICT (name) DO NOTHING;

-- ============================================
-- 3. Add category_id column to posts table
-- ============================================
-- Check if column already exists before adding
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'posts' 
        AND column_name = 'category_id'
    ) THEN
        -- Get default category ID (tanya_jawab)
        ALTER TABLE posts 
        ADD COLUMN category_id INTEGER;
        
        -- Set default value for existing posts
        UPDATE posts 
        SET category_id = (SELECT id FROM post_categories WHERE name = 'tanya_jawab' LIMIT 1)
        WHERE category_id IS NULL;
        
        -- Make it NOT NULL after setting defaults
        ALTER TABLE posts 
        ALTER COLUMN category_id SET NOT NULL;
        
        -- Add foreign key constraint
        ALTER TABLE posts 
        ADD CONSTRAINT fk_posts_category 
        FOREIGN KEY (category_id) 
        REFERENCES post_categories(id) 
        ON DELETE RESTRICT;
    END IF;
END $$;

-- ============================================
-- 4. Create indexes for category_id
-- ============================================
CREATE INDEX IF NOT EXISTS idx_posts_category_id ON posts(category_id);
CREATE INDEX IF NOT EXISTS idx_post_category_created ON posts(category_id, created_at);

-- ============================================
-- 5. Drop old enum type if exists (from previous migration)
-- ============================================
-- Note: Only run this if you previously created post_category enum type
-- DO $$ 
-- BEGIN
--     IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'post_category') THEN
--         -- First, drop any columns using this type
--         -- Then drop the type
--         DROP TYPE IF EXISTS post_category CASCADE;
--     END IF;
-- END $$;

-- ============================================
-- 6. Add comments for documentation
-- ============================================
COMMENT ON TABLE post_categories IS 'Forum post categories';
COMMENT ON COLUMN posts.category_id IS 'Foreign key to post_categories table';

-- ============================================
-- 7. Verify the migration
-- ============================================
-- Uncomment to verify:
-- SELECT * FROM post_categories;
-- SELECT column_name, data_type, column_default 
-- FROM information_schema.columns 
-- WHERE table_name = 'posts' AND column_name = 'category_id';
