#!/usr/bin/env python3
"""
Comprehensive JWT Authentication & API Testing Script
Tests all endpoints with and without authentication
"""

import asyncio
import json
import sys
from pathlib import Path
from subprocess import run, PIPE
from typing import Dict, Any, Optional

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

BASE_URL = "http://127.0.0.1:8000/api"
API_V1_URL = f"{BASE_URL}/v1"

class APITester:
    """Test API endpoints with JWT authentication"""
    
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        self.user_id = None
        self.results = {}
    
    def _run_curl(self, method: str, url: str, data: Optional[Dict] = None, 
                  headers: Optional[Dict] = None, allow_fail: bool = False) -> tuple[int, str]:
        """Run curl command and return status code and response"""
        cmd = ["curl", "-s", "-w", "\n%{http_code}", "-X", method, url]
        
        if headers:
            for key, val in headers.items():
                cmd.extend(["-H", f"{key}: {val}"])
        
        if data:
            cmd.extend(["-H", "Content-Type: application/json", "-d", json.dumps(data)])
        
        try:
            result = run(cmd, capture_output=True, text=True, timeout=10)
            output = result.stdout
            lines = output.rstrip().split('\n')
            status_code = int(lines[-1]) if lines[-1].isdigit() else 0
            response = '\n'.join(lines[:-1])
            return status_code, response
        except Exception as e:
            print(f"❌ cURL Error: {e}")
            return 0, str(e)
    
    def _print_test(self, name: str, status: bool, details: str = ""):
        """Print test result"""
        symbol = "✅" if status else "❌"
        print(f"{symbol} {name}")
        if details:
            print(f"   {details}")
        self.results[name] = status
    
    def test_login(self) -> bool:
        """Test 1: Login endpoint"""
        print("\n" + "="*70)
        print("TEST 1: LOGIN - Get JWT Tokens")
        print("="*70)
        
        # First, we need to get a valid role_id from database or create a test user
        # For now, let's try with a test email
        login_data = {
            "email": "student@example.com",
            "password": "SecurePassword@123",
            "role_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"  # Placeholder
        }
        
        status_code, response = self._run_curl(
            "POST",
            f"{API_V1_URL}/auth/login/",
            login_data
        )
        
        print(f"Status: {status_code}")
        print(f"Response: {response[:200]}...")
        
        if status_code == 200:
            try:
                data = json.loads(response)
                self.access_token = data.get("data", {}).get("access_token")
                self.refresh_token = data.get("data", {}).get("refresh_token")
                self.user_id = data.get("data", {}).get("user_id")
                self._print_test("Login", True, f"Got tokens for user {self.user_id}")
                return True
            except json.JSONDecodeError:
                self._print_test("Login", False, "Invalid JSON response")
                return False
        else:
            self._print_test("Login", False, f"Status {status_code}")
            return False
    
    def test_get_services_without_token(self) -> bool:
        """Test 2: Get services without token (should fail)"""
        print("\n" + "="*70)
        print("TEST 2: GET SERVICES WITHOUT TOKEN (Should Fail)")
        print("="*70)
        
        status_code, response = self._run_curl(
            "GET",
            f"{API_V1_URL}/services/services/"
        )
        
        print(f"Status: {status_code}")
        print(f"Response: {response[:200]}...")
        
        # Should return 401 or 403
        if status_code in [401, 403]:
            self._print_test("Get Services Without Token", True, 
                           f"Correctly rejected with {status_code}")
            return True
        else:
            self._print_test("Get Services Without Token", False, 
                           f"Expected 401/403, got {status_code}")
            return False
    
    def test_get_services_with_invalid_token(self) -> bool:
        """Test 3: Get services with invalid token (should fail)"""
        print("\n" + "="*70)
        print("TEST 3: GET SERVICES WITH INVALID TOKEN (Should Fail)")
        print("="*70)
        
        headers = {
            "Authorization": "Bearer invalid.token.here"
        }
        
        status_code, response = self._run_curl(
            "GET",
            f"{API_V1_URL}/services/services/",
            headers=headers
        )
        
        print(f"Status: {status_code}")
        print(f"Response: {response[:200]}...")
        
        if status_code in [401, 403]:
            self._print_test("Get Services With Invalid Token", True, 
                           f"Correctly rejected with {status_code}")
            return True
        else:
            self._print_test("Get Services With Invalid Token", False, 
                           f"Expected 401/403, got {status_code}")
            return False
    
    def test_get_services_with_token(self) -> bool:
        """Test 4: Get services with valid token"""
        print("\n" + "="*70)
        print("TEST 4: GET SERVICES WITH VALID TOKEN")
        print("="*70)
        
        if not self.access_token:
            print("⚠️  Skipping - no valid token from login")
            return False
        
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        status_code, response = self._run_curl(
            "GET",
            f"{API_V1_URL}/services/services/",
            headers=headers
        )
        
        print(f"Status: {status_code}")
        print(f"Response: {response[:300]}...")
        
        if status_code == 200:
            self._print_test("Get Services With Valid Token", True, 
                           "Successfully retrieved services")
            return True
        else:
            self._print_test("Get Services With Valid Token", False, 
                           f"Expected 200, got {status_code}")
            return False
    
    def test_refresh_token(self) -> bool:
        """Test 5: Refresh access token"""
        print("\n" + "="*70)
        print("TEST 5: REFRESH ACCESS TOKEN")
        print("="*70)
        
        if not self.refresh_token:
            print("⚠️  Skipping - no refresh token from login")
            return False
        
        refresh_data = {
            "refresh_token": self.refresh_token
        }
        
        status_code, response = self._run_curl(
            "POST",
            f"{API_V1_URL}/auth/refresh/",
            refresh_data
        )
        
        print(f"Status: {status_code}")
        print(f"Response: {response[:300]}...")
        
        if status_code == 200:
            try:
                data = json.loads(response)
                new_token = data.get("access_token")
                if new_token:
                    self._print_test("Refresh Token", True, 
                                   "Successfully got new access token")
                    # Update token for further tests
                    self.access_token = new_token
                    return True
            except json.JSONDecodeError:
                pass
        
        self._print_test("Refresh Token", False, f"Status {status_code}")
        return False
    
    def test_invalid_authorization_format(self) -> bool:
        """Test 6: Invalid authorization header format"""
        print("\n" + "="*70)
        print("TEST 6: INVALID AUTHORIZATION HEADER FORMAT (Should Fail)")
        print("="*70)
        
        headers = {
            "Authorization": "InvalidFormat token_here"
        }
        
        status_code, response = self._run_curl(
            "GET",
            f"{API_V1_URL}/services/services/",
            headers=headers
        )
        
        print(f"Status: {status_code}")
        print(f"Response: {response[:200]}...")
        
        if status_code in [401, 403]:
            self._print_test("Invalid Auth Format", True, 
                           f"Correctly rejected with {status_code}")
            return True
        else:
            self._print_test("Invalid Auth Format", False, 
                           f"Expected 401/403, got {status_code}")
            return False
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        
        passed = sum(1 for v in self.results.values() if v)
        total = len(self.results)
        
        for test_name, result in self.results.items():
            symbol = "✅" if result else "❌"
            print(f"{symbol} {test_name}")
        
        print(f"\n{'='*70}")
        print(f"Total: {passed}/{total} tests passed")
        print(f"{'='*70}")
        
        if passed == total:
            print("\n🎉 All tests passed! JWT authentication is working correctly.")
            return True
        else:
            print(f"\n⚠️  {total - passed} test(s) failed.")
            return False
    
    async def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*70)
        print("JWT AUTHENTICATION & API TESTING SUITE")
        print("="*70)
        print(f"\nBase URL: {API_V1_URL}")
        print("\nMake sure your API is running on http://127.0.0.1:8000/api")
        print("Start with: cd skillbridge-be && poetry run python -m uvicorn src.skillbridge.app:app --reload\n")
        
        # Run tests
        self.test_get_services_without_token()
        self.test_get_services_with_invalid_token()
        self.test_invalid_authorization_format()
        
        # Try login (may fail if no test user exists)
        if self.test_login():
            self.test_get_services_with_token()
            self.test_refresh_token()
        
        # Print summary
        return self.print_summary()


async def main():
    """Main test runner"""
    tester = APITester()
    try:
        success = await tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
