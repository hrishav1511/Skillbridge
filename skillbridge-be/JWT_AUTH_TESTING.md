# JWT Authentication Testing Guide

## Overview
This guide explains how to test the JWT authentication module through the `get_services` API endpoint. The JWT authentication system has been fully implemented with token generation, validation, and refresh mechanisms.

## Architecture

### Key Components

1. **TokenRepository** (`src/skillbridge/api/repositories/auth/token.py`)
   - Generates JWT access and refresh tokens
   - Verifies and validates tokens
   - Extracts user information from tokens
   - Handles token refresh

2. **Token Verification** (`src/skillbridge/api/repositories/auth/token_verifier.py`)
   - Decodes and validates JWT signatures
   - Checks token expiration
   - Returns complete token payload

3. **Dependencies**
   - `get_current_user()`: FastAPI dependency to inject complete user data from JWT
   - `validate_token()`: Decorator to protect endpoints
   - `get_user_id()`: Extract just the user_id from token

4. **Endpoints**
   - `POST /api/v1/auth/login/` - Login and get tokens
   - `POST /api/v1/auth/refresh/` - Refresh access token
   - `GET /api/v1/services/services/` - Get services (requires valid JWT)

## Testing Methods

### Method 1: Using the Test Script (Automated)

```bash
# Make sure your app is running
python -m uvicorn src.skillbridge.app:app --reload

# In another terminal, run the test script
python test_jwt_auth.py

# Follow the prompts to enter your Student Role ID (from database)
```

**What it tests:**
- ✅ Login and token generation
- ✅ GET /services/ with valid token
- ✅ GET /services/ without token (should fail)
- ✅ GET /services/ with invalid token (should fail)
- ✅ Token refresh

### Method 2: Manual Testing with cURL

#### Step 1: Get Role IDs from Database
```bash
# Connect to MySQL and get role IDs
mysql -h localhost -u root -p skillbridge

# In MySQL:
SELECT id, slug, title FROM roles;

# You'll need:
# - Student role ID (e.g., a1b2c3d4-e5f6-7890-abcd-ef1234567890)
# - Tutor role ID (for tutor testing)
```

#### Step 2: Create Test Users (if needed)
```bash
# Register a student
curl -X POST "http://127.0.0.1:8000/api/v1/auth/register/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@test.com",
    "password": "Student@123",
    "full_name": "Test Student",
    "phone": "1234567890",
    "role_id": "YOUR_STUDENT_ROLE_ID"
  }'

# Register a tutor
curl -X POST "http://127.0.0.1:8000/api/v1/auth/register/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "tutor@test.com",
    "password": "Tutor@123",
    "full_name": "Test Tutor",
    "phone": "1234567890",
    "role_id": "YOUR_TUTOR_ROLE_ID"
  }'
```

#### Step 3: Login to Get Tokens
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@test.com",
    "password": "Student@123",
    "role_id": "YOUR_STUDENT_ROLE_ID"
  }'

# Response:
# {
#   "success": true,
#   "message": "User logged in successfully.",
#   "data": {
#     "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#     "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#     "token_type": "bearer",
#     "expires_in": 900,
#     "user_id": "...",
#     ...
#   }
# }
```

#### Step 4: Use Token to Access Protected Endpoint
```bash
# Get services with valid token
ACCESS_TOKEN="your_access_token_here"

curl -X GET "http://127.0.0.1:8000/api/v1/services/services/" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Should return 200 with services data
```

#### Step 5: Test Token Validation
```bash
# Without token (should fail with 401)
curl -X GET "http://127.0.0.1:8000/api/v1/services/services/"

# With invalid token (should fail with 401)
curl -X GET "http://127.0.0.1:8000/api/v1/services/services/" \
  -H "Authorization: Bearer invalid_token"

# With wrong authorization format (should fail with 401)
curl -X GET "http://127.0.0.1:8000/api/v1/services/services/" \
  -H "Authorization: invalid_format"
```

#### Step 6: Refresh Access Token
```bash
REFRESH_TOKEN="your_refresh_token_here"

curl -X POST "http://127.0.0.1:8000/api/v1/auth/refresh/" \
  -H "Content-Type: application/json" \
  -d "{
    \"refresh_token\": \"$REFRESH_TOKEN\"
  }"

