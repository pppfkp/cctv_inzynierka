from django.contrib import admin
from management.models import Camera, CalibrationPoint, Setting

# Register your models here.
admin.site.register(Camera)
admin.site.register(CalibrationPoint)
admin.site.register(Setting)