from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from skillbridge.api.repositories.auth.token import get_optional_user_id, validate_token
from skillbridge.api.repositories.review import ReviewRepository, format_average_rating
from skillbridge.api.repositories.user_role_association import UserRoleAssociationRepository
from skillbridge.api.schemas.review import (
    CreateServiceReviewInput,
    CreateTutorReviewInput,
    ServiceReviewOutput,
    ServiceReviewQueryCriteria,
    TutorReviewOutput,
    TutorReviewQueryCriteria,
)
from skillbridge.api.schemas.user import UserOutput
from skillbridge.api.validators.base import BaseValidator

router = APIRouter()


@router.post("/tutor/", status_code=status.HTTP_201_CREATED)
@validate_token
async def create_tutor_review(
    request: Request,
    payload: CreateTutorReviewInput,
    user_id: str = None,
):
    student_id = await UserRoleAssociationRepository().get_student_id_by_user_id(user_id)
    if student_id is None:
        raise HTTPException(status_code=403, detail="Student access required.")
    await ReviewRepository().ensure_tutor_review_allowed(
        tutor_id=payload.tutor_id, student_id=student_id
    )
    has_error, valid_input = BaseValidator.validate(
        validator=CreateTutorReviewInput,
        input_data=payload,
    )
    if has_error:
        return has_error

    review_payload = valid_input.model_dump()
    review_payload["student_id"] = student_id
    data = await ReviewRepository().create_tutor_review(review_payload)
    return {
        "success": data["success"],
        "message": data["message"],
        "data": TutorReviewOutput(**data["data"].to_dict()),
    }


@router.post("/service/", status_code=status.HTTP_201_CREATED)
@validate_token
async def create_service_review(
    request: Request,
    payload: CreateServiceReviewInput,
    user_id: UUID = None,
):
    student_id = await UserRoleAssociationRepository().get_student_id_by_user_id(user_id)
    if student_id is None:
        raise HTTPException(status_code=403, detail="Student access required.")
    await ReviewRepository().ensure_service_review_allowed(
        service_id=payload.service_id,
        student_id=student_id,
    )

    has_error, valid_input = BaseValidator.validate(
        validator=CreateServiceReviewInput,
        input_data=payload,
    )
    if has_error:
        return has_error


    review_payload = valid_input.model_dump()
    review_payload["student_id"] = student_id
    data = await ReviewRepository().create_service_review(review_payload)
    return {
        "success": data["success"],
        "message": data["message"],
        "data": ServiceReviewOutput(**data["data"].to_dict()),
    }


@router.get("/tutor/")
async def get_tutor_reviews(
    request: Request,
    query: TutorReviewQueryCriteria = Depends(TutorReviewQueryCriteria),
    user_id: UUID = None,
):
    user_id = await get_optional_user_id(request)
    data = await ReviewRepository().filter_tutor_reviews(query)
    out = []
    for review in data["data"]:
        payload = review.to_dict()
        student_user = None
        student = getattr(review, "tutor_review_student", None)
        if student and getattr(student, "student_ura", None):
            # student_ura is a list of UserRoleAssociation; find the linked User
            for ura in student.student_ura:
                if getattr(ura, "ura_user", None):
                    u = ura.ura_user
                    student_user = UserOutput(
                        full_name=u.full_name,
                        email=u.email if user_id is not None else None,
                        phone=u.phone if user_id is not None else None,
                        status=u.status if user_id is not None else None,
                        has_registered=u.has_registered if user_id is not None else None,
                        is_verified=u.is_verified,
                        id=u.id if user_id is not None else None,
                    ).model_dump()
                    break
        payload["student"] = student_user
        out.append(TutorReviewOutput(**payload))

    return {"success": data["success"], "message": data["message"], "data": out}


@router.get("/service/")
async def get_service_reviews(
    request: Request,
    query: ServiceReviewQueryCriteria = Depends(ServiceReviewQueryCriteria),
    user_id: UUID = None,
):
    user_id = await get_optional_user_id(request)
    data = await ReviewRepository().filter_service_reviews(query)
    out = []
    for review in data["data"]:
        payload = review.to_dict()
        student_user = None
        student = getattr(review, "service_review_student", None)
        if student and getattr(student, "student_ura", None):
            for ura in student.student_ura:
                if getattr(ura, "ura_user", None):
                    u = ura.ura_user
                    student_user = UserOutput(
                        full_name=u.full_name,
                        email=u.email if user_id is not None else None,
                        phone=u.phone if user_id is not None else None,
                        status=u.status if user_id is not None else None,
                        has_registered=u.has_registered if user_id is not None else None,
                        is_verified=u.is_verified,
                        id=u.id if user_id is not None else None,
                    ).model_dump()
                    break
        payload["student"] = student_user
        out.append(ServiceReviewOutput(**payload))

    return {"success": data["success"], "message": data["message"], "data": out}
