# Generated by Django 5.1.4 on 2025-02-02 19:16

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('face_recognition', '__first__'),
        ('management', '__first__'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Detection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('track_id', models.BigIntegerField()),
                ('time', models.DateTimeField()),
                ('x', models.IntegerField(default=0)),
                ('y', models.IntegerField(default=0)),
                ('w', models.IntegerField(default=0)),
                ('h', models.IntegerField(default=0)),
                ('camera', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='detections', to='management.camera')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='detections', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Entry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recognition_in', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entries_in', to='face_recognition.recognition')),
                ('recognition_out', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='entries_out', to='face_recognition.recognition')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entries', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
