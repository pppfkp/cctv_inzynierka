# Generated by Django 5.1.4 on 2024-12-20 10:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('management', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='setting',
            old_name='setting_key',
            new_name='key',
        ),
    ]