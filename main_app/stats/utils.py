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

logger = logging.getLogger(__name__)



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
    
    # Detections per user - include user details and format as list of dicts
    detections_per_user = list(base_query.values('user', 'user__username')
        .annotate(detection_count=Count('id'))
        .exclude(user__isnull=True)
        .order_by('-detection_count')
        .values('user', 'user__username', 'detection_count'))
    
    # Base query for recognitions within the time range
    recognition_query = Recognition.objects.filter(
        time__range=(start_time, end_time)
    )
    if camera_id is not None:
        recognition_query = recognition_query.filter(detection__camera_id=camera_id)
    
    # Recognition statistics
    avg_distance_all = recognition_query.aggregate(Avg('distance'))['distance__avg'] or 0
    total_recognitions = recognition_query.count()
    
    # Average recognition distance per user - format as list of dicts
    avg_distance_per_user = list(recognition_query.values('user', 'user__username')
        .annotate(avg_distance=Round(Avg('distance'), 2))
        .exclude(user__isnull=True)
        .order_by('avg_distance')
        .values('user', 'user__username', 'avg_distance'))

    return {
        'total_detections': total_detections,
        'unrecognized_detections': unrecognized_detections,
        'recognized_detections': recognized_detections,
        'detections_per_user': detections_per_user,
        'total_recognitions': total_recognitions,
        'avg_distance_all': round(avg_distance_all, 2) if avg_distance_all else 0,
        'avg_distance_per_user': avg_distance_per_user
    }

def get_distinct_users_in_timeframe(
    start_time: datetime,
    end_time: datetime
) -> list[int]:
    """
    Retrieve distinct user IDs for detections within a specified time range.
    Returns a list of user IDs, excluding None values.
    """
    if is_naive(start_time):
        start_time = make_aware(start_time)
    if is_naive(end_time):
        end_time = make_aware(end_time)
    
    query = Detection.objects.filter(time__range=(start_time, end_time))
    user_ids = query.values_list('user_id', flat=True).distinct()
    return list(filter(None, user_ids))

def fetch_camera_photo(camera, width, height):
    """
    Fetch and resize the camera photo for overlay.
    Returns None if the photo cannot be loaded.
    """
    try:
        if not camera.photo:
            logger.warning(f"No photo found for camera {camera.id}")
            return None
            
        with default_storage.open(f"{camera.photo}", 'rb') as f:
            image_data = f.read()
            image = Image.open(io.BytesIO(image_data))
            image = image.convert('RGB')  # Ensure RGB format
            image = image.resize((width, height), Image.Resampling.LANCZOS)
            opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            logger.info(f"Successfully loaded photo for camera {camera.id}")
            return opencv_image
    except Exception as e:
        logger.error(f"Error loading camera photo for camera {camera.id}: {e}")
        return None

import numpy as np
import cv2
from datetime import datetime
from collections import defaultdict

