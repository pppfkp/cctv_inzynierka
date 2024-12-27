from django.contrib import admin, messages
import numpy as np
from face_recognition.models import FaceEmbedding, Recognition
from django.core.exceptions import ValidationError
from .utils import extract_embedding  # Your custom embedding extraction logic
from django.contrib.auth.models import User
from django.shortcuts import render
from django.utils.html import format_html
from PIL import Image
from io import BytesIO
import base64

class FaceEmbeddingAdmin(admin.ModelAdmin):
    list_display = ('user', 'photo')
    readonly_fields = ('embedding',)

    def save_model(self, request, obj, form, change):
        if 'photo' in form.changed_data:  # More robust check for photo change
            photo = form.cleaned_data['photo']
            embedding = extract_embedding(photo)

            if embedding is None:
                raise ValidationError("No face detected or error during embedding extraction. Please upload a valid face photo.")
            
            # Convert to list before saving if it is numpy array
            if isinstance(embedding, np.ndarray):
                embedding = embedding.tolist()
            obj.embedding = embedding
        elif not change: #case for create object without photo
            raise ValidationError("Please upload a photo.")

        super().save_model(request, obj, form, change)

    def get_fields(self, request, obj=None): #exclude embedding from fields
        fields = super().get_fields(request, obj)
        if 'embedding' in fields:
            fields.remove('embedding')
        return fields

admin.site.register(FaceEmbedding, FaceEmbeddingAdmin)

admin.site.register(Recognition)
# admin.site.register(FaceEmbedding)
