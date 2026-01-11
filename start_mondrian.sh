#!/bin/bash
# Mondrian Services Startup Wrapper
# This script ensures Python runs in unbuffered mode for immediate output

cd "$(dirname "$0")"

# Run Python in unbuffered mode (-u flag) for immediate output
python3 -u scripts/start_services.py start-comprehensive
