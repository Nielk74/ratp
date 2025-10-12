#!/usr/bin/env python
"""Comprehensive endpoint validation tests for RATP Live Tracker."""

import httpx
import sys
import time
from typing import Dict, Any, Tuple


BASE_URL = "http://localhost:8000"
TIMEOUT = 10.0


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_test(name: str, status: str, message: str = ""):
    """Print formatted test result."""
    if status == "PASS":
        symbol = f"{Colors.GREEN}✓{Colors.RESET}"
        color = Colors.GREEN
    elif status == "FAIL":
        symbol = f"{Colors.RED}✗{Colors.RESET}"
        color = Colors.RED
    else:  # WARN
        symbol = f"{Colors.YELLOW}⚠{Colors.RESET}"
        color = Colors.YELLOW

    print(f"{symbol} {Colors.BOLD}{name}{Colors.RESET}: {color}{status}{Colors.RESET}", end="")
    if message:
        print(f" - {message}")
    else:
        print()


def probe_endpoint(
    client: httpx.Client,
    method: str,
    path: str,
    expected_status: int = 200,
    check_keys: list = None,
    params: Dict = None
) -> Tuple[bool, str]:
    """Test an endpoint and return success status and message."""
    try:
        url = f"{BASE_URL}{path}"
        response = client.request(method, url, params=params, timeout=TIMEOUT)

        if response.status_code != expected_status:
            return False, f"Expected {expected_status}, got {response.status_code}"

        if check_keys:
            try:
                data = response.json()
                for key in check_keys:
                    if key not in data:
                        return False, f"Missing key: {key}"
            except Exception as e:
                return False, f"Invalid JSON: {str(e)}"

        return True, f"Status {response.status_code}, response valid"

    except httpx.TimeoutException:
        return False, "Request timed out"
    except httpx.ConnectError:
        return False, "Connection failed - is server running?"
    except Exception as e:
        return False, f"Error: {str(e)}"


