from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status as http_status


class ServiceError(Exception):
    """Domain/service layer error with optional code."""

    def __init__(self, message, code="error"):
        self.message = message
        self.code = code
        super().__init__(message)


def custom_exception_handler(exc, context):
    if isinstance(exc, ServiceError):
        return Response(
            {"success": False, "detail": exc.message, "code": exc.code, "status_code": 400},
            status=http_status.HTTP_400_BAD_REQUEST,
        )
    response = exception_handler(exc, context)
    if response is not None:
        rid = getattr(context.get("request"), "request_id", None)
        payload = {
            "success": False,
            "errors": response.data,
            "status_code": response.status_code,
        }
        if rid:
            payload["request_id"] = rid
        response.data = payload
    return response
