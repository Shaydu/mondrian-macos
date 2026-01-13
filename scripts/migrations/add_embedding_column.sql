-- Migration: Add embedding column to dimensional_profiles table
-- Purpose: Store CLIP embeddings (512-dim vectors) for visual similarity search
-- Date: 2026-01-13

-- Add embedding column if it doesn't exist
ALTER TABLE dimensional_profiles ADD COLUMN embedding BLOB;

-- Create index for faster lookups when filtering by advisor_id and checking for embeddings
CREATE INDEX IF NOT EXISTS idx_dimensional_profiles_embedding 
    ON dimensional_profiles(advisor_id) WHERE embedding IS NOT NULL;
