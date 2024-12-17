from django.contrib import admin, messages
from face_recognition.models import FaceEmbedding, Recognition
from .utils import extract_embedding  # Your custom embedding extraction logic
from django.contrib.auth.models import User
from django.shortcuts import render
from django.utils.html import format_html
from PIL import Image
from io import BytesIO
import base64

admin.site.register(Recognition)
admin.site.register(FaceEmbedding)
