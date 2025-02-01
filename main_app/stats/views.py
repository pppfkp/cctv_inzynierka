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