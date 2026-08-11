from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        payload = {
            "success": False,
            "errors": response.data,
            "status_code": response.status_code,
        }
        response.data = payload
    return response


class ServiceError(Exception):
    """Domain/service layer error with optional code."""

    def __init__(self, message, code="error"):
        self.message = message
        self.code = code
        super().__init__(message)
