from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import UntypedToken


@database_sync_to_async
def get_user_from_token(token):
    user_model = get_user_model()
    try:
        validated_token = UntypedToken(token)
        if validated_token.get("token_type") != "access":
            return AnonymousUser()

        user_id = validated_token.get("user_id")
        if user_id is None:
            return AnonymousUser()

        return user_model.objects.get(id=user_id, is_active=True)
    except (InvalidToken, TokenError, user_model.DoesNotExist, ValueError, TypeError):
        return AnonymousUser()


class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        scope = dict(scope)
        token = self._get_token(scope)
        scope["user"] = await get_user_from_token(token) if token else AnonymousUser()
        return await self.inner(scope, receive, send)

    def _get_token(self, scope):
        query_string = scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)
        token_values = query_params.get("token")
        if token_values:
            return token_values[0]

        for header_name, header_value in scope.get("headers", []):
            if header_name != b"authorization":
                continue
            value = header_value.decode()
            if value.lower().startswith("bearer "):
                return value[7:].strip()

        return None


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)
