from django.db import models

class Entry(models.Model):
    user_id = models.IntegerField()  
    detection_date = models.DateTimeField()  

    class Meta:
        db_table = "entry"

class Exit(models.Model):
    user_id = models.IntegerField()  
    detection_date = models.DateTimeField()  

    class Meta:
        db_table = "exit"


    


