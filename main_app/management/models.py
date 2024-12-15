from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

# Create your models here.
class TrackingSubject(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_inside = models.BooleanField(default=False)

@receiver(post_save, sender=User)
def create_tracking_subjects(sender, instance, created, **kwargs):
    if created:
        TrackingSubject.objects.create(user=instance)
        