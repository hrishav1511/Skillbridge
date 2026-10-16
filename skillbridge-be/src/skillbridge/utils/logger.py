import traceback

from fastapi import Request, Response, status
from loguru import logger

from skillbridge.logger import configure_logging


def get_endpoint_info(request: Request, response: Response = None):
    if request:
        log_entry = {
            "method": request.method,
            "endpoint": request.url.path,
            "status_code": (
                response.status_code if response else status.HTTP_400_BAD_REQUEST
            ),
            "remote_addr": request.client.host,
        }
    else:
        log_entry = {}
    return log_entry


def log_exception(message: str = "Internal server error.", request: Request = None):
    logger.critical(
        message,
        request_detail={
            "endpoint_info": get_endpoint_info(request),
            "traceback": traceback.format_exc(),
        },
    )


async def log_endpoint(request: Request, response, elapsed_time: float):
    status_code = response.status_code
    method = request.method
    url = request.url.path
    remote_addr = request.client.host

    detail = get_endpoint_info(request, response)
    detail |= {"elapsed_time": elapsed_time}
    logger.info(
        f"{method} - {url} - {status_code} - {remote_addr} - {elapsed_time:.6f}ms",
        request_detail=detail,
    )


class skillbridgeLoggerExtension:
    def __init__(self):
        self.logger = logger

    def log_exception(
        self,
        message: str = "Internal Server Error.",
    ):
        configure_logging(std_error=True)
        logger.critical(
            message,
            request_detail={
                "traceback": traceback.format_exc(),
            },
        )
