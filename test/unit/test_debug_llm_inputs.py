#!/usr/bin/env python3
"""
LLM Input Debugging Tool
========================

Captures and logs ALL inputs sent to the LLM for inspection and comparison.

This tool runs an analysis and saves:
- System prompt (with any substitutions/augmentations)
- Advisor prompt (with any substitutions/augmentations)
- RAG context (similar advisor images, embeddings data)
- LoRA metadata
- Complete constructed prompt as sent to model
- Final LLM response

Usage:
    # First start services in desired mode:
    ./mondrian.sh --restart --mode=rag
    # or --mode=baseline, --mode=lora, etc.

    # Then run this tool:
    python3 test/unit/test_debug_llm_inputs.py
"""

import requests
import json
import time
import sys
import os
import base64
from pathlib import Path
from datetime import datetime

# Configuration
AI_ADVISOR_URL = "http://127.0.0.1:5100"
JOB_SERVICE_URL = "http://127.0.0.1:5005"
TEST_IMAGE = "source/mike-shrub.jpg"
ADVISOR = "ansel"

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
BOLD = '\033[1m'
NC = '\033[0m'


def print_header(text):
    """Print section header"""
    print(f"\n{CYAN}{'='*80}{NC}")
    print(f"{CYAN}{BOLD}{text}{NC}")
    print(f"{CYAN}{'='*80}{NC}\n")


def print_success(text):
    """Print success message"""
    print(f"{GREEN}✓{NC} {text}")


def print_error(text):
    """Print error message"""
    print(f"{RED}✗{NC} {text}")


def print_info(text):
    """Print info message"""
    print(f"{YELLOW}ℹ{NC} {text}")


def print_section(text):
    """Print subsection"""
    print(f"\n{BLUE}{BOLD}{text}{NC}")
    print(f"{BLUE}{'-'*60}{NC}")


