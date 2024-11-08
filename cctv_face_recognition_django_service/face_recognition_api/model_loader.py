# model_loader.py
import torch
from facenet_pytorch import MTCNN, InceptionResnetV1

# Global variables to hold model instances
_mtcnn = None
_resnet = None
_device = None

def get_models():
    global _mtcnn, _resnet, _device
    _device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    if _mtcnn is None or _resnet is None:
        _mtcnn = MTCNN(device=_device).to(_device)
        _resnet = InceptionResnetV1(pretrained='vggface2', device=_device).eval().to(_device)
    return _mtcnn, _resnet
