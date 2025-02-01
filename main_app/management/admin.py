import json
from django.contrib import admin
from management.models import Camera, Setting
from django.contrib import admin
from django.urls import path
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
import cv2
import base64
from .models import  Camera
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



# Register your models here.
admin.site.register(Camera)
admin.site.register(Setting)