import unicodedata

from django.db import migrations

SKI_SLUG = "ski"
SKI_NAME = "Esquí"


class SkiNameTakenError(Exception):
    pass


def _comparable(name):
    # La BD no iguala NFC con NFD y depende de su localización: se compara aquí
    return unicodedata.normalize("NFC", name).casefold()


def apply_ski(apps, schema_editor):
    Category = apps.get_model("categories", "Category")
    categories = Category.objects.using(schema_editor.connection.alias)
    other_names = categories.exclude(slug=SKI_SLUG).values_list("name", flat=True)
    if any(_comparable(name) == _comparable(SKI_NAME) for name in other_names):
        raise SkiNameTakenError("Otra categoría ya se llama Esquí: no se cambia nada.")
    categories.update_or_create(slug=SKI_SLUG, defaults={"name": SKI_NAME})


def reverse_ski(apps, schema_editor):
    Category = apps.get_model("categories", "Category")
    categories = Category.objects.using(schema_editor.connection.alias)
    categories.filter(slug=SKI_SLUG).delete()


class Migration(migrations.Migration):
    dependencies = [("categories", "0002_seed_categories")]

    operations = [migrations.RunPython(apply_ski, reverse_ski)]
