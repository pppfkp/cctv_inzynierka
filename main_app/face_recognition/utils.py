# utils.py
from PIL import Image
import numpy as np
from .model_loader import get_models, _device

def extract_embedding(photo, confidence_threshold=0.95):
    try:
        # Get models on the specified device
        mtcnn, resnet = get_models()
        
        # Check if the input is already a PIL image
        if not isinstance(photo, Image.Image):
            # Open the image and ensure it's in RGB format
            photo = Image.open(photo).convert('RGB')
        
        # Get both boxes and probabilities from MTCNN
        boxes, probs = mtcnn.detect(photo)
        
        # Check if any faces were detected
        if boxes is None or len(boxes) == 0:
            print("No faces detected in the image")
            return None
        
        # Check if the highest confidence face meets our threshold
        max_prob = max(probs)
        if max_prob < confidence_threshold:
            print(f"Face detected but confidence ({max_prob:.2f}) is below threshold ({confidence_threshold})")
            return None
            
        # Extract the face with highest confidence
        cropped_face = mtcnn(photo)
        if cropped_face is None:
            print("Error cropping face")
            return None
        
        # Ensure cropped_face is on the same device as the resnet model
        cropped_face = cropped_face.to(_device)
        
        # Pass through the face recognition model
        embedding = resnet(cropped_face.unsqueeze(0).to(_device)).detach().cpu()[0]
        
        return embedding 
        
    except Exception as e:
        print(f"Error extracting embedding: {e}")
        return None
    

