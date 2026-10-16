import copy

from loguru import logger

from skillbridge.api.repositories.auth.login import LoginRepository
from skillbridge.api.repositories.auth.token import TokenRepository
from skillbridge.api.repositories.base import BaseRepository
from skillbridge.api.repositories.role import RoleRepository
from skillbridge.api.repositories.student import StudentRepository
from skillbridge.api.repositories.tutor import TutorRepository
from skillbridge.api.repositories.user import UserRepository
from skillbridge.api.repositories.user_role_association import (
    UserRoleAssociationRepository,
)
from skillbridge.api.schemas.user import (
    UserModel,
    UserProfileModel,
    UserRegisterResponse,
)
from skillbridge.api.schemas.user_role import UserRoleAssociationModel
from skillbridge.api.validators.login import LoginInputValidator
from skillbridge.api.validators.user import UserRegisterInputValidator
from skillbridge.config import settings
from skillbridge.database.db.database import get_session
from skillbridge.database.models.sqlalchemy.user_role_associations import (
    UserRoleAssociation,
)
from skillbridge.database.models.sqlalchemy.users import User
from skillbridge.exceptions import CannotRegisterError
from skillbridge.utils.renderer import Status


class RegisterRepository(BaseRepository):
    model = User

    async def register(
        self, register_data: UserRegisterInputValidator
    ) -> UserRegisterResponse:
        async with get_session() as session:
            role = (
                await RoleRepository().get(
                    _id=register_data.role_id,
                    session=session,
                )
            )["data"]
            role_slug = str(role.slug).lower()
            if role_slug not in {"student", "tutor"}:
                raise CannotRegisterError(
                    message="Public registration is limited to student and tutor accounts.",
                    status_code=403,
                )

            existing_user = await UserRepository().get_user_from_email(
                email=register_data.email,
                session=session,
            )
            if existing_user:
                raise CannotRegisterError(
                    message="An account with this email already exists.",
                    status_code=409,
                )

            user_data = register_data.model_dump()
            user_data["email"] = str(register_data.email).lower()
            user_data["password"] = TokenRepository().hash_password(user_data["password"])
            user_model = UserModel(**user_data)
            user = (
                await self.create(
                    data=user_model,
                    session=session,
                )
            )["data"]

            student_id = None
            if role_slug == "tutor":
                user.has_registered = False
                user.is_verified = False
                register_data.approval_status = Status.PENDING
                await TutorRepository().create_tutor_registration_request(
                    register_data=register_data,
                    user_id=user.id,
                    session=session,
                )
            elif role_slug == "student":
                student = await StudentRepository().create_student(
                    register_data=register_data,
                    session=session,
                )
                student_id = student["data"].id
            user_role = UserRoleAssociationModel(
                user_id=user.id,
                role_id=register_data.role_id,
                tutor_id=None,
                student_id=student_id,
            )
            new_user_role = (
                await UserRoleAssociationRepository().create(
                    data=user_role,
                    model=UserRoleAssociation,
                    session=session,
                )
            )["data"]

            await session.commit()

            # Build a minimal serializable response while session is open
            response_payload = {
                "id": user.id,
                "full_name": user.full_name,
                "email": user.email,
                "phone": getattr(user, "phone", None),
            }

        # Return a small wrapper that exposes to_dict() like the endpoint expects
        return _Returnable(response_payload)

    

    async def validate_register_data(self, data: UserRegisterInputValidator):
        async with get_session() as session:
            await UserRepository().check_duplicate_user(
                email=data.email,
                # phone=data.phone,
                session=session,
            )

            role = await RoleRepository().get(
                _id=data.role_id,
                session=session,
            )

            return True


class _Returnable:
    def __init__(self, data: dict):
        self._data = data

    def __getattr__(self, name: str):
        try:
            return self._data[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __getitem__(self, key):
        return self._data[key]

    def to_dict(self):
        return self._data
