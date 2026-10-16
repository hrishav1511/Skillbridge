from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status

from skillbridge.api.repositories.auth.token import validate_token
from skillbridge.api.repositories.student import StudentRepository
from skillbridge.api.repositories.user_role_association import UserRoleAssociationRepository
from skillbridge.api.schemas.student import ProfilePictureUploadResponse
from skillbridge.api.services.media_service import MediaService
from skillbridge.exceptions import handle_exceptions

router = APIRouter()


async def get_media_service():
    student_repository = StudentRepository()
    return MediaService(student_repository=student_repository)


async def _require_student_owner(user_id: UUID, student_id: UUID) -> None:
    owned_student_id = await UserRoleAssociationRepository().get_student_id_by_user_id(user_id)
    if owned_student_id != student_id:
        raise HTTPException(status_code=403, detail="You can modify only your own student profile.")


@router.post(
    "/{student_id}/upload-profile-picture/",
    response_model=ProfilePictureUploadResponse,
    status_code=status.HTTP_200_OK,
)
@handle_exceptions
@validate_token
async def upload_student_profile_picture(
    request: Request,
    student_id: UUID,
    file: UploadFile = File(...),
    media_service: MediaService = Depends(get_media_service),
    user_id: UUID = None,
):
    """Upload profile picture for a student."""
    await _require_student_owner(user_id, student_id)
    profile_url = await media_service.upload_student_profile_picture(student_id, file)
    return ProfilePictureUploadResponse(
        profile_picture_url=profile_url,
        message="Profile picture uploaded successfully",
    )


@router.delete(
    "/{student_id}/profile-picture/",
    status_code=status.HTTP_200_OK,
)
@handle_exceptions
@validate_token
async def delete_student_profile_picture(
    request: Request,
    student_id: UUID,
    user_id: UUID = None,
    media_service: MediaService = Depends(get_media_service),
):
    """Delete a student's profile picture."""
    await _require_student_owner(user_id, student_id)
    await media_service.delete_student_profile_picture(student_id)
    return {"message": "Profile picture deleted successfully"}
