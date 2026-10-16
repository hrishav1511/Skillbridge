from uuid import UUID

from pydantic import BaseModel, Field

from skillbridge.utils.renderer import BaseQueryCriteria, Status

# The columns behind these fields are TEXT, so these bounds exist to reject
# absurd payloads with a named validation error rather than to mirror a column
# width. They must stay in step with the maxlength on the Edit Profile form.
BIO_MAX_LENGTH = 2000
TEACHING_STYLE_MAX_LENGTH = 1000
ACADEMIC_PROGRAM_MAX_LENGTH = 255
PHONE_MAX_LENGTH = 50


class CreateTutorInputValidator(BaseModel):
    academic_program: str | None = Field(
        default=None, max_length=ACADEMIC_PROGRAM_MAX_LENGTH
    )
    bio: str | None = Field(default=None, max_length=BIO_MAX_LENGTH)
    phone: str | None = Field(default=None, max_length=PHONE_MAX_LENGTH)
    teaching_style: str | None = Field(
        default=None, max_length=TEACHING_STYLE_MAX_LENGTH
    )
    is_visible: bool | None = None
    approval_status: Status | None = None
    accepting_requests: bool | None = None
    tags: list[str] | None = None


class UpdateTutorInputValidator(BaseModel):
    full_name: str | None = None
    academic_program: str | None = Field(
        default=None, max_length=ACADEMIC_PROGRAM_MAX_LENGTH
    )
    bio: str | None = Field(default=None, max_length=BIO_MAX_LENGTH)
    phone: str | None = Field(default=None, max_length=PHONE_MAX_LENGTH)
    teaching_style: str | None = Field(
        default=None, max_length=TEACHING_STYLE_MAX_LENGTH
    )
    is_visible: bool | None = None
    approval_status: Status | None = None
    accepting_requests: bool | None = None
    tags: list[str] | None = None


class TutorSearchValidator(BaseQueryCriteria):
    tutor_id: UUID | None = None
    academic_program: str | None = None
    tag: str | None = None
    teaching_style: str | None = None
    approval_status: Status = Status.ALL
    public_only: bool = False
