#!/usr/bin/env python3
"""
Test JWT Authentication Module through the get_services endpoint
This script tests:
1. Login to get JWT tokens (access_token and refresh_token)
2. Using the access_token to call get_services endpoint
3. Verify token validation and authorization
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from uuid import UUID

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import httpx
from httpx import AsyncClient


# Configuration
BASE_URL = "http://127.0.0.1:8000/api"
API_V1_URL = f"{BASE_URL}/v1"

# Test users (you may need to update these based on your test database)
TEST_USERS = {
    "student": {
        "email": "student@test.com",
        "password": "Student@123",
        "role_id": "student_role_uuid"  # You'll need to get this from your database
    },
    "tutor": {
        "email": "tutor@test.com", 
        "password": "Tutor@123",
        "role_id": "tutor_role_uuid"  # You'll need to get this from your database
    }
}


class JWTAuthTester:
    """Test JWT authentication through various endpoints"""
    
    def __init__(self, base_url: str = API_V1_URL):
        self.base_url = base_url
        self.client: Optional[AsyncClient] = None
        self.tokens = {}
        
    async def __aenter__(self):
        self.client = AsyncClient(base_url=self.base_url, timeout=10.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    async def login(self, email: str, password: str, role_id: str) -> Dict[str, Any]:
        """
        Test 1: Login to get tokens
        POST /auth/login
        """
        print(f"\n{'='*60}")
        print(f"TEST 1: LOGIN")
        print(f"{'='*60}")
        print(f"Email: {email}")
        print(f"Role ID: {role_id}")
        
        payload = {
            "email": email,
            "password": password,
            "role_id": role_id
        }
        
        try:
            response = await self.client.post(
                "/auth/login/",
                json=payload
            )
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Login successful!")
                print(f"Response: {json.dumps(data, indent=2, default=str)}")
                
                # Store tokens
                self.tokens = {
                    "access_token": data.get("data", {}).get("access_token"),
                    "refresh_token": data.get("data", {}).get("refresh_token"),
                    "user_id": data.get("data", {}).get("user_id")
                }
                
                return self.tokens
            else:
                print(f"❌ Login failed!")
                print(f"Response: {response.text}")
                return None
                
        except httpx.HTTPError as e:
            print(f"❌ HTTP Error: {e}")
            return None
    
    async def get_services_with_token(self, access_token: str) -> Dict[str, Any]:
        """
        Test 2: Get services with valid JWT token
        GET /services/services/
        """
        print(f"\n{'='*60}")
        print(f"TEST 2: GET SERVICES WITH VALID TOKEN")
        print(f"{'='*60}")
        print(f"Token: {access_token[:50]}...")
        
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        try:
            response = await self.client.get(
                "/services/services/",
                headers=headers
            )
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Successfully retrieved services!")
                print(f"Services count: {len(data.get('data', []))}")
                print(f"Response preview: {json.dumps(data, indent=2, default=str)[:500]}...")
                return data
            else:
                print(f"❌ Failed to retrieve services!")
                print(f"Response: {response.text}")
                return None
                
        except httpx.HTTPError as e:
            print(f"❌ HTTP Error: {e}")
            return None
    
    async def get_services_without_token(self) -> Dict[str, Any]:
        """
        Test 3: Try to get services WITHOUT token (should fail)
        GET /services/services/
        """
        print(f"\n{'='*60}")
        print(f"TEST 3: GET SERVICES WITHOUT TOKEN (SHOULD FAIL)")
        print(f"{'='*60}")
        
        try:
            response = await self.client.get("/services/services/")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 401:
                print(f"✅ Correctly rejected request without token!")
                print(f"Response: {response.text}")
                return {"success": True, "error_expected": True}
            else:
                print(f"⚠️  Request succeeded without token (authorization not enforced?)")
                print(f"Response: {response.text}")
                return {"success": False, "error_expected": False}
                
        except httpx.HTTPError as e:
            print(f"HTTP Error: {e}")
            return {"success": False}
    
    async def get_services_with_invalid_token(self) -> Dict[str, Any]:
        """
        Test 4: Try to get services with INVALID token (should fail)
        GET /services/services/
        """
        print(f"\n{'='*60}")
        print(f"TEST 4: GET SERVICES WITH INVALID TOKEN (SHOULD FAIL)")
        print(f"{'='*60}")
        
        invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.token"
        headers = {
            "Authorization": f"Bearer {invalid_token}"
        }
        
        try:
            response = await self.client.get(
                "/services/services/",
                headers=headers
            )
            print(f"Status Code: {response.status_code}")
            
            if response.status_code in [401, 400]:
                print(f"✅ Correctly rejected request with invalid token!")
                print(f"Response: {response.text}")
                return {"success": True, "error_expected": True}
            else:
                print(f"⚠️  Request succeeded with invalid token (validation not working?)")
                print(f"Response: {response.text}")
                return {"success": False, "error_expected": False}
                
        except httpx.HTTPError as e:
            print(f"HTTP Error: {e}")
            return {"success": False}
    
    async def refresh_token(self, refresh_token: str) -> Optional[str]:
        """
        Test 5: Refresh access token
        POST /auth/refresh
        """
        print(f"\n{'='*60}")
        print(f"TEST 5: REFRESH TOKEN")
        print(f"{'='*60}")
        print(f"Refresh Token: {refresh_token[:50]}...")
        
        payload = {
            "refresh_token": refresh_token
        }
        
        try:
            response = await self.client.post(
                "/auth/refresh/",
                json=payload
            )
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                new_access_token = data.get("access_token")
                print(f"✅ Successfully refreshed token!")
                print(f"New Access Token: {new_access_token[:50]}...")
                return new_access_token
            else:
                print(f"❌ Failed to refresh token!")
                print(f"Response: {response.text}")
                return None
                
        except httpx.HTTPError as e:
            print(f"❌ HTTP Error: {e}")
            return None
    
    async def run_all_tests(self):
        """Run all authentication tests"""
        print("\n" + "="*60)
        print("JWT AUTHENTICATION TEST SUITE")
        print("="*60)
        
        # For now, we'll test with hardcoded values
        # You'll need to update TEST_USERS with actual role UUIDs from your database
        
        results = {
            "login": False,
            "get_services_with_token": False,
            "get_services_without_token": False,
            "get_services_with_invalid_token": False,
            "refresh_token": False
        }
        
        # Get role UUIDs first - you need to fetch these from your database
        print("\n⚠️  Note: You need to provide valid role UUIDs in TEST_USERS")
        print("   These should be obtained from your database.")
        
        # For now, we'll ask the user to provide them
        student_role_id = input("\nEnter Student Role ID (UUID): ").strip()
        
        if not student_role_id:
            print("⚠️  Skipping login test - no role ID provided")
        else:
            # Test login
            tokens = await self.login("student@test.com", "Student@123", student_role_id)
            
            if tokens and tokens.get("access_token"):
                results["login"] = True
                
                # Test get services with valid token
                services = await self.get_services_with_token(tokens["access_token"])
                if services:
                    results["get_services_with_token"] = True
                
                # Test refresh token
                if tokens.get("refresh_token"):
                    new_token = await self.refresh_token(tokens["refresh_token"])
                    if new_token:
                        results["refresh_token"] = True
        
        # Test without token
        no_token_result = await self.get_services_without_token()
        if no_token_result.get("error_expected"):
            results["get_services_without_token"] = True
        
        # Test with invalid token
        invalid_token_result = await self.get_services_with_invalid_token()
        if invalid_token_result.get("error_expected"):
            results["get_services_with_invalid_token"] = True
        
        # Print summary
        self._print_summary(results)
        
        return results
    
    def _print_summary(self, results: Dict[str, bool]):
        """Print test summary"""
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        
        for test_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status}: {test_name}")
        
        total_tests = len(results)
        passed_tests = sum(1 for v in results.values() if v)
        
        print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("\n🎉 All tests passed! JWT authentication is working correctly.")
        else:
            print(f"\n⚠️  {total_tests - passed_tests} test(s) failed. Please review the output above.")


async def main():
    """Main test runner"""
    async with JWTAuthTester() as tester:
        try:
            await tester.run_all_tests()
        except KeyboardInterrupt:
            print("\n\nTests interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"\n\n❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    print("Starting JWT Authentication Tests...\n")
    print("Make sure your SkillBridge API is running on http://127.0.0.1:8000/api")
    print("You can start it with: python -m uvicorn src.skillbridge.app:app --reload\n")
    
    asyncio.run(main())