def main():
    """Run comprehensive endpoint tests."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}RATP Live Tracker - Endpoint Validation Tests{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}\n")

    print(f"{Colors.BOLD}Base URL:{Colors.RESET} {BASE_URL}\n")

    tests_passed = 0
    tests_failed = 0
    tests_warned = 0

    with httpx.Client() as client:
        # Test 1: Health Check
        print(f"\n{Colors.BOLD}Core Endpoints:{Colors.RESET}")
        success, msg = probe_endpoint(client, "GET", "/health", check_keys=["status"])
        if success:
            print_test("Health Check", "PASS", msg)
            tests_passed += 1
        else:
            print_test("Health Check", "FAIL", msg)
            tests_failed += 1
            print(f"\n{Colors.RED}Server is not responding. Aborting tests.{Colors.RESET}")
            return 1

        # Test 2: Root Endpoint
        success, msg = probe_endpoint(client, "GET", "/", check_keys=["name", "version", "status"])
        if success:
            print_test("Root Info", "PASS", msg)
            tests_passed += 1
        else:
            print_test("Root Info", "FAIL", msg)
            tests_failed += 1

        # Test 3: API Documentation
        success, msg = probe_endpoint(client, "GET", "/docs")
        if success:
            print_test("API Docs (Swagger)", "PASS", msg)
            tests_passed += 1
        else:
            print_test("API Docs (Swagger)", "WARN", msg)
            tests_warned += 1

        # Lines API Tests
        print(f"\n{Colors.BOLD}Lines API:{Colors.RESET}")

        # Test 4: Get all lines
        success, msg = probe_endpoint(client, "GET", "/api/lines/", check_keys=["lines", "count"])
        if success:
            print_test("GET /api/lines/", "PASS", msg)
            tests_passed += 1
        else:
            print_test("GET /api/lines/", "FAIL", msg)
            tests_failed += 1

        # Test 5: Filter lines by type
        success, msg = probe_endpoint(
            client, "GET", "/api/lines/",
            params={"transport_type": "metro"},
            check_keys=["lines", "count"]
        )
        if success:
            print_test("GET /api/lines/?transport_type=metro", "PASS", msg)
            tests_passed += 1
        else:
            print_test("GET /api/lines/?transport_type=metro", "FAIL", msg)
            tests_failed += 1

        # Test 6: Get stations for a line
        success, msg = probe_endpoint(client, "GET", "/api/lines/metros/1/stations")
        if success:
            print_test("GET /api/lines/metros/1/stations", "PASS", msg)
            tests_passed += 1
        else:
            print_test("GET /api/lines/metros/1/stations", "WARN", msg)
            tests_warned += 1

        # Traffic API Tests
        print(f"\n{Colors.BOLD}Traffic API:{Colors.RESET}")

        # Test 7: Get all traffic
        success, msg = probe_endpoint(client, "GET", "/api/traffic/", expected_status=200)
        if success:
            print_test("GET /api/traffic/", "PASS", msg)
            tests_passed += 1
        else:
            print_test("GET /api/traffic/", "WARN", f"{msg} (External API may be unavailable)")
            tests_warned += 1

        # Test 8: Get traffic for specific line
        success, msg = probe_endpoint(
            client, "GET", "/api/traffic/",
            params={"line_code": "1"}
        )
        if success:
            print_test("GET /api/traffic/?line_code=1", "PASS", msg)
            tests_passed += 1
        else:
            print_test("GET /api/traffic/?line_code=1", "WARN", f"{msg} (External API may be unavailable)")
            tests_warned += 1

        # Geolocation API Tests
        print(f"\n{Colors.BOLD}Geolocation API:{Colors.RESET}")

        # Test 9: Find nearest stations
        success, msg = probe_endpoint(
            client, "GET", "/api/geo/nearest",
            params={"lat": 48.8584, "lon": 2.3470},
            check_keys=["results", "count"]
        )
        if success:
            print_test("GET /api/geo/nearest (Châtelet)", "PASS", msg)
            tests_passed += 1
        else:
            print_test("GET /api/geo/nearest (Châtelet)", "FAIL", msg)
            tests_failed += 1

        # Test 10: Nearest stations with filters
        success, msg = probe_endpoint(
            client, "GET", "/api/geo/nearest",
            params={"lat": 48.8584, "lon": 2.3470, "max_results": 3, "max_distance": 2},
            check_keys=["results", "count"]
        )
        if success:
            print_test("GET /api/geo/nearest (with filters)", "PASS", msg)
            tests_passed += 1
        else:
            print_test("GET /api/geo/nearest (with filters)", "FAIL", msg)
            tests_failed += 1

        # Test 11: Missing required parameters
        success, msg = test_endpoint(
            client, "GET", "/api/geo/nearest",
            expected_status=422  # Validation error
        )
        if success:
            print_test("GET /api/geo/nearest (validation)", "PASS", "Correctly rejects missing params")
            tests_passed += 1
        else:
            print_test("GET /api/geo/nearest (validation)", "FAIL", msg)
            tests_failed += 1

        # Webhook API Tests
        print(f"\n{Colors.BOLD}Webhook API:{Colors.RESET}")

        # Test 12: List webhooks
        success, msg = test_endpoint(
            client, "GET", "/api/webhooks/",
            check_keys=["subscriptions", "count"]
        )
        if success:
            print_test("GET /api/webhooks/", "PASS", msg)
            tests_passed += 1
        else:
            print_test("GET /api/webhooks/", "FAIL", msg)
            tests_failed += 1

        # Test 13: Create webhook (will fail without valid URL, but should handle gracefully)
        try:
            response = client.post(
                f"{BASE_URL}/api/webhooks/",
                json={
                    "webhook_url": "https://discord.com/api/webhooks/123/test",
                    "line_code": "1",
                    "severity_filter": ["high", "critical"]
                },
                timeout=TIMEOUT
            )
            if response.status_code in [200, 201]:
                print_test("POST /api/webhooks/", "PASS", f"Status {response.status_code}")
                tests_passed += 1
            else:
                print_test("POST /api/webhooks/", "WARN", f"Status {response.status_code}")
                tests_warned += 1
        except Exception as e:
            print_test("POST /api/webhooks/", "WARN", str(e))
            tests_warned += 1

        # Schedules API Tests
        print(f"\n{Colors.BOLD}Schedules API:{Colors.RESET}")

        # Test 14: Get schedules (may fail if external API is down)
        success, msg = test_endpoint(
            client, "GET", "/api/schedules/metros/1/chatelet/A"
        )
        if success:
            print_test("GET /api/schedules/metros/1/chatelet/A", "PASS", msg)
            tests_passed += 1
        else:
            print_test("GET /api/schedules/metros/1/chatelet/A", "WARN", f"{msg} (External API may be unavailable)")
            tests_warned += 1

    # Summary
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}Test Summary:{Colors.RESET}\n")

    total_tests = tests_passed + tests_failed + tests_warned
    print(f"{Colors.GREEN}✓ Passed:{Colors.RESET}  {tests_passed}/{total_tests}")
    print(f"{Colors.YELLOW}⚠ Warnings:{Colors.RESET} {tests_warned}/{total_tests}")
    print(f"{Colors.RED}✗ Failed:{Colors.RESET}  {tests_failed}/{total_tests}")

    print(f"\n{Colors.BOLD}Overall Status:{Colors.RESET} ", end="")
    if tests_failed == 0 and tests_passed > 0:
        print(f"{Colors.GREEN}ALL TESTS PASSED{Colors.RESET} ✓")
        return 0
    elif tests_failed == 0 and tests_warned > 0:
        print(f"{Colors.YELLOW}PASSED WITH WARNINGS{Colors.RESET} ⚠")
        return 0
    else:
        print(f"{Colors.RED}SOME TESTS FAILED{Colors.RESET} ✗")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Tests interrupted by user{Colors.RESET}")
        sys.exit(1)
