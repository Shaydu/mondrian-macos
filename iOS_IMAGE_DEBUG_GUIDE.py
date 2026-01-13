#!/usr/bin/env python3
"""
iOS Reference Image Debugging Guide
====================================

This script helps debug why reference images are not rendering on iOS.

WHAT WAS ADDED:
===============
1. Enhanced logging in job_service_v2.3.py (/api/reference-image/<filename> endpoint)
   - Logs every request with: filename, source IP, User-Agent, request URL
   - Logs file found/not found status with full file path
   - Logs success/failure status with content-type and size

2. Enhanced logging in json_to_html_converter.py 
   - Logs the absolute URLs being embedded in HTML
   - Logs URL conversion from AI service (5100) to job service (5005)

HOW TO USE:
===========

1. Run an analysis from iOS:
   - Open the app and run an analysis
   - The reference images gallery will be included if RAG is enabled

2. Check the debug logs:
   - Backend logs: tail -f /tmp/job_service_ios_debug.log
   - JSON logs: tail -f /Users/shaydu/dev/mondrian-macos/.cursor/debug.log | grep ios-image-debug

3. Look for these patterns in the logs:

   SUCCESS (images rendering):
   ✓ [iOS DEBUG] Reference image request
   ✓ [iOS DEBUG] Found reference image file
   ✓ [iOS DEBUG] Serving reference image successfully
   
   FAILURE (images not rendering):
   ✗ [iOS DEBUG] Reference image not found
   ✗ [iOS DEBUG] Failed to serve reference image

DEBUG LOG FIELDS:
================

From /api/reference-image request logs:
- filename: The image file being requested
- remote_addr: IP address making the request (192.168.x.x from iOS)
- user_agent: Browser/WebView info from iOS app
- request_url: Full URL including port and path
- Status: success / not_found / error

From HTML generation logs:
- display_url: Absolute URL embedded in HTML (should be http://192.168.x.x:5005/api/reference-image/...)
- original_url: URL from AI service before conversion

EXPECTED BEHAVIOR:
==================

Web (http://localhost:5005):
- Images should load and show
- "View full size" link should work
- Debug log shows: "remote_addr: 127.0.0.1"

iOS (http://192.168.x.x:5005):
- Images should load and show  
- "View full size" link should work
- Debug log shows: "remote_addr: 192.168.x.x"
- display_url should be "http://192.168.x.x:5005/api/reference-image/..."

TROUBLESHOOTING:
================

If images are NOT rendering on iOS:

1. Check if request is reaching the server:
   tail -f /tmp/job_service_ios_debug.log
   Look for "[iOS DEBUG] Reference image request" entries

2. Check the file path:
   Look for "[iOS DEBUG] Found reference image file"
   Verify filepath looks correct: .../source/advisor/photographer/ansel/...

3. Check the URL being embedded:
   grep "ios-image-debug" /Users/shaydu/dev/mondrian-macos/.cursor/debug.log
   Look for "display_url" with correct IP address

4. Check network connectivity:
   From iOS, can you curl the URL directly?
   curl http://192.168.x.x:5005/api/reference-image/ansel-old-faithful-geyser-1944.png
"""

import sys

print(__doc__)
