from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

@receiver(post_save, sender=User)
def create_favorites(sender, instance, created, **kwargs):
    if created:
        Favorites.objects.create(user=instance)