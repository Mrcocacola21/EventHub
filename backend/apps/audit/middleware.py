import uuid


class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.META.get("HTTP_X_REQUEST_ID", "").strip()
        if not request_id:
            request_id = uuid.uuid4().hex

        request.request_id = request_id[:64]
        request.audit_ip_address = self._get_ip_address(request)
        request.audit_user_agent = request.META.get("HTTP_USER_AGENT", "")

        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        return response

    @staticmethod
    def _get_ip_address(request):
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded_for:
            return forwarded_for.split(",", 1)[0].strip()

        return request.META.get("REMOTE_ADDR")
