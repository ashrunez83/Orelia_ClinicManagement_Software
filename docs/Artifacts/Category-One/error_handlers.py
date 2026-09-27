# CS 499 Enhancement:
# Centralizes unexpected exception handling so internal error details
# are logged without exposing sensitive implementation details to clients.

import logging

from fastapi import Request
from fastapi.responses import JSONResponse


logger = logging.getLogger(__name__)


async def general_exception_handler(
    request: Request,
    exc: Exception
):
    logger.exception(
        "Unhandled error while processing %s %s",
        request.method,
        request.url.path
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "An internal server error occurred."
        }
    )