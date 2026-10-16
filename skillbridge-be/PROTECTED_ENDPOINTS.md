# Protected Endpoints Quick Reference

## Overview
All endpoints listed below require valid JWT authentication via the Authorization header.

**Format:** `Authorization: Bearer <access_token>`

---

## Authentication Endpoints (Public)

| Method | Endpoint | Protected | Purpose |
|--------|----------|-----------|---------|
| POST | `/auth/login/` | ❌ No | User login - Get tokens |
| POST | `/auth/refresh/` | ❌ No | Refresh access token |
| POST | `/auth/logout/` | ✅ Yes | Logout - Revoke refresh token |

---

## Service Endpoints

| Method | Endpoint | Protected | Role Required | Decorator |
|--------|----------|-----------|---------------|-----------|
| POST | `/services/create/` | ✅ Yes | Tutor | @validate_token |
| GET | `/services/services/` | ✅ Yes | Any | @validate_token |
| GET | `/services/{service_id}` | ❌ No | - | - |
| PUT | `/services/{service_id}/` | ✅ Yes | Tutor | @validate_token |
| DELETE | `/services/{service_id}/` | ✅ Yes | Tutor | @validate_token |
| POST | `/services/create/booking/` | ✅ Yes | Student | @validate_token |

---

## Admin Endpoints

| Method | Endpoint | Protected | Role Required | Decorator |
|--------|----------|-----------|---------------|-----------|
| GET | `/admin/service_revisions/pending/` | ✅ Yes | Admin | @validate_token |
| POST | `/admin/service_revisions/{id}/approve/` | ✅ Yes | Admin | @validate_token |
| POST | `/admin/service_revisions/{id}/reject/` | ✅ Yes | Admin | @validate_token |
| GET | `/admin/tutor_revisions/pending/` | ✅ Yes | Admin | @validate_token |
| POST | `/admin/tutor_revisions/{id}/approve/` | ✅ Yes | Admin | @validate_token |
| POST | `/admin/tutor_revisions/{id}/reject/` | ✅ Yes | Admin | @validate_token |

---

## Review Endpoints

| Method | Endpoint | Protected | Decorator |
|--------|----------|-----------|-----------|
| POST | `/reviews/tutor` | ✅ Yes | @validate_token |
| POST | `/reviews/service` | ✅ Yes | @validate_token |
| GET | `/reviews/tutor` | ❌ No | - |
| GET | `/reviews/service` | ❌ No | - |

---

## Tutor Endpoints

| Method | Endpoint | Protected | Role Required | Decorator |
|--------|----------|-----------|---------------|-----------|
| POST | `/tutors/create/` | ✅ Yes | Any | @validate_token |
| GET | `/tutors/tutors/` | ❌ No | - | - |
| GET | `/tutors/{tutor_id}` | ❌ No | - | - |
| PUT | `/tutors/{tutor_id}/` | ✅ Yes | Tutor | @validate_token |
| POST | `/tutors/{tutor_id}/upload-profile-picture` | ✅ Yes | Tutor | @validate_token |
| POST | `/tutors/{tutor_id}/upload-cover-picture` | ✅ Yes | Tutor | @validate_token |
| DELETE | `/tutors/{tutor_id}/profile-picture` | ✅ Yes | Tutor | @validate_token |
| DELETE | `/tutors/{tutor_id}/cover-picture` | ✅ Yes | Tutor | @validate_token |
| GET | `/tutors/my-services/` | ✅ Yes | Tutor | @validate_token |
| GET | `/tutors/my-service_revisions/` | ✅ Yes | Tutor | @validate_token |

---

## Service Booking Endpoints

| Method | Endpoint | Protected | Decorator |
|--------|----------|-----------|-----------|
| POST | `/service_bookings/create/` | ✅ Yes | @validate_token |
| GET | `/service_bookings/service-bookings/` | ✅ Yes | @validate_token |

---

## User Endpoints

| Method | Endpoint | Protected | Decorator |
|--------|----------|-----------|-----------|
| GET | `/users/` | ❌ No | - |

---

## WebSocket Endpoints

| Protocol | Endpoint | Protected | Auth Method |
|----------|----------|-----------|-------------|
| WebSocket | `/chat/ws/{user_id}` | ✅ Yes | Query param token |

