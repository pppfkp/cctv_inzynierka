# Generated by Django 5.1.4 on 2025-01-14 11:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('management', '0007_remove_camera_enabled_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='camera',
            name='enabled',
            field=models.BooleanField(default=True),
        ),
    ]
