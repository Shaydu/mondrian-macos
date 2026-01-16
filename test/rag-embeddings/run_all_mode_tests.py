#!/usr/bin/env python3
"""
Unified Mode Test Suite Runner
================================
Runs all four analysis modes (baseline, rag, lora, rag+lora) in sequence.
Collects results and generates a comprehensive report.

Usage:
    python3 run_all_mode_tests.py              # Run all tests
    python3 run_all_mode_tests.py --verbose    # Run with detailed output
    python3 run_all_mode_tests.py --mode=rag   # Run specific mode
    python3 run_all_mode_tests.py --help       # Show help

Exit Codes:
    0 = All tests passed
    1 = One or more tests failed
"""

import sys
import os
import json
import time
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
NC = '\033[0m'

# Configuration
PROJECT_DIR = Path(__file__).parent.parent.parent
TEST_DIR = PROJECT_DIR / "test" / "rag-embeddings"
LOG_DIR = PROJECT_DIR / "logs" / "tests"
RESULTS_DIR = TEST_DIR / "results"

# Create output directories
LOG_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Test configurations
TESTS = [
    {"name": "baseline", "file": "test_mode_baseline.py", "mode": "base"},
    {"name": "rag", "file": "test_mode_rag.py", "mode": "rag"},
    {"name": "lora", "file": "test_mode_lora.py", "mode": "lora"},
    {"name": "rag+lora", "file": "test_mode_lora_rag.py", "mode": "rag_lora"},
]


