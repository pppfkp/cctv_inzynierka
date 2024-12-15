from django.contrib import admin
from face_recognition.models import FaceEmbedding, Recognition

# Register your models here.
admin.site.register(FaceEmbedding)
admin.site.register(Recognition)