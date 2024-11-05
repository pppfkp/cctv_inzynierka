# Generated by Django 5.1.2 on 2024-11-04 08:27

import django.db.models.deletion
import pgvector.django.vector
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('cctv_admin', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Camera',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('link', models.CharField(max_length=500, unique=True)),
                ('name', models.CharField(max_length=200, unique=True)),
                ('enabled', models.BooleanField(default=True)),
                ('transformation_matrix', pgvector.django.vector.VectorField(blank=True, dimensions=9, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Setting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('setting_key', models.CharField(max_length=100, unique=True)),
                ('value', models.TextField()),
                ('description', models.TextField(blank=True, null=True)),
                ('data_type', models.CharField(choices=[('str', 'String'), ('int', 'Integer'), ('bool', 'Boolean'), ('float', 'Float')], default='str', max_length=10)),
            ],
        ),
        migrations.CreateModel(
            name='CalibrationPoint',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('canvas_x', models.FloatField()),
                ('canvas_y', models.FloatField()),
                ('camera_x', models.FloatField()),
                ('camera_y', models.FloatField()),
                ('camera', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='calibration_points', to='cctv_admin.camera')),
            ],
        ),
    ]
