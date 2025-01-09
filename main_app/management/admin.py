import json
from django.contrib import admin
from management.models import Camera, Setting, Boundary, Zone
from django.contrib import admin
from django.urls import path
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
import cv2
import base64
from .models import Boundary, Camera
from django.utils.html import format_html
from django.urls import reverse

class CustomAdminSite(admin.AdminSite):
    index_template = 'admin/custom_admin_template.html'

# Register your custom admin site
admin_site = CustomAdminSite(name='custom_admin')

# Register your models with the custom admin site
# admin_site.register(YourModel)

# Replace the default admin site
admin.site = admin_site

class BoundaryAdmin(admin.ModelAdmin):
    list_display = ('zone', 'camera', 'edit_link')
    exclude = ['polygon']

    def save_model(self, request, obj, form, change):
        if not obj.polygon:
            obj.polygon = [235,95,300,100,500,100,500,200,500,300,300,300,100,300,100,200,95,110,156,102]
        super().save_model(request, obj, form, change)

    # change_list_template = 'admin/boundary_change_list.html'

    def edit_link(self, obj):
        return format_html(
            '<a href="{}">Edit Boundary</a>',
            reverse('admin:edit-boundary', args=[obj.pk])
        )
    edit_link.short_description = "Edit"

    # Custom URL for editing a boundary
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:boundary_id>/edit-boundary/', self.admin_site.admin_view(self.edit_boundary_view),
                 name='edit-boundary'),
        ]
        return custom_urls + urls

    # The custom view
    def edit_boundary_view(self, request, boundary_id):
        boundary = get_object_or_404(Boundary, pk=boundary_id)
        camera = boundary.camera

        # Open the camera stream using OpenCV
        cap = cv2.VideoCapture(camera.link)
        if not cap.isOpened():
            return JsonResponse({'error': 'Could not open camera stream'}, status=500)

        ret, frame = cap.read()
        cap.release()

        if not ret:
            return JsonResponse({'error': 'Could not capture image'}, status=500)

        # Convert the frame to base64
        _, jpeg = cv2.imencode('.jpg', frame)
        image_data = base64.b64encode(jpeg.tobytes()).decode('utf-8')

        if request.method == "POST":
            # Process the points sent via AJAX
            data = json.loads(request.body)
            points = data.get('points', [])
            if not points or len(points) % 2 != 0:
                return JsonResponse({'error': 'Invalid points data'}, status=400)

            boundary.polygon = points
            boundary.save()
            return JsonResponse({'message': 'Boundary updated successfully!'})

        # Render the custom form
        return render(request, 'admin/edit_boundary.html', {
            'boundary': boundary,
            'camera': camera,
            'image_data': image_data,
            'csrf_token': request.META.get("CSRF_COOKIE"),
        })


admin.site.register(Boundary, BoundaryAdmin)

# Register your models here.
admin.site.register(Camera)
admin.site.register(Setting)
# admin.site.register(Boundary)
admin.site.register(Zone)