def setup_output_directory():
    """Create timestamped output directory for debug results"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("test_results") / "debug_llm_inputs" / f"debug_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def make_json_serializable(obj):
    """Convert non-JSON-serializable types to serializable types"""
    if isinstance(obj, bytes):
        return base64.b64encode(obj).decode('utf-8')
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [make_json_serializable(v) for v in obj]
    return obj


def get_advisor_metadata():
    """Fetch complete advisor metadata"""
    try:
        response = requests.get(f"{AI_ADVISOR_URL}/advisor/{ADVISOR}/metadata", timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print_error(f"Could not fetch advisor metadata: {e}")
    return None


def run_debug_inference(output_dir):
    """Run inference with full debug logging"""
    image_path = Path(TEST_IMAGE)
    
    if not image_path.exists():
        print_error(f"Test image not found: {image_path}")
        return False

    # Get service info
    print_info("Getting service information...")
    
    try:
        health_resp = requests.get(f"{AI_ADVISOR_URL}/health", timeout=5)
        if health_resp.status_code != 200:
            print_error("AI Advisor Service is not healthy")
            return False
        
        health = health_resp.json()
        service_info = {
            'timestamp': datetime.now().isoformat(),
            'ai_advisor_service': health,
            'test_config': {
                'test_image': str(image_path),
                'advisor': ADVISOR,
            }
        }
        
        with open(output_dir / "service_info.json", 'w') as f:
            json.dump(service_info, f, indent=2)
        
        print_success(f"Service info saved")
        
    except Exception as e:
        print_error(f"Could not get service info: {e}")

    # Get advisor metadata
    print_info("Fetching advisor metadata...")
    advisor_metadata = get_advisor_metadata()
    
    if advisor_metadata:
        # Save complete metadata
        serializable_metadata = make_json_serializable(advisor_metadata)
        with open(output_dir / "advisor_metadata_complete.json", 'w') as f:
            json.dump(serializable_metadata, f, indent=2)
        print_success("Advisor metadata saved")
        
        # Extract and save prompts separately for easier viewing
        if advisor_metadata.get('system_prompt'):
            prompt = advisor_metadata['system_prompt']
            if isinstance(prompt, bytes):
                prompt = prompt.decode('utf-8')
            with open(output_dir / "01_system_prompt.txt", 'w') as f:
                f.write(prompt)
            print_success("System prompt saved")
        
        if advisor_metadata.get('advisor_prompt'):
            prompt = advisor_metadata['advisor_prompt']
            if isinstance(prompt, bytes):
                prompt = prompt.decode('utf-8')
            with open(output_dir / "02_advisor_prompt.txt", 'w') as f:
                f.write(prompt)
            print_success("Advisor prompt saved")
    
    # Run analysis with different modes to compare
    modes_to_test = ['base', 'rag', 'rag+embeddings']
    
    for idx, mode in enumerate(modes_to_test, 1):
        mode_dir = output_dir / f"mode_{idx}_{mode}"
        mode_dir.mkdir(parents=True, exist_ok=True)
        
        print_section(f"Testing Mode: {mode}")
        
        with open(image_path, 'rb') as f:
            files = {'image': (image_path.name, f, 'image/jpeg')}
            data = {
                'advisor': ADVISOR,
                'mode': mode,
            }
            
            if 'rag' in mode:
                data['enable_rag'] = 'true'
            if 'embeddings' in mode:
                data['enable_embeddings'] = 'true'
            
            # Save request config
            with open(mode_dir / "request_config.json", 'w') as req_f:
                json.dump(data, req_f, indent=2)
            
            start_time = time.time()
            
            try:
                print_info(f"Sending request with mode='{mode}'...")
                response = requests.post(
                    f"{AI_ADVISOR_URL}/analyze",
                    files=files,
                    data=data,
                    timeout=120
                )
                
                elapsed = time.time() - start_time
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Save complete response
                    with open(mode_dir / "response_complete.json", 'w') as f:
                        json.dump(result, f, indent=2)
                    
                    print_success(f"Response received in {elapsed:.2f}s")
                    
                    # Extract and save individual fields
                    if 'html' in result:
                        with open(mode_dir / "response_html.html", 'w') as f:
                            f.write(result['html'])
                    
                    if 'mode_used' in result:
                        with open(mode_dir / "mode_used.txt", 'w') as f:
                            f.write(result['mode_used'])
                    
                    if 'metadata' in result and isinstance(result['metadata'], dict):
                        with open(mode_dir / "metadata.json", 'w') as f:
                            json.dump(result['metadata'], f, indent=2)
                    
                    if 'reference_images' in result:
                        with open(mode_dir / "reference_images.json", 'w') as f:
                            json.dump(result['reference_images'], f, indent=2)
                    
                    # Print summary
                    print_info(f"  Mode used: {result.get('mode_used', 'unknown')}")
                    if 'reference_images' in result:
                        print_info(f"  Reference images: {len(result.get('reference_images', []))}")
                    print_success(f"Results saved to: {mode_dir}")
                    
                else:
                    print_error(f"Request failed with status {response.status_code}")
                    print_error(f"Response: {response.text[:300]}")
                    
            except requests.exceptions.Timeout:
                print_error(f"Request timeout after {timeout}s")
            except Exception as e:
                print_error(f"Request failed: {e}")


def main():
    """Main routine"""
    print_header("LLM Input Debugging Tool")
    
    print_info("This tool captures all inputs sent to the LLM for comparison")
    print_info("It tests multiple modes (baseline, RAG, RAG+embeddings)")
    print_info("")
    
    # Setup output
    output_dir = setup_output_directory()
    print_info(f"Output directory: {output_dir}")
    print_info("")
    
    # Run debug
    run_debug_inference(output_dir)
    
    print_header("Debug Complete")
    print_info(f"All inputs and outputs saved to: {output_dir}")
    print_info("")
    print_info("Files saved:")
    print_info("  - service_info.json: Service configuration and health")
    print_info("  - advisor_metadata_complete.json: Full advisor metadata")
    print_info("  - 01_system_prompt.txt: Base system prompt")
    print_info("  - 02_advisor_prompt.txt: Base advisor prompt")
    print_info("")
    print_info("For each mode (baseline, rag, rag+embeddings):")
    print_info("  - mode_X_<name>/request_config.json: Request parameters")
    print_info("  - mode_X_<name>/response_complete.json: Full LLM response")
    print_info("  - mode_X_<name>/mode_used.txt: Mode that was actually used")
    print_info("  - mode_X_<name>/metadata.json: Response metadata")
    print_info("  - mode_X_<name>/reference_images.json: Advisor photo references (if RAG)")
    print_info("")
    print_success("✓ Debug logging complete")


if __name__ == "__main__":
    main()
