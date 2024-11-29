from django.db import models
from django.contrib.auth.models import User
from timescale.db.models.models import TimescaleModel

# detections
# CREATE TABLE IF NOT EXISTS tracking_data (
# 	id SERIAL PRIMARY KEY,
# 	camera_link TEXT NOT NULL,
# 	track_id INT NOT NULL,
# 	user_id INT,
# 	detection_date DATE NOT NULL,
# 	detection_time TIME NOT NULL,
# 	x_center FLOAT NOT NULL,
# 	y_center FLOAT NOT NULL,
# 	width FLOAT NOT NULL,
# 	height FLOAT NOT NULL
# );

# entries
# CREATE TABLE IF NOT EXISTS entry_data (
# 	id SERIAL PRIMARY KEY,
# 	user_id INT,
# 	detection_date DATE NOT NULL,
# 	detection_time TIME NOT NULL,
# );

# exits
# CREATE TABLE IF NOT EXISTS exit_data (
# 	id SERIAL PRIMARY KEY,
# 	user_id INT,
# 	detection_date DATE NOT NULL,
# 	detection_time TIME NOT NULL,
# );


# Create your models here.

class Entry(TimescaleModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    detection_date = models.DateField()
    detection_time = models.TimeField()

    class Meta:
        db_table = 'entry_data'

    def __str__(self):
        return f"Entry: {self.user.username} on {self.detection_date} at {self.detection_time}"


class Exit(TimescaleModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    detection_date = models.DateField()
    detection_time = models.TimeField()

    class Meta:
        db_table = 'exit_data'

    def __str__(self):
        return f"Exit: {self.user.username} on {self.detection_date} at {self.detection_time}"
