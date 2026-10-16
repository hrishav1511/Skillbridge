from fastapi import APIRouter, HTTPException, Request, status

from skillbridge.api.repositories.auth.token import validate_token
from skillbridge.api.repositories.dashboard import DashboardRepository
from skillbridge.api.schemas.dashboard import (
    StudentDashboardResponse,
    TutorDashboardResponse,
)
from skillbridge.exceptions import handle_exceptions

router = APIRouter()


@router.get(
    "/tutor/",
    response_model=TutorDashboardResponse,
    status_code=status.HTTP_200_OK,
)
@handle_exceptions
@validate_token
async def tutor_dashboard(request: Request, user_id=None):
    data = await DashboardRepository().get_tutor_dashboard(user_id)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tutor dashboard is available only for tutor accounts.",
        )
    return {"success": True, "message": "Tutor dashboard fetched.", "data": data}


@router.get(
    "/student/",
    response_model=StudentDashboardResponse,
    status_code=status.HTTP_200_OK,
)
@handle_exceptions
@validate_token
async def student_dashboard(request: Request, user_id=None):
    data = await DashboardRepository().get_student_dashboard(user_id)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student dashboard is available only for student accounts.",
        )
    return {"success": True, "message": "Student dashboard fetched.", "data": data}
