# Generated by Django 5.1.4 on 2025-02-01 14:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stats', '0005_entry'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='exit',
            name='user',
        ),
        migrations.RemoveField(
            model_name='detection',
            name='xywh',
        ),
        migrations.AddField(
            model_name='detection',
            name='h',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='detection',
            name='w',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='detection',
            name='x',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='detection',
            name='y',
            field=models.IntegerField(default=0),
        ),
        migrations.DeleteModel(
            name='Enter',
        ),
        migrations.DeleteModel(
            name='Exit',
        ),
    ]
