import unicodedata

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.functions import Lower

from apps.core.text import reject_control_characters


class UserManager(BaseUserManager):
    @classmethod
    def normalize_email(cls, email):
        email = email.strip()
        email = unicodedata.normalize("NFKC", email)
        return email.lower()

    def get_by_natural_key(self, email):
        return super().get_by_natural_key(self.normalize_email(email))


class User(AbstractUser):
    username = None
    email = models.EmailField(
        max_length=254,
        unique=True,
        validators=[reject_control_characters],
    )

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="users_user_email_lower_unique",
                violation_error_code="email_taken",
            ),
        ]

    def __str__(self):
        return f"User {self.pk}"
