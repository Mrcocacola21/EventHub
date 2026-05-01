from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Profile

User = get_user_model()


class UserShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "username", "role")


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "role",
            "is_verified",
            "date_joined",
            "created_at",
            "updated_at",
        )


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Profile
        fields = (
            "id",
            "user",
            "avatar",
            "bio",
            "phone",
            "created_at",
            "updated_at",
        )


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ("email", "username", "password", "password_confirm")
        extra_kwargs = {
            "email": {"required": True},
            "username": {"required": False, "allow_blank": True},
        }

    def validate_email(self, value):
        email = User.objects.normalize_email(value)

        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")

        return email

    def validate(self, attrs):
        password = attrs.get("password")
        password_confirm = attrs.pop("password_confirm", None)

        if password != password_confirm:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )

        validate_password(password)
        return attrs

    def create(self, validated_data):
        validated_data.pop("role", None)
        validated_data.pop("is_staff", None)
        validated_data.pop("is_superuser", None)
        validated_data.pop("is_verified", None)

        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            username=validated_data.get("username", ""),
            role=User.Roles.USER,
        )


class UserTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "username", "role", "is_verified")


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserTokenSerializer(self.user).data
        return data


class UserMeSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(required=False)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "role",
            "is_verified",
            "date_joined",
            "profile",
        )
        read_only_fields = (
            "id",
            "email",
            "role",
            "is_verified",
            "date_joined",
        )

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", None)

        if "username" in validated_data:
            instance.username = validated_data["username"]
            instance.save(update_fields=["username", "updated_at"])

        if profile_data is not None:
            profile, _ = Profile.objects.get_or_create(user=instance)

            for field in ("avatar", "bio", "phone"):
                if field in profile_data:
                    setattr(profile, field, profile_data[field])

            profile.save()

        return instance
