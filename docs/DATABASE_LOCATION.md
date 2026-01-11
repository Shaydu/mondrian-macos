# Database Location

## Current Configuration

**Database Location:** `/Users/shaydu/dev/mondrian-macos/mondrian/mondrian.db`

All services and scripts now reference this single database file.

## Path Configuration

Services running from the `mondrian/` directory use:
- **Relative path:** `mondrian.db`
- **Absolute path:** `/Users/shaydu/dev/mondrian-macos/mondrian/mondrian.db`

Scripts running from the project root use:
- **Relative path:** `mondrian/mondrian.db`

## Service Configuration

Updated files:
- `mondrian/monitoring_config.json` - All services use `--db mondrian.db`

## Database Schema

The database includes:
- **jobs** table with `enable_rag` column (INTEGER, default 0)
- **advisor_image_techniques** - 48 indexed techniques for 'ansel' advisor
- **user_image_techniques** - Techniques detected in user images
- **photographer_techniques** - Master list of photographic techniques
- **dimensional_profiles** - Dimensional analysis data
- **image_captions** - Image caption data

## Old Database Files (Archived)

Moved to `mondrian/trash/`:
- `mondrian_old_20260110.db` - Previous mondrian subdirectory database
- Other archived versions

## Previous Issues (Resolved)

- ✅ Multiple database files causing confusion
- ✅ Services using different database paths
- ✅ Missing `enable_rag` column in jobs table
- ✅ Inconsistent path references (`../mondrian.db` vs `mondrian.db`)
