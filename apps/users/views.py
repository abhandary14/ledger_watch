from django.contrib.auth import authenticate
from django.db import transaction as db_transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.models import AuditLog
from apps.organizations.models import Organization
from apps.users.models import User
from apps.users.serializers import LoginSerializer, LogoutSerializer, RegisterSerializer, UserMeSerializer


class RegisterView(APIView):
    @extend_schema(
        tags=["Auth"],
        summary="Register a new user and organization",
        request=RegisterSerializer,
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        org_name = serializer.validated_data["organization_name"]

        if User.objects.filter(email=email).exists():
            return Response(
                {"email": ["A user with this email already exists."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with db_transaction.atomic():
            org = Organization.objects.create(name=org_name)
            user = User.objects.create_user(
                email=email,
                password=password,
                organization=org,
                role=User.Role.OWNER,
            )
            AuditLog.objects.create(
                organization=org,
                event_type="USER_REGISTERED",
                metadata={"user_email": email},
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "organization_id": str(org.id),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    @extend_schema(
        tags=["Auth"],
        summary="Log in and receive JWT tokens",
        request=LoginSerializer,
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = authenticate(request, username=email, password=password)
        if user is None:
            return Response(
                {"detail": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        })


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Log out by blacklisting the refresh token",
        request=LogoutSerializer,
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            token.blacklist()
        except TokenError:
            return Response(
                {"detail": "Invalid or expired refresh token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Get current user and organization",
    )
    def get(self, request):
        serializer = UserMeSerializer(request.user)
        return Response(serializer.data)
