from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response


@extend_schema(
    tags=["Health"],
    summary="Health check",
    description="Returns `{\"status\": \"ok\"}` when the API is live.",
    responses={
        200: inline_serializer(
            "HealthResponse",
            fields={"status": serializers.CharField()},
        )
    },
)
@api_view(["GET"])
def health(request):
    """
    GET /health
    Returns a simple status payload confirming the API is live.
    """
    return Response({"status": "ok"})
