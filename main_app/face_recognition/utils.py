# utils.py
from PIL import Image
import numpy as np
from .model_loader import get_models, _device
from management.utils import get_settings

def extract_embedding(photo):
    try:
        setting_dict = get_settings()
        confidence_threshold = float(setting_dict.get("extractEmbeddingTreshold", 0.95))
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
            return None, None
        
        # Check if the highest confidence face meets our threshold
        max_prob = max(probs)
        if max_prob < confidence_threshold:
            print(f"Face detected but confidence ({max_prob:.2f}) is below threshold ({confidence_threshold})")
            return None, None
            
        # Extract the face with highest confidence
        cropped_face = mtcnn(photo)
        if cropped_face is None:
            print("Error cropping face")
            return None, None
        
        # Ensure cropped_face is on the same device as the resnet model
        cropped_face = cropped_face.to(_device)
        
        # Pass through the face recognition model
        embedding = resnet(cropped_face.unsqueeze(0).to(_device)).detach().cpu()[0]
        
        # Ensure the embedding is a 1D array
        if embedding.ndim != 1:
            print(f"Embedding has unexpected shape: {embedding.shape}")
            return None, None
        
        return embedding, cropped_face  # Return both the embedding and cropped face
        
    except Exception as e:
        print(f"Error extracting embedding: {e}")
        return None, None
    

