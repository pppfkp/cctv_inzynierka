import base64
from django.shortcuts import render
from django.views.generic import FormView
from django import forms
from datetime import datetime, timedelta
import cv2
from django.apps import apps
from django.utils import timezone
from django.apps import apps
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Avg, Max, Min, Q
from django.db.models.functions import Trunc
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import F, ExpressionWrapper, DateTimeField, DurationField
from django.shortcuts import get_object_or_404
from .utils import recognize_entry, recognize_exit

@staff_member_required(login_url='admin:login')    
def entries_live_list_view(request):
    Entry = apps.get_model('stats', 'Entry')
    entries = Entry.objects.filter(recognition_out__isnull=True)

    # Create a list to store entry data along with time difference
    entries_with_time = []

    for entry in entries:
        # Assuming entry.recognition_in.time is a timezone-aware datetime object
        entry_time = entry.recognition_in.time

        # Get the current time as a timezone-aware datetime
        current_time = timezone.now()

        # Calculate the time difference
        time_inside = current_time - entry_time

        # Extract hours, minutes, and seconds from the time difference
        hours, remainder = divmod(time_inside.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)

        # Format the time difference as a string
        time_inside_str = f"{int(hours)} hours, {int(minutes)} minutes, {int(seconds)} seconds"

        # Append the entry and its time difference to the list
        entries_with_time.append({
            'entry': entry,
            'time_inside': time_inside_str
        })

    # Pass the list to the template
    return render(request, 'entries_live.html', {'entries': entries_with_time})

@staff_member_required(login_url='admin:login')    
def entries_list_view(request):
    Entry = apps.get_model('stats', 'Entry')
    entries = Entry.objects.all()

    # Create a list to store entry data along with time difference
    entries_with_time = []

    for entry in entries:
        # Assuming entry.recognition_in.time is a timezone-aware datetime object
        entry_time = entry.recognition_in.time
        exit_time = entry.recognition_out.time

        # Calculate the time difference
        time_inside = exit_time

        # Extract hours, minutes, and seconds from the time difference
        hours, remainder = divmod(time_inside.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)

        # Format the time difference as a string
        time_inside_str = f"{int(hours)} hours, {int(minutes)} minutes, {int(seconds)} seconds"

        # Append the entry and its time difference to the list
        entries_with_time.append({
            'entry': entry,
            'time_inside': time_inside_str
        })

    # Pass the list to the template
    return render(request, 'entries.html', {'entries': entries_with_time})

