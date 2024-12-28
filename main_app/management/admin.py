from django.contrib import admin
from management.models import Camera, Setting, Boundary, Zone

# Register your models here.
admin.site.register(Camera)
admin.site.register(Setting)
admin.site.register(Boundary)
admin.site.register(Zone)