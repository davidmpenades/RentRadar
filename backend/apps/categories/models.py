from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower

from apps.core.text import reject_control_characters

SLUG_PATTERN = r"\A[a-z0-9]+(?:-[a-z0-9]+)*\Z"


class Category(models.Model):
    slug = models.CharField(
        max_length=50,
        unique=True,
        validators=[RegexValidator(SLUG_PATTERN, code="invalid")],
    )
    name = models.CharField(
        max_length=60,
        validators=[reject_control_characters],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                name="categories_category_name_lower_unique",
                violation_error_code="name_taken",
            ),
        ]

    def __str__(self):
        return self.name
