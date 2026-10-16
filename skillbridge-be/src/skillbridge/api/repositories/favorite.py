from uuid import UUID

from sqlalchemy import select

from skillbridge.api.repositories.user_role_association import UserRoleAssociationRepository
from skillbridge.database.db.database import get_session
from skillbridge.database.models.sqlalchemy.student_favorite_services import StudentFavoriteService
from skillbridge.database.models.sqlalchemy.student_favorite_tutors import StudentFavoriteTutor
from skillbridge.database.models.sqlalchemy.services import Service
from skillbridge.database.models.sqlalchemy.tutors import Tutor
from skillbridge.exceptions import NotFoundError, UnAuthorizedError


class FavoriteRepository:
    async def get_student_id(self, user_id: UUID) -> UUID:
        student_id = await UserRoleAssociationRepository().get_student_id_by_user_id(user_id)
        if student_id is None:
            raise UnAuthorizedError(
                message="Only students can manage favorites.",
                status_code=403,
            )
        return student_id

    async def set_tutor_favorite(self, student_id: UUID, tutor_id: UUID, favorite: bool):
        async with get_session() as session:
            if await session.get(Tutor, tutor_id) is None:
                raise NotFoundError(message="Tutor not found.", status_code=404)
            existing = (
                await session.execute(
                    select(StudentFavoriteTutor).where(
                        StudentFavoriteTutor.student_id == student_id,
                        StudentFavoriteTutor.tutor_id == tutor_id,
                    )
                )
            ).scalar_one_or_none()
            if favorite and existing is None:
                session.add(StudentFavoriteTutor(student_id=student_id, tutor_id=tutor_id))
            elif not favorite and existing is not None:
                await session.delete(existing)
            await session.commit()
            return favorite

    async def set_service_favorite(self, student_id: UUID, service_id: UUID, favorite: bool):
        async with get_session() as session:
            if await session.get(Service, service_id) is None:
                raise NotFoundError(message="Service not found.", status_code=404)
            existing = (
                await session.execute(
                    select(StudentFavoriteService).where(
                        StudentFavoriteService.student_id == student_id,
                        StudentFavoriteService.service_id == service_id,
                    )
                )
            ).scalar_one_or_none()
            if favorite and existing is None:
                session.add(StudentFavoriteService(student_id=student_id, service_id=service_id))
            elif not favorite and existing is not None:
                await session.delete(existing)
            await session.commit()
            return favorite

    async def get_tutor_ids(self, student_id: UUID) -> set[UUID]:
        async with get_session() as session:
            return set(
                (await session.execute(
                    select(StudentFavoriteTutor.tutor_id).where(
                        StudentFavoriteTutor.student_id == student_id
                    )
                )).scalars().all()
            )

    async def get_service_ids(self, student_id: UUID) -> set[UUID]:
        async with get_session() as session:
            return set(
                (await session.execute(
                    select(StudentFavoriteService.service_id).where(
                        StudentFavoriteService.student_id == student_id
                    )
                )).scalars().all()
            )