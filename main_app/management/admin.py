from django.contrib import admin
from management.models import Camera, CalibrationPoint, Floorplan, Setting

# Register your models here.
admin.site.register(Camera)
admin.site.register(CalibrationPoint)
admin.site.register(Setting)
admin.site.register(Floorplan)