from django.shortcuts import render
from django.views.generic import FormView
from django import forms
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.apps import apps

from .utils import get_detection_statistics

Camera = apps.get_model('management', 'Camera')

class DetectionSearchForm(forms.Form):
    start_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        initial=datetime.now() - timedelta(hours=1)
    )
    end_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        initial=datetime.now()
    )
    camera_id = forms.ChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Get all enabled cameras
        cameras = Camera.objects.filter(enabled=True)
        camera_choices = [('', 'All Cameras')] + [(str(c.id), c.name) for c in cameras]
        self.fields['camera_id'].choices = camera_choices

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time and end_time <= start_time:
            raise forms.ValidationError("End time must be later than start time")
        
        camera_id = cleaned_data.get('camera_id')
        if camera_id == '':
            cleaned_data['camera_id'] = None
        elif camera_id:
            cleaned_data['camera_id'] = int(camera_id)
            
        return cleaned_data

class DetectionSearchView(FormView):
    template_name = 'detections/search.html'
    form_class = DetectionSearchForm
    
    def form_valid(self, form):
        start_time = form.cleaned_data['start_time']
        end_time = form.cleaned_data['end_time']
        camera_id = form.cleaned_data.get('camera_id')
        
        stats = get_detection_statistics(start_time, end_time, camera_id)
        user_objects = User.objects.filter(id__in=stats['detections_per_user'].values('user'))
        
        user_map = {user.id: user for user in user_objects}
        
        detections_per_user = []
        for detection in stats['detections_per_user']:
            user = user_map.get(detection['user'])
            if user:
                detections_per_user.append({
                    'user': user,
                    'count': detection['detection_count']
                })
        
        avg_distance_per_user = []
        for item in stats['avg_distance_per_user']:
            user = user_map.get(item['user'])
            if user:
                avg_distance_per_user.append({
                    'user': user,
                    'avg_distance': item['avg_distance']
                })
        
        context = {
            'form': form,
            'search_performed': True,
            'stats': stats,
            'detections_per_user': detections_per_user,
            'avg_distance_per_user': avg_distance_per_user
        }
        
        return render(self.request, self.template_name, context)
    
    def form_invalid(self, form):
        return render(self.request, self.template_name, {
            'form': form,
            'search_performed': False
        })
