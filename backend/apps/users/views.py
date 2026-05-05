from drf_spectacular.utils import OpenApiExample, extend_schema, extend_schema_view
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    EmailTokenObtainPairSerializer,
    RegisterSerializer,
    UserMeSerializer,
    UserTokenSerializer,
)


@extend_schema(
    tags=["Auth"],
    request=RegisterSerializer,
    responses=UserTokenSerializer,
    examples=[
        OpenApiExample(
            "Register request",
            value={
                "email": "user@example.com",
                "username": "user1",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
            request_only=True,
        ),
        OpenApiExample(
            "Register response",
            value={
                "access": "jwt-access-token",
                "refresh": "jwt-refresh-token",
                "user": {
                    "id": 1,
                    "email": "user@example.com",
                    "username": "user1",
                    "role": "USER",
                    "is_verified": False,
                },
            },
            response_only=True,
        ),
    ],
)
class RegisterView(APIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserTokenSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=["Auth"],
    request=EmailTokenObtainPairSerializer,
    examples=[
        OpenApiExample(
            "Login request",
            value={"email": "user@example.com", "password": "StrongPass123!"},
            request_only=True,
        ),
    ],
)
class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = EmailTokenObtainPairSerializer


@extend_schema(
    tags=["Auth"],
    request=TokenRefreshSerializer,
    examples=[
        OpenApiExample(
            "Refresh request",
            value={"refresh": "jwt-refresh-token"},
            request_only=True,
        ),
    ],
)
class RefreshView(TokenRefreshView):
    serializer_class = TokenRefreshSerializer


@extend_schema_view(
    get=extend_schema(tags=["Users"], summary="Get current user"),
    patch=extend_schema(
        tags=["Users"],
        summary="Update current user/profile",
        examples=[
            OpenApiExample(
                "Update profile",
                value={
                    "username": "new_username",
                    "profile": {
                        "bio": "Backend developer",
                        "phone": "+380000000000",
                    },
                },
                request_only=True,
            ),
        ],
    ),
)
class UserMeView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserMeSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user
