import uuid


class RequestIDMiddleware:
    """Attach an X-Request-ID to every request/response for log correlation."""

    header = "HTTP_X_REQUEST_ID"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        rid = request.META.get(self.header) or str(uuid.uuid4())
        request.request_id = rid
        response = self.get_response(request)
        response["X-Request-ID"] = rid
        return response