@staff_member_required(login_url='admin:login')    
def entries_list_view(request):
    Entry = apps.get_model('stats', 'Entry')
    entries = Entry.objects.all().order_by('-recognition_in__time')

    # Handle search and filter parameters
    username = request.GET.get('username', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    currently_inside = request.GET.get('currently_inside') == 'on'
    time_filter_type = request.GET.get('time_filter_type', 'in')  # 'in' or 'out'

    if username:
        entries = entries.filter(user__username__icontains=username)

    if currently_inside:
        entries = entries.filter(recognition_out__isnull=True)

    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d')
            if time_filter_type == 'in':
                entries = entries.filter(recognition_in__time__date__gte=date_from)
            else:
                entries = entries.filter(recognition_out__time__date__gte=date_from)
        except ValueError:
            pass

    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d')
            if time_filter_type == 'in':
                entries = entries.filter(recognition_in__time__date__lte=date_to)
            else:
                entries = entries.filter(recognition_out__time__date__lte=date_to)
        except ValueError:
            pass

    # Process entries and calculate time differences
    entries_with_time = []
    current_time = timezone.now()
    
    for entry in entries:
        entry_time = entry.recognition_in.time
        exit_time = entry.recognition_out.time if entry.recognition_out else current_time
        
        # Calculate time difference (either until exit or until now)
        time_inside = exit_time - entry_time
        
        # Calculate hours, minutes, seconds
        total_seconds = time_inside.total_seconds()
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        # Format string differently for those still inside
        if entry.recognition_out:
            time_inside_str = f"{int(hours)} hours, {int(minutes)} minutes, {int(seconds)} seconds"
        else:
            time_inside_str = f"{int(hours)} hours, {int(minutes)} minutes, {int(seconds)} seconds (Still inside)"

        entries_with_time.append({
            'entry': entry,
            'time_inside': time_inside_str,
            'entry_time': entry_time,
            'exit_time': entry.recognition_out.time if entry.recognition_out else None,
            'is_inside': entry.recognition_out is None
        })

    return render(request, 'entries.html', {
        'entries': entries_with_time,
        'username': username,
        'date_from': date_from,
        'date_to': date_to,
        'currently_inside': currently_inside,
        'time_filter_type': time_filter_type,
    })

@csrf_exempt
@require_http_methods(["POST"])
def recognize_entry_view(request):
    try:
        data = json.loads(request.body)
        recognition_id = data.get('recognition_id')
        user_id = data.get('user_id')
        
        if not all([recognition_id, user_id]):
            return JsonResponse({
                'error': 'recognition_id and user_id are required'
            }, status=400)
        
        entry = recognize_entry(recognition_id, user_id)
        
        return JsonResponse({
            'status': 'success',
            'entry_id': entry.id,
            'user_id': entry.user_id,
            'recognition_in_id': entry.recognition_in_id
        })
        
    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Internal server error {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def recognize_exit_view(request):
    try:
        data = json.loads(request.body)
        recognition_id = data.get('recognition_id')
        user_id = data.get('user_id')
        
        if not all([recognition_id, user_id]):
            return JsonResponse({
                'error': 'recognition_id and user_id are required'
            }, status=400)
        
        entry = recognize_exit(recognition_id, user_id)
        
        return JsonResponse({
            'status': 'success',
            'entry_id': entry.id,
            'user_id': entry.user_id,
            'recognition_in_id': entry.recognition_in_id,
            'recognition_out_id': entry.recognition_out_id
        })
        
    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Internal server error {str(e)}'}, status=500)
    
def detections_view(request):
    Entry = apps.get_model('stats', 'Entry')
    Detection = apps.get_model('stats', 'Detection')
    User = apps.get_model('auth', 'User')
    Camera = apps.get_model('management', 'Camera')

    # Get filter parameters
    date_from = request.GET.get('date_from')
    username = request.GET.get('username')
    camera_id = request.GET.get('camera')
    
    # Convert date_from to datetime or use today
    if date_from:
        date_from = datetime.strptime(date_from, '%Y-%m-%d')
    else:
        date_from = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    date_to = date_from + timedelta(days=1)
    
    # Base querysets
    detections = Detection.objects.filter(time__gte=date_from, time__lt=date_to)
    entries = Entry.objects.filter(
        Q(recognition_in__time__gte=date_from, recognition_in__time__lt=date_to) |
        Q(recognition_out__time__gte=date_from, recognition_out__time__lt=date_to)
    )
    
    # Apply filters if provided
    if username:
        user = User.objects.get(username=username)
        detections = detections.filter(user=user)
        entries = entries.filter(user=user)
    
    if camera_id:
        detections = detections.filter(camera_id=camera_id)
    
    # Calculate detection statistics
    total_detections = detections.count()
    
    # Only calculate unrecognized stats if no user filter
    unrecognized_percentage = None
    if not username:
        unrecognized_detections = detections.filter(user__isnull=True).count()
        unrecognized_percentage = (unrecognized_detections / total_detections * 100) if total_detections > 0 else 0
    
    # Only calculate user stats if no user filter
    avg_detections_per_user = None
    top_user = None
    bottom_user = None
    if not username:
        avg_detections_per_user = detections.exclude(user__isnull=True).values('user').annotate(
            count=Count('id')).aggregate(Avg('count'))['count__avg'] or 0
        top_user = detections.exclude(user__isnull=True).values('user__username').annotate(
            count=Count('id')).order_by('-count').first()
        bottom_user = detections.exclude(user__isnull=True).values('user__username').annotate(
            count=Count('id')).order_by('count').first()
    
    # Only calculate camera stats if no camera filter
    avg_detections_per_camera = None
    top_camera = None
    bottom_camera = None
    if not camera_id:
        avg_detections_per_camera = detections.values('camera').annotate(
            count=Count('id')).aggregate(Avg('count'))['count__avg'] or 0
        top_camera = detections.values('camera__name').annotate(
            count=Count('id')).order_by('-count').first()
        bottom_camera = detections.values('camera__name').annotate(
            count=Count('id')).order_by('count').first()
    
    # Detection time series (30-minute bins)
    detection_timeseries = detections.annotate(
        interval=Trunc('time', 'hour', output_field=DateTimeField())
    ).values('interval').annotate(count=Count('id')).order_by('interval')

    detection_timeseries = [
        {
            'interval': item['interval'].isoformat(),
            'count': item['count']
        }
        for item in detection_timeseries
    ]
    
    # Entry statistics
    total_entries = entries.count()
    avg_duration = entries.exclude(recognition_out__isnull=True).annotate(
        duration=ExpressionWrapper(
            F('recognition_out__time') - F('recognition_in__time'),
            output_field=DurationField()
        )
    ).aggregate(Avg('duration'))['duration__avg']
    
    # Format duration as hours and minutes
    if avg_duration:
        total_minutes = avg_duration.total_seconds() / 60
        avg_duration_hours = int(total_minutes // 60)
        avg_duration_minutes = int(total_minutes % 60)
        avg_duration_formatted = f"{avg_duration_hours}h {avg_duration_minutes}m"
    else:
        avg_duration_formatted = "0h 0m"

    def format_hour_float(hour_float):
        if hour_float is None:
            return None
            
        hours = int(hour_float)
        minutes = int((hour_float % 1) * 60)
    
        return f"{hours:02d}:{minutes:02d}"
    
    # Average first entry and last exit times
    avg_first_entry = entries.aggregate(
        avg_time=Avg('recognition_in__time__hour'))['avg_time']
    
    avg_last_exit = entries.exclude(recognition_out__isnull=True).aggregate(
        avg_time=Avg('recognition_out__time__hour'))['avg_time']
    
    formatted_first_entry = format_hour_float(avg_first_entry)
    formatted_last_exit = format_hour_float(avg_last_exit)
    
    # Entry/Exit time series
    entry_timeseries = entries.annotate(
        interval=Trunc('recognition_in__time', 'hour')
    ).values('interval').annotate(count=Count('id')).order_by('interval')

    entry_timeseries = [
        {
            'interval': item['interval'].isoformat(),
            'count': item['count']
        }
        for item in entry_timeseries
    ]
    
    exit_timeseries = entries.exclude(recognition_out__isnull=True).annotate(
        interval=Trunc('recognition_out__time', 'hour')
    ).values('interval').annotate(count=Count('id')).order_by('interval')

    exit_timeseries = [
        {
            'interval': item['interval'].isoformat(),
            'count': item['count']
        }
        for item in exit_timeseries
    ]
    
    # Get all cameras for dropdown
    cameras = Camera.objects.filter(enabled=True)
    
    context = {
        'date_from': date_from,
        'username': username,
        'camera_id': camera_id,
        'cameras': cameras,
        'total_detections': total_detections,
        'unrecognized_percentage': round(unrecognized_percentage, 2) if unrecognized_percentage is not None else None,
        'avg_detections_per_user': round(avg_detections_per_user, 2) if avg_detections_per_user is not None else None,
        'avg_detections_per_camera': round(avg_detections_per_camera, 2) if avg_detections_per_camera is not None else None,
        'top_user': top_user,
        'bottom_user': bottom_user,
        'top_camera': top_camera,
        'bottom_camera': bottom_camera,
        'detection_timeseries': json.dumps(list(detection_timeseries)),
        'total_entries': total_entries,
        'avg_duration': avg_duration_formatted,
        'avg_first_entry': formatted_first_entry if avg_first_entry else None,
        'avg_last_exit': formatted_last_exit if avg_last_exit else None,
        'entry_timeseries': json.dumps(list(entry_timeseries)),
        'exit_timeseries': json.dumps(list(exit_timeseries)),
    }
    
    return render(request, 'detections.html', context)

def camera_detections_view(request):
    Entry = apps.get_model('stats', 'Entry')
    Detection = apps.get_model('stats', 'Detection')
    Camera = apps.get_model('management', 'Camera')

    # Get filter parameters
    date_from = request.GET.get('date_from')
    camera_id = request.GET.get('camera')
    
    # Convert date_from to datetime or use today
    if date_from:
        date_from = datetime.strptime(date_from, '%Y-%m-%d')
    else:
        date_from = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    date_to = date_from + timedelta(days=1)
    
    # Get camera or 404
    if not camera_id:
        camera = Camera.objects.filter(enabled=True).first()
    else:
        camera = get_object_or_404(Camera, id=camera_id, enabled=True)
    
    # Get detections for the camera
    detections = Detection.objects.filter(
        camera=camera,
        time__gte=date_from,
        time__lt=date_to
    ).values('x', 'y', 'w', 'h', 'time')
    
    # Calculate foot positions (bottom center of bounding box)
    detection_points = [
        {
            'x': d['x'],
            'y': d['y'] + (d['h'] / 2),  # Bottom center
            'time': d['time'].isoformat()
        } for d in detections
    ]
    
    # Create heatmap data
    # We'll create a 48x27 grid (40px squares for 1920x1080)
    heatmap_data = [[0 for _ in range(48)] for _ in range(27)]
    
    for point in detection_points:
        # Convert coordinates to grid positions
        grid_x = min(47, max(0, int(point['x'] * 48 / 1920)))
        grid_y = min(26, max(0, int(point['y'] * 27 / 1080)))
        heatmap_data[grid_y][grid_x] += 1
    
    # Get all cameras for dropdown
    cameras = Camera.objects.filter(enabled=True)
    
    context = {
        'date_from': date_from,
        'camera': camera,
        'cameras': cameras,
        'detection_points': json.dumps(detection_points),
        'heatmap_data': json.dumps(heatmap_data),
        'total_detections': len(detection_points)
    }
    
    return render(request, 'camera_detections.html', context)