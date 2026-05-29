from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('questionnaires', '0002_userquestionnaireanswer'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddIndex(
            model_name='question',
            index=models.Index(fields=['is_active', 'order_number'], name='questions_is_acti_idx'),
        ),
    ]
