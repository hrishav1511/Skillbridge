from datetime import date, datetime, time, timezone
from uuid import UUID

from pydantic import BaseModel, field_validator

from skillbridge.utils.renderer import BaseResponse


class UpcomingService(BaseModel):
    booking_id: UUID | None = None
    service_id: UUID
    service_name: str
    date: date
    time: time
    scheduled_start_at: datetime
    price: int
    enrolled_students_count: int = 0
    student_id: UUID | None = None
    tutor_id: UUID | None = None

    @field_validator("scheduled_start_at", mode="before")
    @classmethod
    def stored_start_is_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @property
    def starts_at(self) -> datetime:
        return self.scheduled_start_at


class TutorDashboardCards(BaseModel):
    total_services: int
    upcoming_services: int
    total_earnings: float
    total_unique_students_taught: int


class TutorDashboardPerformance(BaseModel):
    average_rating: float
    total_reviews_last_30_days: int
    average_students_per_session: float


class TutorDashboardData(BaseModel):
    cards: TutorDashboardCards
    upcoming_services: list[UpcomingService]
    performance: TutorDashboardPerformance


class TutorDashboardResponse(BaseResponse):
    data: TutorDashboardData


class StudentDashboardData(BaseModel):
    total_upcoming_services: int
    total_available_tutors: int
    services_in_current_month: int
    tutors_in_current_month: int


class StudentDashboardResponse(BaseResponse):
    data: StudentDashboardData


class MonthlyServicesDone(BaseModel):
    month: str
    services_done: int


class AdminDashboardData(BaseModel):
    total_students: int
    total_tutors: int
    total_services: int
    pending_items: int
    monthly_services_done: list[MonthlyServicesDone]


class AdminDashboardResponse(BaseResponse):
    data: AdminDashboardData
