# Generated by Django 5.1.4 on 2024-12-24 10:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('face_recognition', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='faceembedding',
            name='photo',
            field=models.ImageField(default=None, upload_to='face_photos/'),
            preserve_default=False,
        ),
    ]
