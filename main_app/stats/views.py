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
from django.db.models.functions import ExtractWeekDay, ExtractDay

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
    
@staff_member_required(login_url='admin:login')    
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

@staff_member_required(login_url='admin:login')    
def camera_detections_view(request):
    Entry = apps.get_model('stats', 'Entry')
    Detection = apps.get_model('stats', 'Detection')
    Camera = apps.get_model('management', 'Camera')
    User = apps.get_model('auth', 'User')

    # Get filter parameters
    date_from = request.GET.get('date_from')
    time_from = request.GET.get('time_from', '00:00')
    date_to = request.GET.get('date_to')
    time_to = request.GET.get('time_to', '23:59')
    camera_id = request.GET.get('camera')
    user_filter = request.GET.get('user', '').strip()
    
    # Convert date_from and date_to to datetime or use today
    now = timezone.now()
    if date_from and time_from:
        try:
            datetime_from = timezone.make_aware(
                datetime.strptime(f"{date_from} {time_from}", '%Y-%m-%d %H:%M')
            )
        except ValueError:
            datetime_from = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        datetime_from = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if date_to and time_to:
        try:
            datetime_to = timezone.make_aware(
                datetime.strptime(f"{date_to} {time_to}", '%Y-%m-%d %H:%M')
            )
        except ValueError:
            datetime_to = datetime_from + timedelta(days=1)
    else:
        datetime_to = datetime_from + timedelta(days=1)
    
    # Get camera or 404
    if not camera_id:
        camera = Camera.objects.filter(enabled=True).first()
    else:
        camera = get_object_or_404(Camera, id=camera_id, enabled=True)
    
    # Build detection query
    detections = Detection.objects.filter(
        camera=camera,
        time__gte=datetime_from,
        time__lt=datetime_to
    )

    # Apply user filter
    if user_filter.lower() == 'none':
        detections = detections.filter(user__isnull=True)
    elif user_filter:
        detections = detections.filter(user__username__iexact=user_filter)
    
    # Get values for processing
    detections = detections.values('x', 'y', 'w', 'h', 'time')
    
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
        'date_from': datetime_from,
        'time_from': datetime_from.strftime('%H:%M'),
        'date_to': datetime_to,
        'time_to': datetime_to.strftime('%H:%M'),
        'camera': camera,
        'cameras': cameras,
        'user_filter': user_filter,
        'detection_points': json.dumps(detection_points),
        'heatmap_data': json.dumps(heatmap_data),
        'total_detections': len(detection_points)
    }
    
    return render(request, 'camera_detections.html', context)

@staff_member_required(login_url='admin:login')    
def detections_weekly_view(request):
    Entry = apps.get_model('stats', 'Entry')
    Detection = apps.get_model('stats', 'Detection')
    User = apps.get_model('auth', 'User')
    Camera = apps.get_model('management', 'Camera')

    # Get filter parameters
    week_start = request.GET.get('week_start')
    username = request.GET.get('username') or ''  # Default to empty string instead of None
    camera_id = request.GET.get('camera')
    
    # Convert week_start to datetime or use current week's Monday
    if week_start:
        week_start = datetime.strptime(week_start, '%Y-%m-%d')
    else:
        today = timezone.now()
        week_start = today - timedelta(days=today.weekday())
    
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)
    
    # Base querysets with distinct to avoid duplicates
    detections = Detection.objects.filter(time__gte=week_start, time__lt=week_end)
    entries = Entry.objects.filter(
        recognition_in__time__gte=week_start,
        recognition_in__time__lt=week_end
    ).distinct()  # Add distinct to avoid duplicates
    
    # Apply filters if provided
    if username.strip():  # Only filter if username is not empty
        user = User.objects.get(username=username)
        detections = detections.filter(user=user)
        entries = entries.filter(user=user)
    
    if camera_id:
        detections = detections.filter(camera_id=camera_id)
    
    # Rest of the view remains the same until the context...
    
    # Calculate detection statistics
    total_detections = detections.count()
    
    # Only calculate unrecognized stats if no user filter
    unrecognized_percentage = None
    if not username.strip():
        unrecognized_detections = detections.filter(user__isnull=True).count()
        unrecognized_percentage = (unrecognized_detections / total_detections * 100) if total_detections > 0 else 0
    
    # Only calculate user stats if no user filter
    avg_detections_per_user = None
    top_user = None
    bottom_user = None
    if not username.strip():
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
    
    # Detection time series (by weekday)
    detection_timeseries = detections.annotate(
        weekday=ExtractWeekDay('time')
    ).values('weekday').annotate(count=Count('id')).order_by('weekday')

    # Convert to list of weekday names and ensure all days are present
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    detection_counts = {item['weekday']: item['count'] for item in detection_timeseries}
    detection_timeseries = [
        {
            'weekday': weekdays[i],
            'count': detection_counts.get(i + 1, 0)  # Adding 1 because ExtractWeekDay returns 1-7
        }
        for i in range(7)
    ]
    
    # Entry statistics with distinct count
    total_entries = entries.count()  # This will now count distinct entries
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
    
    # Entry/Exit time series by weekday (with distinct)
    entry_timeseries = entries.annotate(
        weekday=ExtractWeekDay('recognition_in__time')
    ).values('weekday').annotate(count=Count('id', distinct=True)).order_by('weekday')

    entry_counts = {item['weekday']: item['count'] for item in entry_timeseries}
    entry_timeseries = [
        {
            'weekday': weekdays[i],
            'count': entry_counts.get(i + 1, 0)
        }
        for i in range(7)
    ]
    
    exit_timeseries = entries.exclude(recognition_out__isnull=True).annotate(
        weekday=ExtractWeekDay('recognition_out__time')
    ).values('weekday').annotate(count=Count('id', distinct=True)).order_by('weekday')

    exit_counts = {item['weekday']: item['count'] for item in exit_timeseries}
    exit_timeseries = [
        {
            'weekday': weekdays[i],
            'count': exit_counts.get(i + 1, 0)
        }
        for i in range(7)
    ]
    
    # Get busiest day stats
    busiest_day_detections = max(detection_timeseries, key=lambda x: x['count'])
    quietest_day_detections = min(detection_timeseries, key=lambda x: x['count'])
    
    # Get all cameras for dropdown
    cameras = Camera.objects.filter(enabled=True)
    
    context = {
        'week_start': week_start,
        'username': username,  # Will now be empty string instead of None
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
        'detection_timeseries': json.dumps(detection_timeseries),
        'total_entries': total_entries,
        'avg_duration': avg_duration_formatted,
        'entry_timeseries': json.dumps(entry_timeseries),
        'exit_timeseries': json.dumps(exit_timeseries),
        'busiest_day_detections': busiest_day_detections,
        'quietest_day_detections': quietest_day_detections,
    }
    
    return render(request, 'detections_weekly.html', context)

