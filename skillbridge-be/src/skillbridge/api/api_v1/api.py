from fastapi import APIRouter

api_router = APIRouter()


from skillbridge.api.api_v1.endpoints import dashboard, role, service, ws, student
from skillbridge.api.api_v1.endpoints.auth import login, register, refresh, logout
from skillbridge.api.api_v1.endpoints import tutor
from skillbridge.api.api_v1.endpoints import user
from skillbridge.api.api_v1.endpoints import admin
from skillbridge.api.api_v1.endpoints import service_booking
from skillbridge.api.api_v1.endpoints import review, notification, favorite, report

api_router.include_router(
    role.router,
    prefix="/role",
    tags=["roles"],
)


api_router.include_router(
    register.router,
    prefix="/user/register",
    tags=["user authentication"],
)

api_router.include_router(
    tutor.router,
    prefix="/tutor",
    tags=["tutor"],
)

api_router.include_router(
    student.router,
    prefix="/student",
    tags=["student"],
)

api_router.include_router(user.router, prefix="/user", tags=["user"],)

api_router.include_router(
    login.router,
    prefix="/user/login",
    tags=["user authentication"],
)

api_router.include_router(
    service.router,
    prefix="/service",
    tags=["service"],
)

api_router.include_router(
    ws.router,
    prefix="/chat",
    tags=["chat"],
)

api_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["admin"],
)


api_router.include_router(
    service_booking.router,
    prefix="/service-booking",
    tags=["service-booking"],
)

api_router.include_router(
    review.router,
    prefix="/review",
    tags=["review"],
)

api_router.include_router(
    notification.router,
    prefix="/notifications",
    tags=["notifications"],
)

api_router.include_router(
    favorite.router,
    prefix="/favorites",
    tags=["favorites"],
)

api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["dashboard"],
)

api_router.include_router(
    report.router,
    prefix="/report",
    tags=["report"],
)

api_router.include_router(
    refresh.router,
    prefix="/refresh-token",
    tags=["user authentication"],
)

api_router.include_router(
    logout.router,
    prefix="/user",
    tags=["user authentication"],
)
