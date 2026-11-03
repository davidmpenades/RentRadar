import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("assets", "0003_fill_asset_public_id")]

    operations = [
        migrations.AlterField(
            model_name="asset",
            name="public_id",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
