from typing import Optional, Tuple
from uuid import UUID

from skillbridge.api.filters.student import StudentSearchFilter
from skillbridge.api.repositories.base import BaseRepository
from skillbridge.api.schemas.student import StudentModel, StudentQueryCriteria
from skillbridge.api.validators.user import UserRegisterInputValidator
from skillbridge.database.db.database import get_session
from skillbridge.database.models.sqlalchemy.students import Student
from sqlalchemy.ext.asyncio import AsyncSession


class StudentRepository(BaseRepository):
    model = Student
    search_filter = StudentSearchFilter

    async def create_student(
        self,
        register_data: UserRegisterInputValidator,
        session: AsyncSession = None,
    ):
        student = await self.create(
            data=StudentModel(**register_data.model_dump()),
            session=session,
        )

        return student

    async def update_profile_picture(
        self,
        student_id: UUID,
        profile_picture_url: Optional[str],
        session: AsyncSession = None,
    ) -> Optional[Student]:
        student = (await self.get(_id=student_id, session=session))["data"]
        if student:
            student.profile_picture_url = profile_picture_url
            await self.update(_id=student.id, data=student, session=session)
        return student

    async def get_student_with_picture(
        self,
        student_id: UUID,
        session: AsyncSession = None,
    ) -> Tuple[Optional[Student], Optional[str]]:
        student = (await self.get(_id=student_id, session=session))["data"]
        if student:
            return student, student.profile_picture_url
        return None, None

    async def delete_profile_picture_url(
        self,
        student_id: UUID,
        session: AsyncSession = None,
    ) -> bool:
        student = (await self.get(_id=student_id, session=session))["data"]
        if student:
            student.profile_picture_url = None
            await self.update(_id=student.id, data=student, session=session)
            return True
        return False
