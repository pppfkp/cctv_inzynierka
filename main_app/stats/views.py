import base64
from django.shortcuts import render
from django.views.generic import FormView
from django import forms
from datetime import datetime, timedelta
import cv2
from django.apps import apps
from django.utils import timezone
from django.apps import apps

from .utils import generate_heatmap, get_detection_statistics, plot_points, plot_bounding_boxes

class DetectionSearchForm(forms.Form):
    VISUALIZATION_CHOICES = [
        ('heatmap', 'Heatmap'),
        ('points', 'Points'),
        ('boxes', 'Bounding Boxes')
    ]

    start_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        initial=datetime.now() - timedelta(hours=1)
    )
    end_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        initial=datetime.now()
    )
    visualization_type = forms.ChoiceField(
        choices=VISUALIZATION_CHOICES,
        initial='heatmap',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time and end_time <= start_time:
            raise forms.ValidationError("End time must be later than start time")
            
        return cleaned_data

class DetectionSearchView(FormView):
    template_name = 'detections/search.html'
    form_class = DetectionSearchForm
    
    def form_valid(self, form):
        try:
            start_time = form.cleaned_data['start_time']
            end_time = form.cleaned_data['end_time']
            visualization_type = form.cleaned_data.get('visualization_type')
            
            print(f"Processing request: start={start_time}, end={end_time}, viz={visualization_type}")
            
            # Get statistics
            stats = get_detection_statistics(start_time, end_time)
            print(f"Statistics retrieved: {stats}")
            
            # Generate visualizations based on selected type
            print(f"Generating {visualization_type} visualization...")
            
            if visualization_type == 'heatmap':
                raw_viz = generate_heatmap(
                    start_time=start_time,
                    end_time=end_time,
                    img_width=1920,
                    img_height=1080
                )
            elif visualization_type == 'points':
                raw_viz = plot_points(
                    start_time=start_time,
                    end_time=end_time
                )
            else:  # boxes
                raw_viz = plot_bounding_boxes(
                    start_time=start_time,
                    end_time=end_time,
                    opacity=0.6
                )
            
            print(f"Visualization generated for cameras: {list(raw_viz.keys())}")
            
            # Convert visualizations to base64
            viz_data = {}
            for cam_id, viz_img in raw_viz.items():
                success, buffer = cv2.imencode('.png', viz_img)
                if success:
                    img_base64 = base64.b64encode(buffer).decode('utf-8')
                    viz_data[cam_id] = img_base64
                    print(f"Successfully encoded visualization for camera {cam_id}")
                else:
                    print(f"Failed to encode visualization for camera {cam_id}")
        
            print("Visualization Data keys:", viz_data.keys())
        
            return render(self.request, self.template_name, {
                'form': form,
                'search_performed': True,
                'stats': stats,
                'heatmap_data': viz_data,  # Keep the same template variable name for compatibility
                'visualization_type': visualization_type
            })
            
        except Exception as e:
            print(f"Error in form_valid: {str(e)}")
            form.add_error(None, f"Error processing request: {str(e)}")
            return self.form_invalid(form)
        

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