from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def health(request):
    """
    GET /health
    Returns a simple status payload confirming the API is live.
    """
    return Response({"status": "ok"})
