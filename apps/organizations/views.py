import secrets

from django.db import IntegrityError
from django.db import transaction as db_transaction
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from apps.audit.models import AuditLog
from apps.organizations.models import Organization, SecurityChallenge
from apps.users.models import User
from apps.users.permissions import IsOwner
from apps.users.serializers import CreateMemberSerializer, OrgMemberSerializer, UpdateMemberRoleSerializer



def _validate_and_consume_challenge(user, password: str, challenge: str) -> str | None:
    """
    Validate password + challenge. Returns None on success, or an error string.

    Challenge consumption is a single atomic DB DELETE so two concurrent
    requests cannot both validate the same token.
    """
    if not password or not challenge:
        return "password and challenge are required."
    if not user.check_password(password):
        return "Password is incorrect."
    if not SecurityChallenge.consume(user, challenge):
        return "Challenge has expired or does not match. Please request a new one."
    return None


class OrgDirectoryView(APIView):
    """
    GET /api/v1/organizations/directory/

    Returns all members of the authenticated user's organization.
    Accessible to all roles (employee, admin, owner) — read-only.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Organizations"],
        summary="List organization members (read-only, all roles)",
    )
    def get(self, request):
        members = User.objects.filter(
            organization_id=request.user.organization_id
        ).order_by("created_at")
        serializer = OrgMemberSerializer(members, many=True)
        return Response(serializer.data)


class SecurityChallengeView(APIView):
    """
    GET /api/v1/organizations/security-challenge/

    Generates a fresh 32-character challenge token for the authenticated owner.
    The token is persisted in the DB (5-minute TTL) and must be submitted alongside
    the owner's password when performing destructive actions (delete member, transfer ownership).
    """

    permission_classes = [IsOwner]

    @extend_schema(
        tags=["Organizations"],
        summary="Generate a security challenge token",
        responses={200: OpenApiResponse(description="Returns a 32-char challenge string.")},
    )
    def get(self, request):
        token = SecurityChallenge.issue(request.user)
        return Response({"challenge": token})


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


class OrgMemberListCreateView(APIView):
    """
    GET  /api/v1/organizations/members/ — list all members of the owner's org
    POST /api/v1/organizations/members/ — create a new member (admin or employee)

    Both actions restricted to OWNER role only.
    """

    permission_classes = [IsOwner]

    @extend_schema(
        tags=["Organizations"],
        summary="List organization members",
    )
    def get(self, request):
        members = User.objects.filter(
            organization_id=request.user.organization_id
        ).order_by("created_at")
        serializer = OrgMemberSerializer(members, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=["Organizations"],
        summary="Add a new member to the organization",
        request=CreateMemberSerializer,
    )
    def post(self, request):
        serializer = CreateMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = User.objects.normalize_email(serializer.validated_data["email"])

        if User.objects.filter(email=email).exists():
            return Response(
                {"email": ["A user with this email already exists."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with db_transaction.atomic():
                member = User.objects.create_user(
                    email=email,
                    password=serializer.validated_data["password"],
                    organization_id=request.user.organization_id,
                    role=serializer.validated_data["role"],
                    first_name=serializer.validated_data.get("first_name", ""),
                    last_name=serializer.validated_data.get("last_name", ""),
                )
                AuditLog.objects.create(
                    organization_id=request.user.organization_id,
                    event_type="USER_REGISTERED",
                    metadata={
                        "user_id": str(member.id),
                        "created_by": str(request.user.id),
                        "role": member.role,
                    },
                )
        except IntegrityError:
            return Response(
                {"email": ["A user with this email already exists."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(OrgMemberSerializer(member).data, status=status.HTTP_201_CREATED)


class OrgMemberDetailView(APIView):
    """
    PATCH /api/v1/organizations/members/<uuid>/ — change a member's role (admin ↔ employee)
    DELETE /api/v1/organizations/members/<uuid>/ — remove a member from the org

    Both restricted to OWNER role. Cannot target the owner themselves.
    """

    permission_classes = [IsOwner]

    def _get_member(self, request, pk):
        from django.shortcuts import get_object_or_404
        member = get_object_or_404(
            User.objects.filter(organization_id=request.user.organization_id),
            pk=pk,
        )
        return member

    @extend_schema(
        tags=["Organizations"],
        summary="Update a member's role",
        request=UpdateMemberRoleSerializer,
    )
    def patch(self, request, pk):
        member = self._get_member(request, pk)

        if member.role == User.Role.OWNER:
            return Response(
                {"detail": "Cannot change the owner's role directly. Use transfer-ownership instead."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if str(member.id) == str(request.user.id):
            return Response(
                {"detail": "Cannot change your own role."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = UpdateMemberRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with db_transaction.atomic():
            member.role = serializer.validated_data["role"]
            member.save(update_fields=["role"])

            AuditLog.objects.create(
                organization_id=request.user.organization_id,
                event_type="MEMBER_ROLE_UPDATED",
                metadata={
                    "member_id": str(member.id),
                    "new_role": member.role,
                    "updated_by": str(request.user.id),
                },
            )

        return Response(OrgMemberSerializer(member).data)

    @extend_schema(
        tags=["Organizations"],
        summary="Remove a member from the organization",
        responses={
            204: OpenApiResponse(description="Member removed."),
            400: OpenApiResponse(description="Cannot remove owner or self."),
            404: OpenApiResponse(description="Member not found."),
        },
    )
    def delete(self, request, pk):
        member = self._get_member(request, pk)

        if member.role == User.Role.OWNER:
            return Response(
                {"detail": "Cannot remove the owner. Use transfer-ownership to reassign ownership first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if str(member.id) == str(request.user.id):
            return Response(
                {"detail": "Cannot remove yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        err = _validate_and_consume_challenge(
            request.user,
            request.data.get("password", ""),
            request.data.get("challenge", ""),
        )
        if err:
            return Response({"detail": err}, status=status.HTTP_400_BAD_REQUEST)

        with db_transaction.atomic():
            AuditLog.objects.create(
                organization_id=request.user.organization_id,
                event_type="MEMBER_REMOVED",
                metadata={
                    "member_id": str(member.id),
                    "member_email": member.email,
                    "removed_by": str(request.user.id),
                },
            )

            member.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TransferOwnershipView(APIView):
    """
    POST /api/v1/organizations/transfer-ownership/

    Transfer org ownership to an admin in the same org.

    - The target user must be ADMIN in the caller's org.
    - The old owner's account is DELETED (tokens invalidated by cascade).
    - The new owner's email changes to owner@<their_current_domain>.
    - The new owner's role changes to OWNER.
    - All done atomically.

    Caller (old owner) must log out immediately after — their account no longer exists.
    """

    permission_classes = [IsOwner]

    @extend_schema(
        tags=["Organizations"],
        summary="Transfer ownership to an admin",
        responses={
            200: OpenApiResponse(description="Ownership transferred. Caller's account deleted."),
            400: OpenApiResponse(description="Target is not an admin in this org, or email conflict."),
            404: OpenApiResponse(description="Target user not found."),
        },
    )
    def post(self, request):
        from django.shortcuts import get_object_or_404

        err = _validate_and_consume_challenge(
            request.user,
            request.data.get("password", ""),
            request.data.get("challenge", ""),
        )
        if err:
            return Response({"detail": err}, status=status.HTTP_400_BAD_REQUEST)

        new_owner_id = request.data.get("new_owner_id")
        if not new_owner_id:
            return Response(
                {"detail": "new_owner_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_owner = get_object_or_404(
            User.objects.filter(organization_id=request.user.organization_id),
            pk=new_owner_id,
        )

        if new_owner.role != User.Role.ADMIN:
            return Response(
                {"detail": "Target user must be an admin in your organization."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # New email: owner@<new_owner's current domain>
        new_owner_domain = new_owner.email.split("@")[1]
        new_email = f"owner@{new_owner_domain}"

        # Make sure new email isn't already taken by someone other than the current owner
        if User.objects.filter(email=new_email).exclude(pk=request.user.pk).exists():
            return Response(
                {"detail": f"Email {new_email} is already in use by another account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_owner = request.user

        with db_transaction.atomic():
            # Write audit log BEFORE mutating either row so real emails are captured.
            AuditLog.objects.create(
                organization_id=old_owner.organization_id,
                event_type="OWNERSHIP_TRANSFERRED",
                metadata={
                    "old_owner_id": str(old_owner.id),
                    "old_owner_email": old_owner.email,
                    "new_owner_id": str(new_owner.id),
                    "new_owner_email": new_email,
                },
            )

            # Free the old owner's email slot FIRST so the unique constraint is
            # never violated when new_owner claims new_email (which may equal the
            # old owner's current email when both share the same domain).
            old_owner.email = f"deleted-{old_owner.id}@deleted"
            old_owner.save(update_fields=["email"])

            # Promote new owner now that the email slot is free.
            new_owner.email = new_email
            new_owner.role = User.Role.OWNER
            new_owner.save(update_fields=["email", "role"])

            # Delete old owner — cascades to OutstandingToken, invalidating sessions.
            old_owner.delete()

        return Response({"transferred": True}, status=status.HTTP_200_OK)
