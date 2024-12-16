from django.contrib import admin, messages
from face_recognition.models import FaceEmbedding, Recognition
from .utils import extract_embedding  # Your custom embedding extraction logic
from django.contrib.auth.models import User
from django.shortcuts import render
from django.utils.html import format_html
from PIL import Image
from io import BytesIO
import base64

class FaceEmbeddingAdmin(admin.ModelAdmin):
    add_form_template = "admin/face_embedding_form.html"
    change_form_template = "admin/face_embedding_change_form.html"


    def save_model(self, request, obj, form, change):
        status = 'success'  # Set default status to success

        if 'image' in request.POST:  # Extract embedding if an image was submitted
            image_data = request.POST['image']
            try:
                # Split the Base64 image data and decode
                format, imgstr = image_data.split(';base64,') 
                image = Image.open(BytesIO(base64.b64decode(imgstr)))

                # Extract embedding from the image
                embedding = extract_embedding(image)

                if embedding is None:
                    # If no embedding was detected, show error and prevent save
                    messages.error(request, "Error processing image: No face detected in the image.")
                    status = 'error'  # Set status to error
                else:
                    obj.embedding = embedding.tolist()  # Store as list

            except Exception as e:
                # Add error message and prevent saving
                messages.error(request, f"Error processing image: {str(e)}")
                status = 'error'  # Set status to error

        if status == 'success':
            # Only save if no error occurred
            super().save_model(request, obj, form, change)
            # Manually trigger success message here
            messages.success(request, "Face embedding extracted and saved successfully.")
        else:
            # Prevent saving and show the add form again with error
            return
            

    def embedding_display(self, obj):
        # Convert the embedding to a string for display in the admin
        if obj.embedding.any():
            return format_html('<pre>{}</pre>', str(obj.embedding))  # Preformatted text display
        return "No embedding"

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['users'] = User.objects.all()  # Pass user list to the template
        return super().add_view(request, form_url, extra_context=extra_context)

    list_display = ('user', 'embedding_display')  # Display embedding in the list view

admin.site.register(FaceEmbedding, FaceEmbeddingAdmin) # comment out to disable custom admin page
admin.site.register(Recognition)
# admin.site.register(FaceEmbedding)