def generate_heatmap(
    start_time: datetime,
    end_time: datetime,
    camera_id: Optional[int] = None,
    img_width: int = 1920,
    img_height: int = 1080,
    heatmap_radius: int = 30,
    gaussian_sigma: int = 10,
    opacity: float = 0.7,
    colormap: str = 'jet',
    min_intensity: float = 0.1,
    max_intensity: float = 0.95
) -> Dict[int, np.ndarray]:
    """
    Generate an enhanced heatmap visualization with Gaussian smoothing and customizable colormaps.

    Args:
        start_time: Start of time range to plot
        end_time: End of time range to plot
        camera_id: Optional specific camera ID to plot
        img_width: Width of output image
        img_height: Height of output image
        heatmap_radius: Radius around each point where heat will accumulate
        gaussian_sigma: Standard deviation for Gaussian smoothing
        opacity: Opacity of heatmap overlay (0.0 to 1.0)
        colormap: Matplotlib colormap name ('jet', 'hot', 'viridis', etc.)
        min_intensity: Minimum intensity threshold for visualization (0.0 to 1.0)
        max_intensity: Maximum intensity threshold for visualization (0.0 to 1.0)
    
    Returns:
        dict: Camera ID to heatmap image mapping
    """
    logger.info(f"Starting enhanced heatmap generation for period {start_time} to {end_time}")

    # Query detections within the specified time range
    detections_query = Detection.objects.filter(
        time__range=(start_time, end_time)
    )

    if camera_id is not None:
        detections_query = detections_query.filter(camera_id=camera_id)
        cameras = Camera.objects.filter(id=camera_id, enabled=True)
    else:
        camera_ids = detections_query.values_list('camera_id', flat=True).distinct()
        cameras = Camera.objects.filter(id__in=camera_ids, enabled=True)

    if not cameras.exists():
        logger.warning("No enabled cameras found for the specified criteria")
        return {}

    heatmap_plots = {}

    for camera in cameras:
        logger.info(f"Processing camera {camera.id}")
        cam_detections = detections_query.filter(camera_id=camera.id)
        detection_count = cam_detections.count()

        if not detection_count:
            continue

        # Create accumulator arrays for the heatmap
        heatmap = np.zeros((img_height, img_width), dtype=np.float32)
        
        # Process detections with kernel-based accumulation
        kernel = create_gaussian_kernel(heatmap_radius, gaussian_sigma)
        
        for detection in cam_detections:
            try:
                x, y, w, h = map(int, detection.xywh)
                add_detection_to_heatmap(
                    heatmap, x + w//2, y + h//2, 
                    kernel, heatmap_radius, 
                    img_width, img_height
                )
            except (AttributeError, ValueError) as e:
                logger.error(f"Error processing detection {detection.id}: {e}")
                continue

        if np.sum(heatmap) > 0:
            overlay = create_heatmap_overlay(
                heatmap,
                camera,
                img_width,
                img_height,
                gaussian_sigma,
                opacity,
                colormap,
                min_intensity,
                max_intensity
            )
            
            heatmap_plots[camera.id] = overlay
            logger.info(f"Successfully generated enhanced heatmap for camera {camera.id}")
        else:
            logger.warning(f"No valid points to generate heatmap for camera {camera.id}")

    return heatmap_plots

def create_gaussian_kernel(radius: int, sigma: float) -> np.ndarray:
    """Create a Gaussian kernel for heat distribution."""
    y, x = np.ogrid[-radius:radius + 1, -radius:radius + 1]
    mask = x*x + y*y <= radius*radius
    kernel = np.zeros((2*radius+1, 2*radius+1))
    kernel[mask] = np.exp(-(x*x + y*y)[mask]/(2*sigma**2))
    return kernel / kernel.max()

def add_detection_to_heatmap(
    heatmap: np.ndarray,
    center_x: int,
    center_y: int,
    kernel: np.ndarray,
    radius: int,
    img_width: int,
    img_height: int
) -> None:
    """Add a single detection to the heatmap using the precomputed kernel."""
    y_min = max(0, center_y - radius)
    y_max = min(img_height, center_y + radius + 1)
    x_min = max(0, center_x - radius)
    x_max = min(img_width, center_x + radius + 1)
    
    kernel_y_min = radius - (center_y - y_min)
    kernel_y_max = radius + (y_max - center_y)
    kernel_x_min = radius - (center_x - x_min)
    kernel_x_max = radius + (x_max - center_x)
    
    heatmap[y_min:y_max, x_min:x_max] += kernel[
        kernel_y_min:kernel_y_max,
        kernel_x_min:kernel_x_max
    ]

def create_heatmap_overlay(
    heatmap: np.ndarray,
    camera,
    img_width: int,
    img_height: int,
    gaussian_sigma: float,
    opacity: float,
    colormap: str,
    min_intensity: float,
    max_intensity: float
) -> np.ndarray:
    """Create the final heatmap overlay with background blending."""
    # Apply additional Gaussian smoothing
    heatmap = cv2.GaussianBlur(heatmap, (0, 0), gaussian_sigma)
    
    # Normalize and clip heatmap values
    heatmap = cv2.normalize(heatmap, None, 0, 1, cv2.NORM_MINMAX)
    heatmap = np.clip((heatmap - min_intensity) / (max_intensity - min_intensity), 0, 1)
    
    # Convert to colormap using matplotlib
    cmap = plt.get_cmap(colormap)
    heatmap_colored = (cmap(heatmap) * 255).astype(np.uint8)
    
    # Get and prepare background
    background = fetch_camera_photo(camera, img_width, img_height)
    if background is None:
        background = np.ones((img_height, img_width, 3), dtype=np.uint8) * 255
    
    if len(background.shape) == 2:
        background = cv2.cvtColor(background, cv2.COLOR_GRAY2BGR)
    
    # Convert heatmap to BGR for OpenCV
    heatmap_colored_bgr = cv2.cvtColor(heatmap_colored, cv2.COLOR_RGBA2BGR)
    
    # Create smooth alpha mask for blending
    alpha = heatmap.copy()
    alpha = cv2.GaussianBlur(alpha, (0, 0), gaussian_sigma / 2)
    alpha = np.clip(alpha * opacity, 0, 1)
    alpha = np.dstack([alpha] * 3)
    
    # Perform alpha blending
    overlay = background * (1 - alpha) + heatmap_colored_bgr * alpha
    return np.clip(overlay, 0, 255).astype(np.uint8)

