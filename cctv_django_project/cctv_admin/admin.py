from django.contrib import admin
from .models import Camera, Setting, CalibrationPoint

class CameraAdmin(admin.ModelAdmin):
    list_display = ('name', 'link', 'enabled')
    search_fields = ('name', 'link')
    list_filter = ('enabled',)

    fieldsets = (
        (None, {
            'fields': ('name', 'link', 'enabled')
        }),
        ('Advanced Options', {
            'fields': ('transformation_matrix',),
            'classes': ('collapse',),  # Makes this section collapsible
        }),
    )

class SettingAdmin(admin.ModelAdmin):
    list_display = ('setting_key', 'value', 'data_type')  # Fields to display in the list view
    search_fields = ('setting_key',)  # Add search functionality
    list_filter = ('data_type',)  # Filter by data type

class CalibrationPointAdmin(admin.ModelAdmin):
    list_display = ('camera', 'canvas_x', 'canvas_y', 'camera_x', 'camera_y')  # Fields to display in the list view
    search_fields = ('camera__name',)  # Search by camera name
    list_filter = ('camera',)  # Filter by camera

admin.site.register(CalibrationPoint, CalibrationPointAdmin)
admin.site.register(Camera, CameraAdmin)
admin.site.register(Setting, SettingAdmin)
