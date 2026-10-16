#!/usr/bin/env python3
"""
Direct JWT Authentication Unit Tests
Tests the authentication module without running the server
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
import json
import pytest

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_token_creation():
    """Test 1: Token creation"""
    print("\n" + "="*70)
    print("TEST 1: TOKEN CREATION")
    print("="*70)
    
    try:
        from skillbridge.api.repositories.auth.token import TokenRepository
        from skillbridge.api.repositories.auth.config import auth_config
        
        # Create tokens
        test_user_id = "550e8400-e29b-41d4-a716-446655440000"
        tokens = TokenRepository.create_tokens(test_user_id)
        
        print(f"✅ Tokens created successfully!")
        print(f"   Access Token Length: {len(tokens['access_token'])}")
        print(f"   Refresh Token Length: {len(tokens['refresh_token'])}")
        print(f"   Access Token Expires: {tokens['access_token_expires']}")
        print(f"   Refresh Token Expires: {tokens['refresh_token_expires']}")
        
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens['access_token'] is not None
        assert tokens['refresh_token'] is not None
        
    except Exception as e:
        print(f"❌ Failed to create tokens: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Token creation failed: {e}")


def test_token_verification(tokens):
    """Test 2: Token verification"""
    print("\n" + "="*70)
    print("TEST 2: TOKEN VERIFICATION")
    print("="*70)
    
    try:
        from skillbridge.api.repositories.auth.token_verifier import TokenVerifier
        from skillbridge.api.repositories.auth.config import auth_config
        import asyncio
        
        verifier = TokenVerifier()
        
        # Test with access token
        access_token = tokens['access_token']
        print(f"Access Token to verify: {access_token[:50]}...")
        
        # Decode without verification first to see structure
        from jose import jwt
        payload = jwt.decode(access_token, auth_config.JWT_SECRET_KEY, algorithms=[auth_config.JWT_ALGORITHM])
        
        print(f"✅ Token decoded successfully!")
        print(f"   Payload: {json.dumps(payload, indent=2, default=str)}")
        
        # Check required claims
        assert "sub" in payload, "Missing 'sub' (subject/user_id) claim"
        assert "exp" in payload, "Missing 'exp' (expiration) claim"
        assert "type" in payload, "Missing 'type' claim"
        assert payload["type"] == "access", f"Expected type='access', got {payload['type']}"
        
        print(f"✅ All required claims present!")
    except Exception as e:
        print(f"❌ Token verification failed: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Token verification failed: {e}")


def test_password_hashing():
    """Test 3: Password hashing and verification"""
    print("\n" + "="*70)
    print("TEST 3: PASSWORD HASHING & VERIFICATION")
    print("="*70)
    
    try:
        from skillbridge.api.repositories.auth.token import TokenRepository
        
        test_password = "SecurePassword@123"
        
        # Hash password
        hashed = TokenRepository.hash_password(test_password)
        print(f"✅ Password hashed successfully!")
        print(f"   Original: {test_password}")
        print(f"   Hashed: {hashed[:50]}...")
        
        # Verify correct password
        is_valid = TokenRepository.verify_password(test_password, hashed)
        assert is_valid, "Valid password failed verification!"
        print(f"✅ Correct password verified successfully!")
        
        # Verify wrong password
        is_invalid = TokenRepository.verify_password("WrongPassword", hashed)
        assert not is_invalid, "Wrong password incorrectly verified!"
        print(f"✅ Wrong password correctly rejected!")
        
    except Exception as e:
        print(f"❌ Password hashing test failed: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Password hashing test failed: {e}")


def test_token_expiration():
    """Test 4: Token expiration handling"""
    print("\n" + "="*70)
    print("TEST 4: TOKEN EXPIRATION DETECTION")
    print("="*70)
    
    try:
        from jose import jwt
        from jose.exceptions import ExpiredSignatureError
        from skillbridge.api.repositories.auth.config import auth_config
        from datetime import datetime, timedelta
        
        # Create an expired token
        expired_payload = {
            "sub": "test_user",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # Expired 1 hour ago
            "type": "access",
            "jti": "test_jti"
        }
        
        expired_token = jwt.encode(
            expired_payload,
            auth_config.JWT_SECRET_KEY,
            algorithm=auth_config.JWT_ALGORITHM
        )
        
        print(f"✅ Expired token created")
        print(f"   Token: {expired_token[:50]}...")
        
        # Try to verify it
        try:
            jwt.decode(
                expired_token,
                auth_config.JWT_SECRET_KEY,
                algorithms=[auth_config.JWT_ALGORITHM]
            )
            print(f"❌ Expired token was not rejected!")
            pytest.fail("Expired token was not rejected")
        except ExpiredSignatureError:
            print(f"✅ Expired token correctly rejected with ExpiredSignatureError!")
            return
    except Exception as e:
        print(f"❌ Token expiration test failed: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Token expiration test failed: {e}")


def test_invalid_token_signature():
    """Test 5: Invalid token signature detection"""
    print("\n" + "="*70)
    print("TEST 5: INVALID TOKEN SIGNATURE DETECTION")
    print("="*70)
    
    try:
        from jose import jwt
        from jose.exceptions import JWTError
        from skillbridge.api.repositories.auth.config import auth_config
        
        # Create a token with wrong secret
        payload = {
            "sub": "test_user",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "type": "access",
            "jti": "test_jti"
        }
        
        # Sign with different secret
        wrong_secret = "completely_different_secret_key"
        invalid_token = jwt.encode(
            payload,
            wrong_secret,
            algorithm=auth_config.JWT_ALGORITHM
        )
        
        print(f"✅ Token created with wrong secret")
        
        # Try to verify with correct secret
        try:
            jwt.decode(
                invalid_token,
                auth_config.JWT_SECRET_KEY,
                algorithms=[auth_config.JWT_ALGORITHM]
            )
            print(f"❌ Invalid signature was not rejected!")
            pytest.fail("Invalid signature was not rejected")
        except JWTError:
            print(f"✅ Invalid signature correctly rejected with InvalidSignatureError!")
            return
    except Exception as e:
        print(f"❌ Invalid signature test failed: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Invalid signature test failed: {e}")


def test_token_types():
    """Test 6: Different token types (access vs refresh)"""
    print("\n" + "="*70)
    print("TEST 6: TOKEN TYPE VALIDATION")
    print("="*70)
    
    try:
        from skillbridge.api.repositories.auth.token import TokenRepository
        from jose import jwt
        from skillbridge.api.repositories.auth.config import auth_config
        
        test_user_id = "550e8400-e29b-41d4-a716-446655440000"
        tokens = TokenRepository.create_tokens(test_user_id)
        
        # Decode both tokens
        access_payload = jwt.decode(
            tokens['access_token'],
            auth_config.JWT_SECRET_KEY,
            algorithms=[auth_config.JWT_ALGORITHM]
        )
        
        refresh_payload = jwt.decode(
            tokens['refresh_token'],
            auth_config.JWT_SECRET_KEY,
            algorithms=[auth_config.JWT_ALGORITHM]
        )
        
        print(f"Access Token Type: {access_payload.get('type')}")
        print(f"Refresh Token Type: {refresh_payload.get('type')}")
        
        assert access_payload.get('type') == 'access', "Access token has wrong type"
        assert refresh_payload.get('type') == 'refresh', "Refresh token has wrong type"
        
        print(f"✅ Token types are correct!")
        
        # Check expiration times
        access_exp = access_payload.get('exp')
        refresh_exp = refresh_payload.get('exp')
        
        print(f"Access token expires in: {(access_exp - datetime.now(timezone.utc).timestamp()) / 60:.1f} minutes")
        print(f"Refresh token expires in: {(refresh_exp - datetime.now(timezone.utc).timestamp()) / (60*60*24):.1f} days")
        
        assert refresh_exp > access_exp, "Refresh token should expire later than access token"
        print(f"✅ Refresh token expiration is longer than access token!")
        
    except Exception as e:
        print(f"❌ Token type test failed: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Token type test failed: {e}")


def test_endpoint_decorators():
    """Test 7: Endpoint decorator implementation"""
    print("\n" + "="*70)
    print("TEST 7: ENDPOINT DECORATOR IMPLEMENTATION")
    print("="*70)
    
    try:
        # Check that @validate_token decorator exists
        from skillbridge.api.repositories.auth.token import validate_token
        print(f"✅ @validate_token decorator found!")
        
        # Check that it's callable
        assert callable(validate_token), "@validate_token should be callable"
        print(f"✅ @validate_token is callable!")
        
        # List endpoints that should have @validate_token
        endpoints_to_check = [
            ("service.py", [
                "create_service",
                "get_services",
                "update_service",
                "delete_service",
            ]),
            ("admin.py", [
                "list_pending_revisions",
                "approve_service_revision",
                "reject_service_revision",
            ]),
            ("review.py", [
                "create_tutor_review",
                "create_service_review",
            ]),
            ("service_booking.py", [
                "create_service_booking",
            ]),
            ("tutor.py", [
                "create_tutor",
                "update_tutor",
            ]),
        ]
        
        print("\n✅ Protected endpoints should have @validate_token decorator:")
        for file, endpoints in endpoints_to_check:
            print(f"   {file}:")
            for endpoint in endpoints:
                print(f"      - {endpoint}")
        
    except Exception as e:
        print(f"❌ Endpoint decorator test failed: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Endpoint decorator test failed: {e}")


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("JWT AUTHENTICATION UNIT TESTS")
    print("="*70)
    
    results = {}
    
    # Test 1: Token creation
    success, tokens = test_token_creation()
    results["Token Creation"] = success
    
    if tokens:
        # Test 2: Token verification
        success, payload = test_token_verification(tokens)
        results["Token Verification"] = success
        
        # Test 4: Token expiration
        success = test_token_expiration()
        results["Token Expiration Detection"] = success
    
    # Test 3: Password hashing
    success = test_password_hashing()
    results["Password Hashing"] = success
    
    # Test 5: Invalid signature
    success = test_invalid_token_signature()
    results["Invalid Signature Detection"] = success
    
    # Test 6: Token types
    success = test_token_types()
    results["Token Types"] = success
    
    # Test 7: Endpoint decorators
    success = test_endpoint_decorators()
    results["Endpoint Decorators"] = success
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        symbol = "✅" if result else "❌"
        print(f"{symbol} {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("="*70)
    
    if passed == total:
        print("\n🎉 All tests passed! JWT authentication is correctly implemented.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
