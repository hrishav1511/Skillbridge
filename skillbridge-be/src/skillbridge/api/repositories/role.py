from skillbridge.api.filters.role import RoleSearchFilter
from skillbridge.api.repositories.base import BaseRepository
from skillbridge.api.validators.role import CreateRoleInputValidator
from skillbridge.database.db.database import get_session
from skillbridge.database.models.sqlalchemy.roles import Role


class RoleRepository(BaseRepository):
    model = Role
    search_filter = RoleSearchFilter

    async def create_role(self, role: CreateRoleInputValidator):
        async with get_session() as session:
            new_role = await self.create(
                data=role,
                session=session,
            )
            await session.commit()
            return new_role
