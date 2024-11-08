# project/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # path('admin/', admin.site.urls),  
    path('api/', include('face_recognition_api.urls')),  
]
