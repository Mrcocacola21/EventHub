from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiExample
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import serializers


@extend_schema(
    tags=["Health"],
    responses=inline_serializer(
        name="HealthResponse",
        fields={
            "status": serializers.CharField(),
            "service": serializers.CharField(),
        },
    ),
    examples=[
        OpenApiExample(
            "Healthy service",
            value={"status": "ok", "service": "eventhub-backend"},
            response_only=True,
        ),
    ],
)
@api_view(["GET"])
def health_check(request):
    return Response(
        {
            "status": "ok",
            "service": "eventhub-backend",
        }
    )