@dataclass
class TestResult:
    """Represents a single test result."""
    name: str
    mode: str
    status: str  # "passed", "failed", "skipped"
    duration: float
    error: Optional[str] = None
    details: Optional[Dict] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class TestSuite:
    """Manages execution and reporting of mode tests."""
    
    def __init__(self, verbose: bool = False, specific_mode: Optional[str] = None):
        self.verbose = verbose
        self.specific_mode = specific_mode
        self.results: List[TestResult] = []
        self.start_time = None
        self.end_time = None
    
    def print_header(self, text: str):
        """Print formatted header."""
        print(f"\n{BLUE}{'='*80}{NC}")
        print(f"{BLUE}{text:^80}{NC}")
        print(f"{BLUE}{'='*80}{NC}\n")
    
    def print_subheader(self, text: str):
        """Print formatted subheader."""
        print(f"\n{CYAN}→ {text}{NC}")
    
    def print_success(self, text: str):
        """Print success message."""
        print(f"  {GREEN}✓{NC} {text}")
    
    def print_fail(self, text: str):
        """Print failure message."""
        print(f"  {RED}✗{NC} {text}")
    
    def print_info(self, text: str):
        """Print info message."""
        print(f"  {YELLOW}ℹ{NC} {text}")
    
    def print_skip(self, text: str):
        """Print skip message."""
        print(f"  {YELLOW}⊘{NC} {text}")
    
    def check_prerequisites(self) -> bool:
        """Check if test environment is ready."""
        self.print_header("Checking Prerequisites")
        
        # Check if test image exists, and find one if not
        test_image_path = Path("source/photo-B371453D-558B-40C5-910D-72940700046C-8d4c2233.jpg")
        if not test_image_path.exists():
            self.print_info(f"Test image not found, looking for alternatives...")
            source_dir = Path("source")
            jpg_files = list(source_dir.glob("*.jpg"))
            if jpg_files:
                test_image_path = jpg_files[0]
                self.print_success(f"Using test image: {test_image_path}")
            else:
                self.print_fail("No test images found in source/ directory")
                return False
        else:
            self.print_success(f"Test image found: {test_image_path}")
        
        # Check AI Advisor Service
        try:
            import requests
            response = requests.get("http://localhost:5100/health", timeout=5)
            if response.status_code == 200:
                self.print_success("AI Advisor Service running at http://localhost:5100")
                return True
            else:
                self.print_fail(f"Service returned status {response.status_code}")
                return False
        except Exception as e:
            self.print_fail(f"AI Advisor Service not available: {e}")
            self.print_info("Start services with: ./mondrian.sh --restart")
            return False
    
    def run_test(self, test_config: Dict) -> TestResult:
        """Run a single test."""
        test_name = test_config["name"]
        test_file = test_config["file"]
        test_path = TEST_DIR / test_file
        
        self.print_subheader(f"Running {test_name.upper()} mode test")
        
        if not test_path.exists():
            self.print_fail(f"Test file not found: {test_path}")
            return TestResult(
                name=test_name,
                mode=test_config["mode"],
                status="failed",
                duration=0,
                error=f"Test file not found: {test_file}"
            )
        
        start_time = time.time()
        
        try:
            # Find a test image
            test_image = None
            preferred_image = TEST_DIR / "source" / "photo-B371453D-558B-40C5-910D-72940700046C-8d4c2233.jpg"
            if preferred_image.exists():
                test_image = str(preferred_image)
            else:
                source_dir = TEST_DIR / "source"
                if source_dir.exists():
                    jpg_files = list(source_dir.glob("*.jpg"))
                    if jpg_files:
                        test_image = str(jpg_files[0])
            
            if not test_image:
                # Try parent directory
                parent_source = TEST_DIR.parent.parent / "source"
                if parent_source.exists():
                    jpg_files = list(parent_source.glob("*.jpg"))
                    if jpg_files:
                        test_image = str(jpg_files[0])
            
            # Run test script
            cmd = [sys.executable, str(test_path)]
            if self.verbose:
                cmd.append("--verbose")
            
            # Set environment with test image path if found
            env = os.environ.copy()
            if test_image:
                env["TEST_IMAGE_PATH"] = test_image
            
            self.print_info(f"Running: {' '.join(cmd)}")
            if test_image:
                self.print_info(f"Using test image: {test_image}")
            
            result = subprocess.run(
                cmd,
                cwd=str(TEST_DIR),
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                env=env
            )
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                self.print_success(f"{test_name} test passed ({duration:.1f}s)")
                return TestResult(
                    name=test_name,
                    mode=test_config["mode"],
                    status="passed",
                    duration=duration,
                    details={"stdout": result.stdout[-500:] if result.stdout else ""}
                )
            else:
                self.print_fail(f"{test_name} test failed ({duration:.1f}s)")
                error_msg = result.stderr if result.stderr else result.stdout
                if self.verbose:
                    print(f"\n{RED}Error Output:{NC}\n{error_msg}\n")
                return TestResult(
                    name=test_name,
                    mode=test_config["mode"],
                    status="failed",
                    duration=duration,
                    error=error_msg[-500:] if error_msg else "Unknown error"
                )
        
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            self.print_fail(f"{test_name} test timed out ({duration:.1f}s)")
            return TestResult(
                name=test_name,
                mode=test_config["mode"],
                status="failed",
                duration=duration,
                error="Test timed out after 600 seconds"
            )
        
        except Exception as e:
            duration = time.time() - start_time
            self.print_fail(f"{test_name} test error: {e}")
            return TestResult(
                name=test_name,
                mode=test_config["mode"],
                status="failed",
                duration=duration,
                error=str(e)
            )
    
    def run_all(self) -> int:
        """Run all tests and return exit code."""
        self.print_header("🧪 MONDRIAN MODE TEST SUITE")
        print(f"Testing all analysis modes: baseline, rag, lora, rag+lora")
        print(f"Results will be saved to: {RESULTS_DIR}")
        
        # Check prerequisites
        if not self.check_prerequisites():
            return 1
        
        self.start_time = time.time()
        
        # Run tests
        tests_to_run = TESTS
        if self.specific_mode:
            tests_to_run = [t for t in TESTS if t["name"] == self.specific_mode]
            if not tests_to_run:
                self.print_fail(f"Unknown mode: {self.specific_mode}")
                return 1
        
        for test_config in tests_to_run:
            result = self.run_test(test_config)
            self.results.append(result)
        
        self.end_time = time.time()
        
        # Print summary
        self.print_summary()
        
        # Save results
        self.save_results()
        
        # Return exit code
        failed_count = sum(1 for r in self.results if r.status == "failed")
        return 1 if failed_count > 0 else 0
    
    def print_summary(self):
        """Print test summary."""
        self.print_header("📊 TEST SUMMARY")
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "passed")
        failed = sum(1 for r in self.results if r.status == "failed")
        total_duration = self.end_time - self.start_time
        
        # Results table
        print(f"{'Mode':<15} {'Status':<12} {'Duration':<12} {'Result':<40}")
        print("-" * 80)
        
        for result in self.results:
            status_str = "PASS" if result.status == "passed" else "FAIL"
            status_color = GREEN if result.status == "passed" else RED
            
            error_str = (result.error[:37] + "...") if result.error and len(result.error) > 40 else (result.error or "")
            
            print(f"{result.name:<15} {status_color}{status_str:<12}{NC} {result.duration:>8.1f}s     {error_str:<40}")
        
        print("-" * 80)
        print(f"{'TOTAL:':<15} {passed}/{total} passed  {total_duration:.1f}s total")
        
        # Color-coded result
        if failed == 0:
            print(f"\n{GREEN}✓ All tests passed!{NC}")
        else:
            print(f"\n{RED}✗ {failed} test(s) failed{NC}")
    
    def save_results(self):
        """Save test results to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = RESULTS_DIR / f"test_results_{timestamp}.json"
        
        # Prepare results
        results_data = {
            "timestamp": datetime.now().isoformat(),
            "total_duration": self.end_time - self.start_time,
            "tests": [asdict(r) for r in self.results],
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for r in self.results if r.status == "passed"),
                "failed": sum(1 for r in self.results if r.status == "failed"),
            }
        }
        
        with open(results_file, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"\n{CYAN}Results saved to: {results_file}{NC}")
        
        # Also save to a summary file
        summary_file = RESULTS_DIR / "latest_results.json"
        with open(summary_file, 'w') as f:
            json.dump(results_data, f, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Run Mondrian mode analysis tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 run_all_mode_tests.py              # Run all tests
  python3 run_all_mode_tests.py --verbose    # Run with detailed output
  python3 run_all_mode_tests.py --mode=rag   # Run only RAG mode test
  python3 run_all_mode_tests.py --mode=lora  # Run only LoRA mode test
        """
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed output from each test"
    )
    
    parser.add_argument(
        "-m", "--mode",
        choices=["baseline", "rag", "lora", "rag+lora"],
        help="Run only a specific analysis mode"
    )
    
    args = parser.parse_args()
    
    # Run test suite
    suite = TestSuite(verbose=args.verbose, specific_mode=args.mode)
    exit_code = suite.run_all()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
