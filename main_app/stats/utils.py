from datetime import datetime
from django.apps import apps

Detection = apps.get_model('stats', 'Detection')
Recognition = apps.get_model('face_recognition', 'Recognition')

from django.db.models import Count
from django.utils.timezone import make_aware, is_naive
from typing import Optional, Dict

from django.db.models import Avg



def get_detection_statistics(
    start_time: datetime,
    end_time: datetime,
    camera_id: Optional[int] = None
) -> Dict:
    # Ensure timezone-aware datetimes
    if is_naive(start_time):
        start_time = make_aware(start_time)
    if is_naive(end_time):
        end_time = make_aware(end_time)
        
    # Base query for detections
    base_query = Detection.objects.filter(time__range=(start_time, end_time))
    if camera_id is not None:
        base_query = base_query.filter(camera_id=camera_id)

    # Total detections
    total_detections = base_query.count()
    
    # Unrecognized detections (user_id is null)
    unrecognized_detections = base_query.filter(user__isnull=True).count()
    
    # Recognized detections (user_id is not null)
    recognized_detections = base_query.filter(user__isnull=False).count()
    
    # Detections per user
    detections_per_user = base_query.values('user').annotate(
        detection_count=Count('id')
    ).exclude(user__isnull=True).order_by('-detection_count')
    
    # Base query for recognitions
    recognition_query = Recognition.objects.filter(time__range=(start_time, end_time))
    
    # Recognition statistics
    avg_distance_all = recognition_query.aggregate(Avg('distance'))['distance__avg'] or 0
    total_recognitions = recognition_query.count()
    
    # Average recognition distance per user
    avg_distance_per_user = recognition_query.values('user').annotate(
        avg_distance=Avg('distance')
    ).exclude(user__isnull=True)
    
    return {
        'total_detections': total_detections,
        'unrecognized_detections': unrecognized_detections,
        'recognized_detections': recognized_detections,
        'detections_per_user': detections_per_user,
        'total_recognitions': total_recognitions,
        'avg_distance_all': avg_distance_all,
        'avg_distance_per_user': avg_distance_per_user
    }


def get_distinct_users_in_timeframe(
    start_time: datetime,
    end_time: datetime,
    camera_id: Optional[int] = None
) -> list[int]:
    """
    Retrieve distinct user IDs for detections within a specified time range.
    """
    if is_naive(start_time):
        start_time = make_aware(start_time)
    if is_naive(end_time):
        end_time = make_aware(end_time)
    
    query = Detection.objects.filter(time__range=(start_time, end_time))
    
    if camera_id is not None:
        query = query.filter(camera_id=camera_id)
    
    user_ids = query.values_list('user_id', flat=True).distinct()
    return list(filter(None, user_ids))