---

## Testing Protected Endpoints

### 1. Get Access Token
```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePassword@123",
    "role_id": "your-role-uuid"
  }'

# Response:
# {
#   "data": {
#     "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#     "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#     ...
#   }
# }
```

### 2. Use Token for Protected Endpoint
```bash
ACCESS_TOKEN="your-access-token-here"

curl -X GET http://127.0.0.1:8000/api/v1/services/services/ \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Response: 200 OK - Services list
```

### 3. Refresh Expired Token
```bash
REFRESH_TOKEN="your-refresh-token-here"

curl -X POST http://127.0.0.1:8000/api/v1/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "'$REFRESH_TOKEN'"}'

# Response:
# {
#   "access_token": "new-token-here",
#   "token_type": "bearer"
# }
```

### 4. Test Authorization Enforcement
```bash
# Missing token (should fail)
curl -X GET http://127.0.0.1:8000/api/v1/services/services/
# Response: 401 - "Authorization header missing"

# Invalid format (should fail)
curl -X GET http://127.0.0.1:8000/api/v1/services/services/ \
  -H "Authorization: InvalidFormat token"
# Response: 401 - "Invalid authorization header format"

# Invalid token (should fail)
curl -X GET http://127.0.0.1:8000/api/v1/services/services/ \
  -H "Authorization: Bearer invalid.token.here"
# Response: 401 - "Invalid token"

# Expired token (should fail)
curl -X GET http://127.0.0.1:8000/api/v1/services/services/ \
  -H "Authorization: Bearer $EXPIRED_ACCESS_TOKEN"
# Response: 401 - "Token expired"

# Valid token (should succeed)
curl -X GET http://127.0.0.1:8000/api/v1/services/services/ \
  -H "Authorization: Bearer $VALID_ACCESS_TOKEN"
# Response: 200 - Services data
```

---

## Token Expiration Times

| Token Type | Expiration | Use Case |
|------------|-----------|----------|
| Access Token | 15 minutes | Use for API requests |
| Refresh Token | 7 days | Use to get new access token |

---

## Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `401 Authorization header missing` | No auth header sent | Add `Authorization: Bearer <token>` header |
| `401 Invalid authorization header format` | Wrong header format | Use format: `Authorization: Bearer <token>` |
| `401 Invalid token` | Token signature invalid | Get new token from login |
| `401 Token expired` | Access token expired | Use refresh token to get new access token |
| `401 Refresh token not found or revoked` | Refresh token was revoked | Login again to get new tokens |
| `403 Forbidden` | Insufficient permissions | Ensure user has required role |

---

## Decorator Implementation Details

### @validate_token Decorator

```python
from skillbridge.api.repositories.auth.token import validate_token

@router.get("/protected/")
@validate_token
async def protected_endpoint(user_id: str = None):
    """
    user_id is automatically extracted from JWT token
    by the @validate_token decorator
    """
    print(f"User ID: {user_id}")
    return {"message": "Success"}
```

**How it works:**
1. Intercepts the request
2. Extracts JWT from Authorization header
3. Verifies token signature and expiration
4. Extracts `user_id` from token's `sub` claim
5. Injects `user_id` as parameter to endpoint function
6. Returns 401 if token is missing or invalid

---

## Best Practices

✅ **DO:**
- Store refresh token securely (HttpOnly cookie recommended)
- Refresh access token before expiration (every 10 minutes)
- Use HTTPS in production
- Include token in Authorization header for all requests
- Handle 401 responses by redirecting to login

❌ **DON'T:**
- Store tokens in localStorage (XSS vulnerability)
- Send token in URL query parameters
- Log or expose tokens in error messages
- Use same secret key across environments
- Send passwords via unencrypted connections

---

## Implementation Files

- **Token Creation/Verification:** `src/skillbridge/api/repositories/auth/token.py`
- **Token Validation Logic:** `src/skillbridge/api/repositories/auth/token_verifier.py`
- **Configuration:** `src/skillbridge/api/repositories/auth/config.py`
- **Protected Endpoints:** See specific endpoint files above
- **Login Handler:** `src/skillbridge/api/repositories/auth/login.py`

---

**Last Updated:** 2026-08-17