def plot_points(
    start_time: datetime,
    end_time: datetime,
    camera_id: int = None,
    img_width: int = 1920,
    img_height: int = 1080,
    point_color: tuple = (0, 0, 255),  # Red color for the point
    point_radius: int = 5  # Radius of the point to be drawn
) -> dict:
    """
    Generate visualizations with only points at the top center of each bounding box.

    Args:
        start_time: Start of time range to plot
        end_time: End of time range to plot
        camera_id: Optional specific camera ID to plot
        img_width: Width of output image
        img_height: Height of output image
        point_color: BGR color tuple for points
        point_radius: Radius of the point
    Returns:
        dict: Camera ID to overlay image mapping
    """
    logger.info(f"Starting point plotting for period {start_time} to {end_time}")
    logger.info(f"Parameters: camera_id={camera_id}, width={img_width}, height={img_height}")

    # Query detections within the specified time range
    detections_query = Detection.objects.filter(
        time__range=(start_time, end_time)
    )

    if camera_id is not None:
        detections_query = detections_query.filter(camera_id=camera_id)
        cameras = Camera.objects.filter(id=camera_id, enabled=True)
        logger.info(f"Filtered to camera {camera_id}: {detections_query.count()} detections")
    else:
        camera_ids = detections_query.values_list('camera_id', flat=True).distinct()
        cameras = Camera.objects.filter(id__in=camera_ids, enabled=True)
        logger.info(f"Processing {cameras.count()} cameras: {list(cameras.values_list('id', flat=True))}")

    if not cameras.exists():
        logger.warning("No enabled cameras found for the specified criteria")
        return {}

    point_plots = {}

    for camera in cameras:
        logger.info(f"Processing camera {camera.id}")

        # Get detections for this camera
        cam_detections = detections_query.filter(camera_id=camera.id)
        detection_count = cam_detections.count()

        logger.info(f"Camera {camera.id} has {detection_count} detections")

        if not detection_count:
            continue

        # Create blank overlay for points
        point_overlay = np.zeros((img_height, img_width, 3), dtype=np.uint8)
        valid_points = 0

        for detection in cam_detections:
            try:
                x, y, w, h = map(int, detection.xywh)

                # Calculate top-center of the bounding box
                top_center = (x, img_height - (y + h // 2))

                # Draw point at the top center
                cv2.circle(point_overlay, top_center, point_radius, point_color, -1)

                valid_points += 1
            except (AttributeError, ValueError) as e:
                logger.error(f"Error processing detection {detection.id}: {e}")
                continue

        logger.info(f"Camera {camera.id}: Plotted {valid_points} points out of {detection_count} detections")

        if valid_points > 0:
            # Get or create background image
            background = fetch_camera_photo(camera, img_width, img_height)
            if background is None:
                logger.warning(f"Using blank background for camera {camera.id}")
                background = np.ones((img_height, img_width, 3), dtype=np.uint8) * 255

            point_overlay = cv2.flip(point_overlay, 0)

            # Create overlay
            overlay = cv2.addWeighted(
                background,
                1,  # Use full opacity for the background
                point_overlay,
                0.6,  # Apply partial opacity to the points
                0
            )

            point_plots[camera.id] = overlay
            logger.info(f"Successfully generated point plot for camera {camera.id}")
        else:
            logger.warning(f"No valid points to generate plot for camera {camera.id}")

    logger.info(f"Completed point plotting. Generated {len(point_plots)} plots")
    return point_plots

def plot_bounding_boxes(
    start_time: datetime,
    end_time: datetime,
    camera_id: int = None,
    img_width: int = 1920,
    img_height: int = 1080,
    box_color: tuple = (0, 255, 0),  # Green color in BGR
    thickness: int = 2,
    opacity: float = 0.6,
    point_color: tuple = (0, 0, 255),  # Red color for the point
    point_radius: int = 5  # Radius of the point to be drawn
) -> dict:
    """
    Generate bounding box visualizations for detected objects and plot points at the top center of each bounding box.

    Args:
        start_time: Start of time range to plot
        end_time: End of time range to plot
        camera_id: Optional specific camera ID to plot
        img_width: Width of output image
        img_height: Height of output image
        box_color: BGR color tuple for bounding boxes
        thickness: Thickness of bounding box lines
        opacity: Opacity of overlay
        point_color: BGR color tuple for points
        point_radius: Radius of the point
    Returns:
        dict: Camera ID to overlay image mapping
    """
    logger.info(f"Starting bounding box plotting for period {start_time} to {end_time}")
    logger.info(f"Parameters: camera_id={camera_id}, width={img_width}, height={img_height}")

    # Query detections within the specified time range
    detections_query = Detection.objects.filter(
        time__range=(start_time, end_time)
    )

    if camera_id is not None:
        detections_query = detections_query.filter(camera_id=camera_id)
        cameras = Camera.objects.filter(id=camera_id, enabled=True)
        logger.info(f"Filtered to camera {camera_id}: {detections_query.count()} detections")
    else:
        camera_ids = detections_query.values_list('camera_id', flat=True).distinct()
        cameras = Camera.objects.filter(id__in=camera_ids, enabled=True)
        logger.info(f"Processing {cameras.count()} cameras: {list(cameras.values_list('id', flat=True))}")

    if not cameras.exists():
        logger.warning("No enabled cameras found for the specified criteria")
        return {}

    box_plots = {}

    for camera in cameras:
        logger.info(f"Processing camera {camera.id}")

        # Get detections for this camera
        cam_detections = detections_query.filter(camera_id=camera.id)
        detection_count = cam_detections.count()

        logger.info(f"Camera {camera.id} has {detection_count} detections")

        if not detection_count:
            continue

        # Create blank overlay for bounding boxes
        box_overlay = np.zeros((img_height, img_width, 3), dtype=np.uint8)
        valid_boxes = 0

        for detection in cam_detections:
            try:
                x, y, w, h = map(int, detection.xywh)
                top_left = (x - w // 2, img_height - (y + h // 2))
                bottom_right = (x + w // 2, img_height - (y - h // 2))

                if 0 <= top_left[0] < img_width and 0 <= top_left[1] < img_height:
                    # Draw bounding box
                    cv2.rectangle(
                        box_overlay,
                        top_left,
                        bottom_right,
                        box_color,
                        thickness
                    )

                    # Calculate top-center of the bounding box
                    top_center = (x, img_height - (y + h // 2))

                    # Draw point at the top center
                    cv2.circle(box_overlay, top_center, point_radius, point_color, -1)

                    valid_boxes += 1
                else:
                    logger.warning(f"Box outside bounds for detection {detection.id}: {top_left}, {bottom_right}")
            except (AttributeError, ValueError) as e:
                logger.error(f"Error processing detection {detection.id}: {e}")
                continue

        logger.info(f"Camera {camera.id}: Plotted {valid_boxes} valid boxes out of {detection_count} detections")

        if valid_boxes > 0:
            # Get or create background image
            background = fetch_camera_photo(camera, img_width, img_height)
            if background is None:
                logger.warning(f"Using blank background for camera {camera.id}")
                background = np.ones((img_height, img_width, 3), dtype=np.uint8) * 255

            box_overlay = cv2.flip(box_overlay, 0)

            # Create overlay
            overlay = cv2.addWeighted(
                background,
                1 - opacity,
                box_overlay,
                opacity,
                0
            )

            box_plots[camera.id] = overlay
            logger.info(f"Successfully generated bounding box plot for camera {camera.id}")
        else:
            logger.warning(f"No valid boxes to generate plot for camera {camera.id}")

    logger.info(f"Completed bounding box plotting. Generated {len(box_plots)} plots")
    return box_plots

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