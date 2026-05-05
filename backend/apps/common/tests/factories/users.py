import factory
from django.contrib.auth import get_user_model


User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    username = factory.Sequence(lambda n: f"user{n}")
    role = User.Roles.USER
    is_verified = False
    is_active = True
    password = "StrongPass123!"

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", "StrongPass123!")
        manager = cls._get_manager(model_class)
        return manager.create_user(*args, password=password, **kwargs)


class OrganizerFactory(UserFactory):
    email = factory.Sequence(lambda n: f"organizer{n}@example.com")
    username = factory.Sequence(lambda n: f"organizer{n}")
    role = User.Roles.ORGANIZER
    is_verified = True


class AdminUserFactory(UserFactory):
    email = factory.Sequence(lambda n: f"admin{n}@example.com")
    username = factory.Sequence(lambda n: f"admin{n}")
    role = User.Roles.ADMIN
    is_staff = True
    is_verified = True


class SuperUserFactory(AdminUserFactory):
    email = factory.Sequence(lambda n: f"superuser{n}@example.com")
    is_superuser = True
