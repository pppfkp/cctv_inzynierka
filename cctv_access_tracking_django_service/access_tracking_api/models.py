from django.db import models
from django.contrib.auth.models import User
from timescale.db.models.models import TimescaleModel
from timescale.db.models.fields import TimescaleDateTimeField

# Create your models here.

class Entry(TimescaleModel):
    user_id = models.IntegerField() 
    time = TimescaleDateTimeField(interval = "1 second")

    class Meta:
        db_table = 'entry_data'
        app_label = 'access_tracking_api'

    def __str__(self):
               return f"Exit: {self.user_id} on {self.time}"


class Exit(TimescaleModel):
    user_id = models.IntegerField() 
    time = TimescaleDateTimeField(interval = "1 second")

    class Meta:
        db_table = 'exit_data'
        app_label = 'access_tracking_api'

    def __str__(self):
        return f"Exit: {self.user_id} on {self.time}"
