from uuid import UUID

from pydantic import BaseModel


class FavoriteStatusInput(BaseModel):
    favorite: bool = True


class FavoriteStatusOutput(BaseModel):
    target_id: UUID
    favorite: bool