# Response:
# {
#   "access_token": "new_jwt_token...",
#   "token_type": "bearer"
# }
```

### Method 3: Using Postman

1. **Create Environment Variables**
   - `base_url`: `http://127.0.0.1:8000/api`
   - `access_token`: (will be filled after login)
   - `refresh_token`: (will be filled after login)
   - `student_role_id`: (get from database)

2. **Login Request**
   - Method: POST
   - URL: `{{base_url}}/v1/auth/login/`
   - Body (JSON):
   ```json
   {
     "email": "student@test.com",
     "password": "Student@123",
     "role_id": "{{student_role_id}}"
   }
   ```
   - Tests (to save tokens):
   ```javascript
   if (pm.response.code === 200) {
     var jsonData = pm.response.json();
     pm.environment.set("access_token", jsonData.data.access_token);
     pm.environment.set("refresh_token", jsonData.data.refresh_token);
   }
   ```

3. **Get Services Request**
   - Method: GET
   - URL: `{{base_url}}/v1/services/services/`
   - Headers:
     - Authorization: `Bearer {{access_token}}`
   - Tests:
   ```javascript
   pm.test("Status is 200", function() {
     pm.response.to.have.status(200);
   });
   pm.test("Response has services", function() {
     var jsonData = pm.response.json();
     pm.expect(jsonData.data).to.be.an('array');
   });
   ```

4. **Refresh Token Request**
   - Method: POST
   - URL: `{{base_url}}/v1/auth/refresh/`
   - Body (JSON):
   ```json
   {
     "refresh_token": "{{refresh_token}}"
   }
   ```

## JWT Token Structure

The JWT tokens follow this structure:

**Access Token:**
```json
{
  "sub": "user_id",
  "exp": 1234567890,
  "type": "access",
  "jti": "unique_token_id",
  "role": "student",
  "tutor_id": "optional_tutor_id",
  "student_id": "optional_student_id"
}
```

**Refresh Token:**
```json
{
  "sub": "user_id",
  "exp": 9999999999,
  "type": "refresh",
  "jti": "unique_token_id"
}
```

## Configuration

Edit `src/skillbridge/api/repositories/auth/config.py`:

```python
# Token expiration settings
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # 15 minutes
REFRESH_TOKEN_EXPIRE_DAYS = 7    # 7 days

# JWT settings
JWT_ALGORITHM = "HS256"
JWT_SECRET_KEY = "your-secret-key"  # Should use environment variables in production

# Password hashing
BCRYPT_ROUNDS = 12
```

## Troubleshooting

### Error: "Authorization header missing"
- **Cause**: No Authorization header provided
- **Fix**: Add `Authorization: Bearer <token>` to request headers

### Error: "Invalid authorization header format"
- **Cause**: Authorization header doesn't follow "Bearer <token>" format
- **Fix**: Ensure the header is exactly: `Authorization: Bearer <valid_jwt_token>`

### Error: "Refresh token not found or revoked"
- **Cause**: Refresh token was revoked or doesn't exist in database
- **Fix**: Login again to get a new refresh token, or check if token was revoked

### Error: "Refresh token expired"
- **Cause**: Refresh token has expired (check REFRESH_TOKEN_EXPIRE_DAYS)
- **Fix**: Login again to get a new refresh token

### Token validation failing but token looks valid
- **Cause**: Token secret key mismatch or algorithm mismatch
- **Fix**: Check that `JWT_SECRET_KEY` and `JWT_ALGORITHM` match between token generation and verification

## Security Considerations

1. **Token Storage**: Store tokens securely in client (HttpOnly cookies preferred over localStorage)
2. **Token Rotation**: Refresh tokens regularly using the /refresh endpoint
3. **HTTPS**: Always use HTTPS in production to prevent token interception
4. **Secret Key**: Use strong, random secret keys from environment variables
5. **Token Expiration**: Use short-lived access tokens (15 min) with longer refresh tokens (7 days)
6. **Revocation**: Implement token revocation for logout

## Performance Notes

- Token verification is fast (< 1ms) using JWT decoding
- No database lookup required for token verification
- Refresh token validation requires one database query
- Consider caching role information if using frequently

## Next Steps

1. ✅ Test with the automated test script
2. ✅ Verify tokens are created correctly
3. ✅ Test token validation on protected endpoints
4. ✅ Test token refresh functionality
5. ✅ Test authorization (role-based access)
6. ✅ Implement token revocation for logout
7. ✅ Set up secure token storage in frontend

---

**Test Status**: Ready for full testing
**Last Updated**: 2026-08-17
