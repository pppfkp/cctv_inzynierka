# stats/views.py
import base64
from django.shortcuts import render
from django.views.generic import FormView
from django import forms
from datetime import datetime, timedelta
from django.apps import apps
import cv2

from .utils import generate_heatmap, get_detection_statistics, plot_points, plot_bounding_boxes

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
        try:
            start_time = form.cleaned_data['start_time']
            end_time = form.cleaned_data['end_time']
            camera_id = form.cleaned_data.get('camera_id')
            
            print(f"Processing request: start={start_time}, end={end_time}, camera={camera_id}")
            
            # Get statistics
            stats = get_detection_statistics(start_time, end_time, camera_id)
            print(f"Statistics retrieved: {stats}")
            
            # Generate heatmaps and convert them to base64
            heatmap_data = {}
            print("Generating heatmaps...")

            raw_heatmaps = generate_heatmap(
                start_time,
                end_time,
                camera_id,
                img_width=1920,
                img_height=1080
            )

            raw_heatmaps = plot_points(
                start_time=start_time,
                end_time=end_time,
                camera_id=camera_id
            )

            
            # raw_heatmaps = plot_bounding_boxes(
            #     start_time=start_time,
            #     end_time=end_time,
            #     camera_id=camera_id,
            #     opacity=0.6
            # )
            
            print(f"Raw heatmaps generated for cameras: {list(raw_heatmaps.keys())}")
            
            for cam_id, heatmap_img in raw_heatmaps.items():
                success, buffer = cv2.imencode('.png', heatmap_img)
                if success:
                    img_base64 = base64.b64encode(buffer).decode('utf-8')
                    heatmap_data[cam_id] = img_base64
                    print(f"Successfully encoded heatmap for camera {cam_id}")
                else:
                    print(f"Failed to encode heatmap for camera {cam_id}")
        
            print("Heatmap Data keys:", heatmap_data.keys())
        
            return render(self.request, self.template_name, {
                'form': form,
                'search_performed': True,
                'stats': stats,
                'heatmap_data': heatmap_data,
            })
            
        except Exception as e:
            print(f"Error in form_valid: {str(e)}")
            form.add_error(None, f"Error processing request: {str(e)}")
            return self.form_invalid(form)