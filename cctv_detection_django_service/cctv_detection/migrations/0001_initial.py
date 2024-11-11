# Generated by Django 5.1.3 on 2024-11-11 08:09

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Entry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.IntegerField()),
                ('detection_date', models.DateTimeField()),
            ],
            options={
                'db_table': 'entry',
            },
        ),
        migrations.CreateModel(
            name='Exit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.IntegerField()),
                ('detection_date', models.DateTimeField()),
            ],
            options={
                'db_table': 'exit',
            },
        ),
    ]