@staff_member_required(login_url='admin:login')    
def detections_monthly_view(request):
    Entry = apps.get_model('stats', 'Entry')
    Detection = apps.get_model('stats', 'Detection')
    User = apps.get_model('auth', 'User')
    Camera = apps.get_model('management', 'Camera')

    # Get filter parameters
    month_start = request.GET.get('month_start')
    username = request.GET.get('username') or ''
    camera_id = request.GET.get('camera')
    
    # Convert month_start to datetime or use current month's first day
    if month_start:
        month_start = datetime.strptime(month_start, '%Y-%m')
    else:
        today = timezone.now()
        month_start = today.replace(day=1)
    
    month_start = month_start.replace(hour=0, minute=0, second=0, microsecond=0)
    if month_start.month == 12:
        month_end = month_start.replace(year=month_start.year + 1, month=1)
    else:
        month_end = month_start.replace(month=month_start.month + 1)
    
    # Base querysets with distinct to avoid duplicates
    detections = Detection.objects.filter(time__gte=month_start, time__lt=month_end)
    entries = Entry.objects.filter(
        recognition_in__time__gte=month_start,
        recognition_in__time__lt=month_end
    ).distinct()
    
    # Apply filters if provided
    if username.strip():
        user = User.objects.get(username=username)
        detections = detections.filter(user=user)
        entries = entries.filter(user=user)
    
    if camera_id:
        detections = detections.filter(camera_id=camera_id)
    
    # Calculate detection statistics
    total_detections = detections.count()
    
    # Only calculate unrecognized stats if no user filter
    unrecognized_percentage = None
    if not username.strip():
        unrecognized_detections = detections.filter(user__isnull=True).count()
        unrecognized_percentage = (unrecognized_detections / total_detections * 100) if total_detections > 0 else 0
    
    # Only calculate user stats if no user filter
    avg_detections_per_user = None
    top_user = None
    bottom_user = None
    if not username.strip():
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
    
    # Detection time series (by day of month)
    detection_timeseries = detections.annotate(
        day=ExtractDay('time')
    ).values('day').annotate(count=Count('id')).order_by('day')

    # Ensure all days of the month are present
    days_in_month = (month_end - month_start).days
    detection_counts = {item['day']: item['count'] for item in detection_timeseries}
    detection_timeseries = [
        {
            'day': i + 1,
            'count': detection_counts.get(i + 1, 0)
        }
        for i in range(days_in_month)
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
    
    # Entry/Exit time series by day
    entry_timeseries = entries.annotate(
        day=ExtractDay('recognition_in__time')
    ).values('day').annotate(count=Count('id', distinct=True)).order_by('day')

    entry_counts = {item['day']: item['count'] for item in entry_timeseries}
    entry_timeseries = [
        {
            'day': i + 1,
            'count': entry_counts.get(i + 1, 0)
        }
        for i in range(days_in_month)
    ]
    
    exit_timeseries = entries.exclude(recognition_out__isnull=True).annotate(
        day=ExtractDay('recognition_out__time')
    ).values('day').annotate(count=Count('id', distinct=True)).order_by('day')

    exit_counts = {item['day']: item['count'] for item in exit_timeseries}
    exit_timeseries = [
        {
            'day': i + 1,
            'count': exit_counts.get(i + 1, 0)
        }
        for i in range(days_in_month)
    ]
    
    # Get busiest day stats
    busiest_day_detections = max(detection_timeseries, key=lambda x: x['count'])
    quietest_day_detections = min(detection_timeseries, key=lambda x: x['count'])
    
    # Get all cameras for dropdown
    cameras = Camera.objects.filter(enabled=True)
    
    context = {
        'month_start': month_start,
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
        'detection_timeseries': json.dumps(detection_timeseries),
        'total_entries': total_entries,
        'avg_duration': avg_duration_formatted,
        'entry_timeseries': json.dumps(entry_timeseries),
        'exit_timeseries': json.dumps(exit_timeseries),
        'busiest_day_detections': busiest_day_detections,
        'quietest_day_detections': quietest_day_detections,
        'days_in_month': days_in_month,
    }
    
    return render(request, 'detections_monthly.html', context)

