# utils.py
from PIL import Image
import numpy as np
from .model_loader import get_models, _device

def extract_embedding(photo):
    try:
        # Get models on the specified device
        mtcnn, resnet = get_models()
        
        # Open the image and ensure it's in RGB format
        image = Image.open(photo).convert('RGB')
        
        # Perform face detection and move the detected face tensor to the correct device
        cropped_face = mtcnn(image)
        if cropped_face is None:
            print("No face detected")
            return None
        
        # Ensure cropped_face is on the same device as the resnet model
        cropped_face = cropped_face.to(_device)
        
        # Pass through the face recognition model
        embedding = resnet(cropped_face.unsqueeze(0).to(_device)).detach().cpu()[0]
        
        return embedding
    except Exception as e:
        print(f"Error extracting embedding: {e}")
        return None