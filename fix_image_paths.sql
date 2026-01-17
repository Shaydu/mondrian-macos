-- Fix image paths to point to correct Linux location
UPDATE dimensional_profiles 
SET image_path = REPLACE(image_path, '/Users/shaydu/dev/mondrian-macos', '/home/doo/dev/mondrian-macos')
WHERE image_path LIKE '/Users/shaydu/%';

-- Show updated paths
SELECT COUNT(*) as total, COUNT(DISTINCT image_path) as unique_paths 
FROM dimensional_profiles 
WHERE advisor_id='ansel';
