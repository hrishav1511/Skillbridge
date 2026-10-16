"""
Tests for Service Approval & Revision Workflow - Endpoints
NOTE: These endpoint tests require a running application and database.
For development, use curl or Postman to test the endpoints.
"""

# Example API Workflow Tests:
#
# 1. TUTOR CREATES SERVICE (creates PENDING CREATE revision):
#    POST /api/v1/services/create/
#    Headers: Authorization: Bearer <tutor_token>
#    Body: {
#        "tutor_id": "<tutor_id>",
#        "service_name": "Python Basics",
#        "description": "Learn Python fundamentals",
#        "date": "2026-07-15",
#        "time": "14:30:00",
#        "price": 50,
#        "level": "BEGINNER",
#        "joining_link": "https://zoom.us/..."
#    }
#    Expected: 201, revision with approval_status="PENDING", revision_type="CREATE"
#
# 2. ADMIN LISTS PENDING REVISIONS:
#    GET /api/v1/services/admin/revisions/pending/
#    Headers: Authorization: Bearer <admin_token>
#    Expected: 200, list of all pending revisions
#
# 3. ADMIN APPROVES CREATE REVISION (service becomes visible to students):
#    POST /api/v1/services/admin/revisions/<revision_id>/approve/
#    Headers: Authorization: Bearer <admin_token>
#    Expected: 200, revision with approval_status="ACCEPTED", service now published
#
# 4. STUDENT CAN SEE APPROVED SERVICE:
#    GET /api/v1/services/services/
#    Headers: Authorization: Bearer <student_token>
#    Expected: 200, service is in the list
#
# 5. TUTOR UPDATES SERVICE (creates PENDING UPDATE revision):
#    PUT /api/v1/services/<service_id>/
#    Headers: Authorization: Bearer <tutor_token>
#    Body: { "price": 75 }
#    Expected: 201, new revision with revision_type="UPDATE", approval_status="PENDING"
#    Note: Previous ACCEPTED service remains unchanged for students
#
# 6. ADMIN REJECTS UPDATE REVISION (published service stays unchanged):
#    POST /api/v1/services/admin/revisions/<revision_id>/reject/
#    Headers: Authorization: Bearer <admin_token>
#    Body: { "rejection_reason": "Price too high" }
#    Expected: 200, revision with approval_status="REJECTED"
#
# 7. TUTOR VIEWS THEIR APPROVED SERVICES:
#    GET /api/v1/services/tutor/my-services/
#    Headers: Authorization: Bearer <tutor_token>
#    Expected: 200, list of published services
#
# 8. TUTOR VIEWS THEIR REVISIONS (all statuses):
#    GET /api/v1/services/tutor/my-revisions/
#    Headers: Authorization: Bearer <tutor_token>
#    Expected: 200, list of all revisions (PENDING, ACCEPTED, REJECTED)
#
# 9. TUTOR DELETES SERVICE (creates PENDING DELETE revision):
#    DELETE /api/v1/services/<service_id>/
#    Headers: Authorization: Bearer <tutor_token>
#    Expected: 200, revision with revision_type="DELETE", approval_status="PENDING"
#
# 10. ADMIN APPROVES DELETE REVISION (service is removed):
#     POST /api/v1/services/admin/revisions/<revision_id>/approve/
#     Headers: Authorization: Bearer <admin_token>
#     Expected: 200, revision with approval_status="ACCEPTED", service deleted


# Run integration tests with the actual application:
# 1. Start the application: python -m uvicorn src.skillbridge.app:app --reload
# 2. Run manual tests or use pytest with TestClient after proper setup

