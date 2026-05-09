from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("learning_paths", "0004_add_regenerate_and_replacement_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="learningpathcourse",
            name="phase_number",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                help_text="Phase this course belongs to. Null means manually added without a specific phase.",
            ),
        ),
    ]
