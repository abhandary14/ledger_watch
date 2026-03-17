from rest_framework import serializers

from apps.users.models import User


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    organization_name = serializers.CharField(max_length=255)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class UserMeSerializer(serializers.ModelSerializer):
    organization = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "role", "organization"]
        read_only_fields = fields

    def get_organization(self, obj):
        return {"id": str(obj.organization_id), "name": obj.organization.name}


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
