import torch
from torch import nn
from torchvision import models, transforms

IMAGE_SIZE = 224
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]


def build_model(num_classes):
    model = models.mobilenet_v2(weights=None)
    model.classifier[1] = nn.Linear(model.last_channel, num_classes)
    return model


def load_classifier(checkpoint_path):
    checkpoint = torch.load(
        checkpoint_path, map_location="cpu", weights_only=False
    )
    class_names = checkpoint["class_names"]
    model = build_model(len(class_names))
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    # Must match the deterministic evaluation preprocessing in train.py.
    preprocess = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(IMAGE_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    return {
        "model": model,
        "class_names": class_names,
        "preprocess": preprocess,
    }


@torch.inference_mode()
def predict_image(bundle, image):
    tensor = bundle["preprocess"](image.convert("RGB")).unsqueeze(0)
    logits = bundle["model"](tensor)
    probs = torch.softmax(logits, dim=1)[0]
    values = {
        name: float(probs[i])
        for i, name in enumerate(bundle["class_names"])
    }
    index = int(torch.argmax(probs))
    return bundle["class_names"][index], float(probs[index]), values
