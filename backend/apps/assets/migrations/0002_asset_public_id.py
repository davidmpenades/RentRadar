from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("assets", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="asset",
            name="public_id",
            field=models.UUIDField(editable=False, null=True),
        ),
    ]
