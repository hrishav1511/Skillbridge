from functools import wraps

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy.exc import DataError
from starlette.responses import JSONResponse

from skillbridge.utils.logger import (
    skillbridgeLoggerExtension,
)

skillbridge_exception = skillbridgeLoggerExtension()


class skillbridgeHttpException(Exception):
    def __init__(
        self,
        message: str,
        status: int = status.HTTP_400_BAD_REQUEST,
        detail: str | dict | list = "",
    ):
        self.message = message
        self.status = status
        self.detail = detail
        super().__init__(message)


def handle_exceptions(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            # Call the actual function (the endpoint)
            return await func(*args, **kwargs)

        except HTTPException as http_ex:
            # Handle FastAPI HTTPExceptions explicitly
            logger.error(f"HTTP error occurred: {http_ex.detail}")
            return JSONResponse(
                status_code=http_ex.status_code,
                content={"detail": http_ex.detail},
            )
        except DataError as e:
            # MySQL rejects over-long or otherwise unstorable values with a
            # DataError. Falling through to the generic handler below would
            # report it as a 500 with no detail, which is indistinguishable
            # from a server fault; it is a bad request, so say so.
            skillbridge_exception.log_exception(message=type(e).__name__)
            logger.error(f"Database rejected the submitted data: {e}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "success": False,
                    "message": "One of the submitted values is too long or "
                               "not in a storable format.",
                    "detail": "One of the submitted values is too long or "
                              "not in a storable format.",
                },
            )
        except Exception as e:
            # Handle all other exceptions
            skillbridge_exception.log_exception(message=type(e).__name__)
            status_code = getattr(e, "status_code", 500)
            message = getattr(e, "message", None) or str(e) or "Something went wrong."
            if status_code >= 500:
                message = "Something went wrong while processing the request."
            return JSONResponse(
                status_code=status_code,
                content={
                    "success": False,
                    "message": message,
                    "detail": message,
                },
            )

    return wrapper


class BaseExceptionMixin(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class SomethingWentWrong:
    success: bool = False
    message: str

    def __init__(self, message: str = None):
        if message:
            self.message = message
        else:
            self.message = "Something went wrong."


class InvalidTokenException(BaseExceptionMixin):
    pass


class TokenExpiredException(BaseExceptionMixin):
    pass


class DataValidationException(BaseExceptionMixin):
    pass


class ValidatorError(BaseExceptionMixin):
    pass


class NotFoundError(BaseExceptionMixin):
    pass


class InvalidSortError(BaseExceptionMixin):
    """An unsupported `sort` query parameter: a bad request, not a server fault."""

    pass


class InvalidCredentialsError(BaseExceptionMixin):
    pass


class InvalidEmailDomainError(BaseExceptionMixin):
    pass


class NotRegisteredError(BaseExceptionMixin):
    pass


class NotAuthenticatedError(BaseExceptionMixin):
    pass


class EmailNotSent(BaseExceptionMixin):
    pass


class LicenseUpdateError(BaseExceptionMixin):
    pass


class CannotRegisterError(BaseExceptionMixin):
    pass


class UnAuthorizedError(BaseExceptionMixin):
    pass


class InvalidOTPError(BaseExceptionMixin):
    pass


class OTPVerificationError(BaseExceptionMixin):
    pass


class OTPNotVerifiedError(BaseExceptionMixin):
    pass


class DuplicateUserError(BaseExceptionMixin):
    pass


class TripTypeAlreadyExistsError(BaseExceptionMixin):
    pass


class DataDoesntExistError(BaseExceptionMixin):
    pass


class NoSuchTripDataError(BaseExceptionMixin):
    pass


class ExistingUserBindingError(BaseExceptionMixin):
    pass


class AlreadyExistsError(BaseExceptionMixin):
    pass


class AllStepsNotCompletedError(BaseExceptionMixin):
    pass


class FileNotFound(BaseExceptionMixin):
    pass


class PhoneNotVerifiedError(BaseExceptionMixin):
    pass


class StepAlreadyExistError(BaseExceptionMixin):
    pass


class ContentBlockAlreadyExistError(BaseExceptionMixin):
    pass


class InvocationAlreadyExistError(BaseExceptionMixin):
    pass


class MediaAlreadyExistError(BaseExceptionMixin):
    pass


class ActionAlreadyExistError(BaseExceptionMixin):
    pass


class ContentAlreadyExistError(BaseExceptionMixin):
    pass


class LandmarkAlreadyExistError(BaseExceptionMixin):
    pass


class MarkedLocationAlreadyExistError(BaseExceptionMixin):
    pass


class AssociationAlreadyExistError(BaseExceptionMixin):
    pass


class TripAlreadyExistsError(BaseExceptionMixin):
    pass


class SearchRequestAlreadyExistsError(BaseExceptionMixin):
    pass


class CannotRevokeFinishedSearchError(BaseExceptionMixin):
    pass


class LanguageNotSupportedError(BaseExceptionMixin):
    pass


class LandmarkCategoryAlreadyExistsError(BaseExceptionMixin):
    pass


class LandmarkAlreadyExistsError(BaseExceptionMixin):
    pass


class UnpaidfidyaExistsError(BaseExceptionMixin):
    pass

class AuthenticationError(BaseExceptionMixin):
    pass
