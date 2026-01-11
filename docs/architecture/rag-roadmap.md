# RAG Roadmap: Advisor Image Metadata

## Plan: Add and Ingest Advisor Image Metadata

Enhance the RAG system by storing and ingesting rich metadata (title, date taken, description, etc.) for each advisor image, enabling user-friendly references in queries and outputs.

### Steps
1. Add metadata columns (title, date_taken, description) to the `dimensional_profiles` table via a database migration.
2. Define a metadata manifest format (CSV, JSON, or YAML) for advisor images, or extract from EXIF if available.
3. Update preprocessing scripts (e.g., `compute_image_embeddings.py`) to:
   - Read metadata from the manifest or image files.
   - Store metadata in the database alongside embeddings/dimensional scores.
4. Validate that new and existing images have metadata populated in the database.
5. Document the metadata ingestion process for future reference.

### Further Considerations
1. Choose a manifest format: CSV (simple), JSON/YAML (flexible), or EXIF extraction.
2. Optionally, create a script to backfill metadata for existing images.
3. Ensure all downstream RAG and UI code can access and display the new metadata fields.
