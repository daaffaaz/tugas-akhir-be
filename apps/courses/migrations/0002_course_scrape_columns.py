# Generated manually for scrape-aligned Course columns

from django.db import migrations, models


def backfill_video_hours_and_scraped_date(apps, schema_editor):
    Course = apps.get_model('courses', 'Course')
    for c in Course.objects.iterator(chunk_size=500):
        updates = {}
        if c.duration_hours is not None and c.video_hours is None:
            updates['video_hours'] = c.duration_hours
        if c.scraped_at and not c.scraped_date:
            updates['scraped_date'] = c.scraped_at.date()
        if updates:
            for k, v in updates.items():
                setattr(c, k, v)
            Course.objects.filter(pk=c.pk).update(**updates)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='course',
            old_name='instructor_name',
            new_name='instructor',
        ),
        migrations.RenameField(
            model_name='course',
            old_name='review_count',
            new_name='reviews_count',
        ),
        migrations.RenameField(
            model_name='course',
            old_name='difficulty_level',
            new_name='level',
        ),
        migrations.AddField(
            model_name='course',
            name='duration',
            field=models.TextField(blank=True, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='course',
            name='video_hours',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name='course',
            name='reading_count',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='course',
            name='assignment_count',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='course',
            name='what_you_learn',
            field=models.TextField(blank=True, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='course',
            name='tag',
            field=models.TextField(blank=True, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='course',
            name='scraped_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_video_hours_and_scraped_date, noop_reverse),
        migrations.RemoveField(
            model_name='course',
            name='duration_hours',
        ),
    ]
