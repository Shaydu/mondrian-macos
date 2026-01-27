"""
Centralized timeout configuration for all services and operations.

All timeouts should be defined and imported from this module to ensure
consistency across the codebase.
"""

# Service startup and health checks
SERVICE_STARTUP_TIMEOUT = 30  # seconds - time to wait for service to start
SERVICE_HEALTH_CHECK_TIMEOUT = 5  # seconds - quick health check timeout

# AI Advisor service timeouts
AI_ADVISOR_REQUEST_TIMEOUT = 600  # seconds (10 minutes) - max for analysis requests
AI_ADVISOR_STARTUP_TIMEOUT = 30  # seconds - startup wait timeout

# Job processing timeouts
JOB_SUBMISSION_TIMEOUT = 30  # seconds - submit job API call
JOB_STATUS_CHECK_TIMEOUT = 10  # seconds - poll job status API call
JOB_PROCESSING_TIMEOUT = 600  # seconds (10 minutes) - max wait for job completion

# E2E test timeouts (by model/mode)
E2E_TEST_BASELINE_TIMEOUT = 90  # seconds
E2E_TEST_LORA_TIMEOUT = 90  # seconds
E2E_TEST_THINKING_TIMEOUT = 180  # seconds (3 minutes - thinking models are slower)
E2E_TEST_RAG_TIMEOUT = 120  # seconds (RAG with embeddings is slower)
E2E_TEST_LORA_RAG_TIMEOUT = 180  # seconds (combination is slowest)
E2E_TEST_LONG_TIMEOUT = 300  # seconds (5 minutes - for integration tests)
E2E_TEST_VERY_LONG_TIMEOUT = 600  # seconds (10 minutes - for slow operations)

# Database timeouts
DATABASE_LOCK_TIMEOUT = 5  # seconds - SQLite lock timeout
DATABASE_CONN_TIMEOUT = 10  # seconds - connection timeout

# External API timeouts (downloads, external services)
EXTERNAL_API_TIMEOUT = 15  # seconds - general external API calls
EXTERNAL_DOWNLOAD_TIMEOUT = 30  # seconds - file downloads
EXTERNAL_STREAM_TIMEOUT = 300  # seconds (5 minutes) - streaming downloads

# Process/subprocess timeouts
SUBPROCESS_GENERAL_TIMEOUT = 5  # seconds - general subprocess operations
SUBPROCESS_KILL_TIMEOUT = 3  # seconds - SIGTERM/SIGKILL timeout
SUBPROCESS_WAIT_TIMEOUT = 5  # seconds - process.wait() timeout

# Port and service polling
PORT_CHECK_TIMEOUT = 10  # seconds - wait for port to become available
SERVICE_READINESS_TIMEOUT = 120  # seconds (2 minutes) - full service startup verification
SERVICE_READINESS_CHECK_INTERVAL = 2  # seconds - interval between readiness checks

# Job status polling
JOB_POLL_INTERVAL = 5  # seconds - interval between status checks
JOB_POLL_MAX_WAIT = 600  # seconds (10 minutes) - max total wait time

# Health check polling
HEALTH_CHECK_POLL_INTERVAL = 0.1  # seconds - quick health check poll
HEALTH_CHECK_MAX_WAIT = 30  # seconds - max wait for health check
