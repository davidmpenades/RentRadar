import uuid

from django.db import migrations


# Un UUID por fila: un default en AddField daría el mismo a todas
def fill_public_id(apps, schema_editor):
    Asset = apps.get_model("assets", "Asset")
    assets = Asset.objects.using(schema_editor.connection.alias)
    pending = assets.filter(public_id__isnull=True)
    for pk in list(pending.values_list("pk", flat=True)):
        assets.filter(pk=pk).update(public_id=uuid.uuid4())


# Deshacer deja el campo vacío y conserva los bienes
def unfill_public_id(apps, schema_editor):
    Asset = apps.get_model("assets", "Asset")
    Asset.objects.using(schema_editor.connection.alias).update(public_id=None)


class Migration(migrations.Migration):
    dependencies = [("assets", "0002_asset_public_id")]

    operations = [migrations.RunPython(fill_public_id, unfill_public_id)]
