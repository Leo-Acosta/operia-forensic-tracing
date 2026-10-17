"""Fixed public errors: never serialize driver exceptions or rejected input."""
import logging

from fastapi.exceptions import RequestValidationError, ResponseValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.exc import IntegrityError
from starlette.responses import JSONResponse


def install_safe_errors(app):
    def response(request, code, status):
        request_id = getattr(request.state, "request_id", "")
        logging.getLogger("operia.security").warning(
            "api_failure code=%s request_id=%s", code, request_id)
        return JSONResponse({"detail": code, "request_id": request_id}, status_code=status)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exception):
        return response(request, "request_validation_failed", 422)

    @app.exception_handler(ResponseValidationError)
    async def invalid_response(request, exception):
        return response(request, "response_validation_failed", 500)

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, exception):
        if isinstance(exception, IntegrityError) and str(exception.orig) in {"custody_append_only", "custody_parent_preserved"}:
            return response(request, "custody_append_only", 409)
        return response(request, "database_operation_failed", 503)
