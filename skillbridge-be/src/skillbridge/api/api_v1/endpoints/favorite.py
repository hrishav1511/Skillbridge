from uuid import UUID

from fastapi import APIRouter, Request, status

from skillbridge.api.repositories.auth.token import validate_token
from skillbridge.api.repositories.favorite import FavoriteRepository
from skillbridge.api.schemas.favorite import FavoriteStatusInput, FavoriteStatusOutput
from skillbridge.exceptions import handle_exceptions

router = APIRouter()


@router.put(
    "/tutors/{tutor_id}/",
    response_model=FavoriteStatusOutput,
    status_code=status.HTTP_200_OK,
)
@handle_exceptions
@validate_token
async def favorite_tutor(
    request: Request,
    tutor_id: UUID,
    payload: FavoriteStatusInput,
    user_id: UUID = None,
):
    repository = FavoriteRepository()
    student_id = await repository.get_student_id(user_id)
    favorite = await repository.set_tutor_favorite(student_id, tutor_id, payload.favorite)
    return {"target_id": tutor_id, "favorite": favorite}


@router.put(
    "/services/{service_id}/",
    response_model=FavoriteStatusOutput,
    status_code=status.HTTP_200_OK,
)
@handle_exceptions
@validate_token
async def favorite_service(
    request: Request,
    service_id: UUID,
    payload: FavoriteStatusInput,
    user_id: UUID = None,
):
    repository = FavoriteRepository()
    student_id = await repository.get_student_id(user_id)
    favorite = await repository.set_service_favorite(student_id, service_id, payload.favorite)
    return {"target_id": service_id, "favorite": favorite}
