from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.organizations.models import Organization


class OrganizationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            org = Organization.objects.get(pk=pk)
        except Organization.DoesNotExist:
            return None
        if str(org.id) != str(user.organization_id):
            return None
        return org

    @extend_schema(
        tags=["Organizations"],
        summary="Update organization name",
    )
    def patch(self, request, pk):
        org = self.get_object(pk, request.user)
        if org is None:
            return Response(
                {"detail": "Not found or access denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        name = request.data.get("name", "").strip()
        if not name:
            return Response(
                {"name": ["This field may not be blank."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        org.name = name
        org.save(update_fields=["name"])
        return Response(
            {
                "id": str(org.id),
                "name": org.name,
                "created_at": org.created_at.isoformat(),
            }
        )
