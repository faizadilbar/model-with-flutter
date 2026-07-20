"""
detectors/eye_model_predictor.py

Eye State Model Predictor & Human Blink Rate Tracker.
Loads fine-tuned ResNet18 / MobileNetV2 model to predict eye state (Open vs Closed)
and computes human blink rate (blinks per minute) using BlinkCounter.
"""

import os
import torch
import torch.nn as nn
from torchvision import transforms, models
import numpy as np
from PIL import Image

from detectors.blink_counter import BlinkCounter


class EyeModelPredictor:
    def __init__(self, model_path: str = "models/best_eye_model.pth", device: str = None):
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        self.model = None
        self.class_to_idx = {}
        self.idx_to_class = {}
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        self.blink_counter = BlinkCounter()

        if os.path.exists(model_path):
            self.load_model(model_path)
        else:
            print(f"[WARNING] Model file '{model_path}' not found. Standalone predictions disabled until trained.")

    def load_model(self, model_path: str):
        print(f"[INFO] Loading PyTorch eye model from '{model_path}'...")
        checkpoint = torch.load(model_path, map_location=self.device)

        arch = checkpoint.get("model_architecture", "resnet18")
        self.class_to_idx = checkpoint.get("class_to_idx", {"awake": 0, "sleepy": 1})
        self.idx_to_class = {v: k for k, v in self.class_to_idx.items()}

        num_classes = len(self.class_to_idx)
        if arch == "resnet18":
            self.model = models.resnet18(pretrained=False)
            self.model.fc = nn.Linear(self.model.fc.in_features, num_classes)
        elif arch == "mobilenet_v2":
            self.model = models.mobilenet_v2(pretrained=False)
            self.model.classifier[1] = nn.Linear(self.model.classifier[1].in_features, num_classes)
        else:
            raise ValueError(f"Unknown architecture: {arch}")

        self.model.load_state_dict(checkpoint["state_dict"])
        self.model.to(self.device)
        self.model.eval()
        print(f"[INFO] Model successfully loaded ({arch}). Class mapping: {self.class_to_idx}")

    @torch.no_grad()
    def predict_image(self, img: Image.Image) -> dict:
        """
        Predicts eye state for a PIL Image or OpenCV BGR frame.
        Returns dict with predicted class, probabilities, and closed probability.
        """
        if self.model is None:
            raise RuntimeError("Model is not loaded.")

        if isinstance(img, np.ndarray):
            # Convert BGR (OpenCV) to RGB PIL Image
            img = Image.fromarray(img[:, :, ::-1])

        tensor_img = self.transform(img).unsqueeze(0).to(self.device)
        outputs = self.model(tensor_img)
        probs = torch.softmax(outputs, dim=1).squeeze(0).cpu().numpy()

        pred_idx = int(np.argmax(probs))
        pred_label = self.idx_to_class.get(pred_idx, "unknown")

        sleepy_idx = self.class_to_idx.get("sleepy", 1)
        sleepy_prob = float(probs[sleepy_idx])

        return {
            "label": pred_label,
            "confidence": float(probs[pred_idx]),
            "is_closed": (pred_label == "sleepy"),
            "closed_prob": sleepy_prob,
        }

    def process_frame(self, eye_crop: np.ndarray) -> dict:
        """
        Processes a single frame's eye crop, updates human blink rate counter.
        """
        result = self.predict_image(eye_crop)

        # Pass artificial EAR inverse or closed_prob to blink counter
        # When eye is closed, closed_prob is high -> EAR proxy drops
        ear_proxy = 1.0 - result["closed_prob"]
        blink_detected = self.blink_counter.update(ear_proxy)
        blink_rate = self.blink_counter.blink_rate()

        result.update({
            "blink_detected": blink_detected,
            "total_blinks": self.blink_counter.count,
            "blink_rate_bpm": blink_rate,
            "is_blink_anomalous": self.blink_counter.is_anomalous(),
        })

        return result
