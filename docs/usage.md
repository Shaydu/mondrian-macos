# Usage Guide: RAG and Non-RAG Options

## Running the Job Service

The Mondrian Job Service supports both RAG (Retrieval-Augmented Generation) and non-RAG analysis flows. The selection is made per job, not via a global command-line flag.

### 1. RAG Flow
- **How to enable:**
  - When submitting a job via API or form, set the `enable_rag` parameter to `true` (e.g., `enable_rag=true`).
  - For internal Python calls, pass `enable_rag=True` to the job creation or `process_job` function.
- **Effect:**
  - The backend will use RAG context for analysis and LLM prompting.

### 2. Non-RAG Flow
- **How to enable:**
  - Omit the `enable_rag` parameter or set it to `false` (e.g., `enable_rag=false`).
  - For internal Python calls, pass `enable_rag=False`.
- **Effect:**
  - The backend will use the standard (non-RAG) prompt and analysis flow.

### 3. Command-Line Arguments
- There is currently **no top-level command-line flag** (such as `--rag` or `--enable-rag`) for selecting RAG/non-RAG globally.
- The main command-line arguments are:
  - `--port` (default: 5005)
  - `--db` (default: mondrian.db)
  - `--ai_service_url` (default: http://127.0.0.1:5100/analyze)
  - `--debug` (enable debug mode)

### 4. Example API Usage
```bash
# RAG-enabled job submission (example)
curl -F "file=@photo.jpg" -F "enable_rag=true" http://localhost:5005/analyze

# Non-RAG job submission (example)
curl -F "file=@photo.jpg" -F "enable_rag=false" http://localhost:5005/analyze
```

---

## Streaming LLM "Thinking" Updates
- The backend supports streaming status and LLM "thinking" updates via the `/stream/<job_id>` endpoint.
- If the LLM model provides intermediate "thinking" steps (e.g., `llm_thinking`), these are included in the streamed status updates.
- The `thinking` field in the status response indicates if the model is currently "thinking".
- Example fields in the status response:
  - `llm_thinking`: Current LLM thought or step
  - `progress_percentage`: Progress as a percentage
  - `status`: Current status (e.g., analyzing)
  - `step_phase`: Current phase (e.g., advisor_analysis)
  - `stream_url`: URL for streaming updates

---

For more details, see the API documentation or contact the development team.
