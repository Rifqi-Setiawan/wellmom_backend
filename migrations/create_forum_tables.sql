-- Migration: Create Forum Discussion Tables
-- Date: 2025-01-08
-- Description: Create tables for forum discussion feature (posts, post_likes, post_replies)

-- ============================================
-- 1. Create posts table
-- ============================================
CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    author_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    details TEXT NOT NULL,
    like_count INTEGER DEFAULT 0 NOT NULL,
    reply_count INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL,
    is_deleted BOOLEAN DEFAULT FALSE NOT NULL,
    deleted_at TIMESTAMP
);

-- Indexes for posts table
CREATE INDEX IF NOT EXISTS idx_posts_author_user_id ON posts(author_user_id);
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at);
CREATE INDEX IF NOT EXISTS idx_posts_like_count ON posts(like_count);
CREATE INDEX IF NOT EXISTS idx_posts_reply_count ON posts(reply_count);
CREATE INDEX IF NOT EXISTS idx_posts_is_deleted ON posts(is_deleted);
CREATE INDEX IF NOT EXISTS idx_post_author_created ON posts(author_user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_post_popularity ON posts(like_count, reply_count, created_at);

-- ============================================
-- 2. Create post_likes table
-- ============================================
CREATE TABLE IF NOT EXISTS post_likes (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    UNIQUE(post_id, user_id)
);

-- Indexes for post_likes table
CREATE INDEX IF NOT EXISTS idx_post_likes_post_id ON post_likes(post_id);
CREATE INDEX IF NOT EXISTS idx_post_likes_user_id ON post_likes(user_id);
CREATE INDEX IF NOT EXISTS idx_post_like_post ON post_likes(post_id, created_at);
CREATE INDEX IF NOT EXISTS idx_post_like_user ON post_likes(user_id, created_at);

-- ============================================
-- 3. Create post_replies table
-- ============================================
CREATE TABLE IF NOT EXISTS post_replies (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    author_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_reply_id INTEGER REFERENCES post_replies(id) ON DELETE CASCADE,
    reply_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL,
    is_deleted BOOLEAN DEFAULT FALSE NOT NULL,
    deleted_at TIMESTAMP
);

-- Indexes for post_replies table
CREATE INDEX IF NOT EXISTS idx_post_replies_post_id ON post_replies(post_id);
CREATE INDEX IF NOT EXISTS idx_post_replies_author_user_id ON post_replies(author_user_id);
CREATE INDEX IF NOT EXISTS idx_post_replies_parent_reply_id ON post_replies(parent_reply_id);
CREATE INDEX IF NOT EXISTS idx_post_replies_created_at ON post_replies(created_at);
CREATE INDEX IF NOT EXISTS idx_post_replies_is_deleted ON post_replies(is_deleted);
CREATE INDEX IF NOT EXISTS idx_post_reply_post ON post_replies(post_id, created_at);
CREATE INDEX IF NOT EXISTS idx_post_reply_author ON post_replies(author_user_id, created_at);

-- ============================================
-- 4. Create trigger to update updated_at automatically
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to posts table
DROP TRIGGER IF EXISTS update_posts_updated_at ON posts;
CREATE TRIGGER update_posts_updated_at
    BEFORE UPDATE ON posts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to post_replies table
DROP TRIGGER IF EXISTS update_post_replies_updated_at ON post_replies;
CREATE TRIGGER update_post_replies_updated_at
    BEFORE UPDATE ON post_replies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 5. Comments for documentation
-- ============================================
COMMENT ON TABLE posts IS 'Forum discussion posts created by ibu_hamil or perawat';
COMMENT ON TABLE post_likes IS 'Likes on forum posts (one like per user per post)';
COMMENT ON TABLE post_replies IS 'Replies/comments on forum posts (supports nested replies)';

COMMENT ON COLUMN posts.like_count IS 'Denormalized counter for performance';
COMMENT ON COLUMN posts.reply_count IS 'Denormalized counter for performance';
COMMENT ON COLUMN posts.is_deleted IS 'Soft delete flag';
COMMENT ON COLUMN post_replies.parent_reply_id IS 'For nested replies (optional)';
COMMENT ON COLUMN post_replies.is_deleted IS 'Soft delete flag';
