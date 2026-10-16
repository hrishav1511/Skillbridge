from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from skillbridge.api.repositories.auth.token import validate_token
from skillbridge.api.repositories.notification import NotificationRepository
from skillbridge.api.repositories.report import (
    ReviewReportRepository,
    ServiceReportRepository,
    TutorReportRepository,
)
from skillbridge.api.repositories.user_role_association import UserRoleAssociationRepository
from skillbridge.api.schemas.report import (
    CreateServiceReportInput,
    CreateTutorReportInput,
    CreateReviewReportInput,
    ReportedReviewOutput,
    ReviewReportCreateResponse,
    ReviewReportListResponse,
    ServiceReportCreateResponse,
    ServiceReportListResponse,
    TutorReportCreateResponse,
    TutorReportListResponse,
)
from skillbridge.database.db.database import get_session
from skillbridge.exceptions import handle_exceptions

router = APIRouter()


async def _ensure_student(user_id: UUID):
    student_id = await UserRoleAssociationRepository().get_student_id_by_user_id(user_id)
    if student_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student access required.")
    return student_id


async def _ensure_admin(user_id: UUID):
    is_admin = await UserRoleAssociationRepository().is_user_admin(user_id=user_id)
    if not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")


@router.post(
    "/tutor/",
    status_code=status.HTTP_201_CREATED,
    response_model=TutorReportCreateResponse,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def report_tutor(
    request: Request,
    payload: CreateTutorReportInput,
    user_id: UUID = None,
):
    student_id = await _ensure_student(user_id)
    report = await TutorReportRepository().create_report(
        student_id=student_id,
        tutor_id=payload.tutor_id,
        reason=payload.reason,
    )
    return {
        "success": True,
        "message": "Tutor report created.",
        "data": {
            "id": report.id,
            "student_id": report.student_id,
            "tutor_id": report.tutor_id,
            "reason": report.reason,
        },
    }


@router.post(
    "/service/",
    status_code=status.HTTP_201_CREATED,
    response_model=ServiceReportCreateResponse,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def report_service(
    request: Request,
    payload: CreateServiceReportInput,
    user_id: UUID = None,
):
    student_id = await _ensure_student(user_id)
    report = await ServiceReportRepository().create_report(
        student_id=student_id,
        service_id=payload.service_id,
        reason=payload.reason,
    )
    return {
        "success": True,
        "message": "Service report created.",
        "data": {
            "id": report.id,
            "student_id": report.student_id,
            "service_id": report.service_id,
            "reason": report.reason,
        },
    }


def _associated_user_name(entity, association_attribute: str) -> str | None:
    """Read the display name behind a tutor or student row.

    Names live on the user account rather than on the tutor/student record, so
    the report list has to walk the role association to reach one.
    """
    if entity is None:
        return None
    associations = getattr(entity, association_attribute, None) or []
    for association in associations:
        user = getattr(association, "ura_user", None)
        if user is not None and user.full_name:
            return user.full_name
    return None


@router.get(
    "/tutor/",
    status_code=status.HTTP_200_OK,
    response_model=TutorReportListResponse,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def list_tutor_reports(
    request: Request,
    user_id: UUID = None,
):
    await _ensure_admin(user_id)
    reports = await TutorReportRepository().list_reports()
    return {
        "success": True,
        "message": "Tutor reports fetched.",
        "data": [
            {
                "id": item.id,
                "student_id": item.student_id,
                "tutor_id": item.tutor_id,
                "reason": item.reason,
                "reporter_name": _associated_user_name(
                    getattr(item, "reported_tutor_student", None), "student_ura"
                ),
                "tutor_name": _associated_user_name(
                    getattr(item, "reported_tutor_tutor", None), "tutor_ura"
                ),
                "tutor_profile_picture_url": getattr(
                    getattr(item, "reported_tutor_tutor", None),
                    "profile_picture_url",
                    None,
                ),
                "reported_at": item.reported_at,
            }
            for item in reports
        ],
    }


@router.get(
    "/service/",
    status_code=status.HTTP_200_OK,
    response_model=ServiceReportListResponse,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def list_service_reports(
    request: Request,
    user_id: UUID = None,
):
    await _ensure_admin(user_id)
    reports = await ServiceReportRepository().list_reports()
    return {
        "success": True,
        "message": "Service reports fetched.",
        "data": [
            {
                "id": item.id,
                "student_id": item.student_id,
                "service_id": item.service_id,
                "reason": item.reason,
                "reporter_name": _associated_user_name(
                    getattr(item, "reported_service_student", None), "student_ura"
                ),
                "service_name": getattr(
                    getattr(item, "reported_service_service", None),
                    "service_name",
                    None,
                ),
                "reported_at": item.reported_at,
            }
            for item in reports
        ],
    }


def _reported_review_output(report) -> ReportedReviewOutput:
    review = report.reported_tutor_review or report.reported_service_review
    review_type = "tutor" if report.tutor_review_id else "service"
    review_id = report.tutor_review_id or report.service_review_id
    return ReportedReviewOutput(
        id=report.id,
        reporter_user_id=report.reporter_user_id,
        review_type=review_type,
        review_id=review_id,
        reason=report.reason,
        review_comment=review.comment if review else None,
        review_rating=review.rating if review else 0,
        reporter_name=(
            report.reporter_user.full_name
            if getattr(report, "reporter_user", None)
            else None
        ),
        reported_at=report.reported_at,
    )


@router.post(
    "/review/{review_type}/{review_id}/",
    status_code=status.HTTP_201_CREATED,
    response_model=ReviewReportCreateResponse,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def report_review(
    request: Request,
    review_type: str,
    review_id: UUID,
    payload: CreateReviewReportInput,
    user_id: UUID = None,
):
    report, review, normalized_type = await ReviewReportRepository().create_report(
        reporter_user_id=user_id,
        review_type=review_type,
        review_id=review_id,
        reason=payload.reason,
    )
    return {
        "success": True,
        "message": "Review report created.",
        "data": ReportedReviewOutput(
            id=report.id,
            reporter_user_id=report.reporter_user_id,
            review_type=normalized_type,
            review_id=review.id,
            reason=report.reason,
            review_comment=review.comment,
            review_rating=review.rating,
            reported_at=report.reported_at,
        ),
    }


@router.get(
    "/review/",
    status_code=status.HTTP_200_OK,
    response_model=ReviewReportListResponse,
    response_model_by_alias=False,
)
@handle_exceptions
@validate_token
async def list_review_reports(request: Request, user_id: UUID = None):
    await _ensure_admin(user_id)
    reports = await ReviewReportRepository().list_reports()
    return {
        "success": True,
        "message": "Review reports fetched.",
        "data": [_reported_review_output(report) for report in reports],
    }


@router.delete("/review/{report_id}/", status_code=status.HTTP_200_OK)
@handle_exceptions
@validate_token
async def discard_review_report(
    request: Request, report_id: UUID, user_id: UUID = None
):
    await _ensure_admin(user_id)
    await ReviewReportRepository().discard_report(report_id)
    return {"success": True, "message": "Review report discarded."}


@router.delete("/review/{report_id}/review/", status_code=status.HTTP_200_OK)
@handle_exceptions
@validate_token
async def remove_reported_review(
    request: Request, report_id: UUID, user_id: UUID = None
):
    await _ensure_admin(user_id)
    review_id = await ReviewReportRepository().remove_reported_review(report_id)
    return {
        "success": True,
        "message": "Reported review removed.",
        "data": {"review_id": review_id},
    }


@router.patch(
    "/tutor/{report_id}/disable/",
    status_code=status.HTTP_200_OK,
)
@handle_exceptions
@validate_token
async def disable_reported_tutor(
    request: Request,
    report_id: UUID,
    user_id: UUID = None,
):
    await _ensure_admin(user_id)
    async with get_session() as session:
        report = await TutorReportRepository().get(_id=report_id, session=session)
        tutor = await TutorReportRepository().disable_tutor(
            report["data"].tutor_id,
            session=session,
        )
        await TutorReportRepository().discard_report(report_id, session=session)
        tutor_user_id = await UserRoleAssociationRepository().get_user_id_by_tutor_id(
            tutor.id, session=session
        )
        if tutor_user_id is not None:
            await NotificationRepository().create_for_user(
                user_id=tutor_user_id,
                notification_type="TUTOR_DISABLED_AFTER_REPORT",
                title="Tutor profile disabled",
                message="Your tutor profile was disabled after a moderation review.",
                data={"tutor_id": str(tutor.id)},
                session=session,
            )
        await session.commit()
    return {
        "success": True,
        "message": "Tutor disabled and report discarded.",
        "data": {"tutor_id": tutor.id, "status": tutor.status},
    }


@router.patch(
    "/service/{report_id}/disable/",
    status_code=status.HTTP_200_OK,
)
@handle_exceptions
@validate_token
async def disable_reported_service(
    request: Request,
    report_id: UUID,
    user_id: UUID = None,
):
    await _ensure_admin(user_id)
    async with get_session() as session:
        report = await ServiceReportRepository().get(_id=report_id, session=session)
        service = await ServiceReportRepository().disable_service(
            report["data"].service_id,
            session=session,
        )
        await ServiceReportRepository().discard_report(report_id, session=session)
        tutor_user_id = await UserRoleAssociationRepository().get_user_id_by_tutor_id(
            service.tutor_id, session=session
        )
        if tutor_user_id is not None:
            await NotificationRepository().create_for_user(
                user_id=tutor_user_id,
                notification_type="SERVICE_DISABLED_AFTER_REPORT",
                title="Service disabled",
                message="Your service was disabled after a moderation review.",
                data={"service_id": str(service.id)},
                session=session,
            )
        await session.commit()
    return {
        "success": True,
        "message": "Service disabled and report discarded.",
        "data": {"service_id": service.id, "status": service.status},
    }


@router.delete(
    "/tutor/{report_id}/",
    status_code=status.HTTP_200_OK,
)
@handle_exceptions
@validate_token
async def discard_tutor_report(
    request: Request,
    report_id: UUID,
    user_id: UUID = None,
):
    await _ensure_admin(user_id)
    await TutorReportRepository().discard_report(report_id)
    return {"success": True, "message": "Tutor report discarded."}


@router.delete(
    "/service/{report_id}/",
    status_code=status.HTTP_200_OK,
)
@handle_exceptions
@validate_token
async def discard_service_report(
    request: Request,
    report_id: UUID,
    user_id: UUID = None,
):
    await _ensure_admin(user_id)
    await ServiceReportRepository().discard_report(report_id)
    return {"success": True, "message": "Service report discarded."}
