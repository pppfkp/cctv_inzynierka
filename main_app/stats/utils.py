from datetime import datetime
import io
from django.apps import apps
import numpy as np
import cv2
from django.core.files.storage import default_storage
from PIL import Image
import logging
from django.db.models.functions import Round
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError

Detection = apps.get_model('stats', 'Detection')
Entry = apps.get_model('stats', 'Entry')
Camera = apps.get_model('management', 'Camera')
Recognition = apps.get_model('face_recognition', 'Recognition')

from django.db.models import Count
from django.utils.timezone import make_aware, is_naive
from typing import Optional, Dict

from django.db.models import Avg
import matplotlib.pyplot as plt
import numpy as np
import cv2
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

def recognize_entry(recognition_id, user_id):
    # Get the recognition object
    recognition = get_object_or_404(Recognition, id=recognition_id)
    
    # Check if user already has an active entry (recognition_out is None)
    active_entry = Entry.objects.filter(
        user_id=user_id,
        recognition_out__isnull=True
    ).first()
    
    if active_entry:
        raise ValidationError("User already has an active entry. Must exit first.")
    
    # Create new entry
    entry = Entry.objects.create(
        user_id=user_id,
        recognition_in_id=recognition_id
    )
    
    return entry

def recognize_exit(recognition_id, user_id):
    # Get the recognition object
    recognition = get_object_or_404(Recognition, id=recognition_id)
    
    # Find the user's active entry
    active_entry = Entry.objects.filter(
        user_id=user_id,
        recognition_out__isnull=True
    ).first()
    
    if not active_entry:
        raise ValidationError("No active entry found for user. Must enter first.")
    
    # Update the entry with exit recognition
    active_entry.recognition_out = recognition
    active_entry.save()
    
    return active_entry