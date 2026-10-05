from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """The project's user: Django's, kept swappable from the first migration."""
