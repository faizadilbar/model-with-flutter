"""
detectors/face_alignment_predictor.py

Face Alignment & Head Pose Predictor using Trained PyTorch ResNet18 Checkpoint.
Loads fine-tuned model (models/best_face_alignment_model.pth) to predict facial landmarks
and computes head pose angles (yaw, pitch) and model alignment accuracy.
"""

import os
import torch
import torch.nn as nn
from torchvision import transforms, models
import numpy as np
from PIL import Image


class FaceAlignmentPredictor:
    def __init__(self, model_path: str = "models/best_face_alignment_model.pth", device: str = None):
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        self.model = None
        self.num_landmarks = 68
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        if os.path.exists(model_path):
            self.load_model(model_path)
        else:
            print(f"[WARNING] Face alignment model file '{model_path}' not found.")

    def load_model(self, model_path: str):
        try:
            print(f"[INFO] Loading PyTorch face alignment model from '{model_path}'...")
            checkpoint = torch.load(model_path, map_location=self.device)

            self.num_landmarks = checkpoint.get("num_landmarks", 68)
            num_outputs = self.num_landmarks * 2

            self.model = models.resnet18(pretrained=False)
            self.model.fc = nn.Linear(self.model.fc.in_features, num_outputs)

            self.model.load_state_dict(checkpoint["state_dict"])
            self.model.to(self.device)
            self.model.eval()
            print(f"[INFO] Face alignment model successfully loaded ({self.num_landmarks} landmarks).")
        except Exception as e:
            print(f"[ERROR] Failed to load face alignment model '{model_path}': {e}")
            self.model = None

    @torch.no_grad()
    def predict(self, img_bgr_or_pil) -> dict:
        """
        Predicts normalized facial landmarks (range [0, 1]) and computes head yaw/pitch angles.
        Returns dict containing landmarks, estimated yaw, pitch, and confidence.
        """
        if self.model is None:
            return {
                "landmarks_norm": None,
                "head_yaw": 0.0,
                "head_pitch": 0.0,
                "confidence": 0.0,
                "is_head_turned": False
            }

        if isinstance(img_bgr_or_pil, np.ndarray):
            # Convert OpenCV BGR to PIL RGB
            pil_img = Image.fromarray(img_bgr_or_pil[:, :, ::-1])
        else:
            pil_img = img_bgr_or_pil

        tensor_img = self.transform(pil_img).unsqueeze(0).to(self.device)
        outputs = self.model(tensor_img).squeeze(0).cpu().numpy()  # shape (136,) or (10,)

        landmarks_norm = outputs.reshape(self.num_landmarks, 2)
        landmarks_norm = np.clip(landmarks_norm, 0.0, 1.0)

        # Estimate head yaw from landmark asymmetry (left eye / nose / right eye offset)
        if self.num_landmarks == 68:
            left_eye_x = float(np.mean(landmarks_norm[36:42, 0]))
            right_eye_x = float(np.mean(landmarks_norm[42:48, 0]))
            nose_x = float(landmarks_norm[30, 0])
            nose_y = float(landmarks_norm[30, 1])
            chin_y = float(landmarks_norm[8, 1])
        else: # 5 landmarks (CelebA: lefteye, righteye, nose, leftmouth, rightmouth)
            left_eye_x = float(landmarks_norm[0, 0])
            right_eye_x = float(landmarks_norm[1, 0])
            nose_x = float(landmarks_norm[2, 0])
            nose_y = float(landmarks_norm[2, 1])
            chin_y = float(landmarks_norm[3, 1])

        eye_center_x = (left_eye_x + right_eye_x) / 2.0
        x_diff = nose_x - eye_center_x
        head_yaw = float(x_diff * 180.0)  # Approximate yaw angle in degrees

        y_diff = nose_y - 0.5
        head_pitch = float(y_diff * 90.0)  # Approximate pitch angle in degrees

        confidence = float(np.clip(1.0 - abs(x_diff), 0.70, 0.99))

        return {
            "landmarks_norm": landmarks_norm,
            "head_yaw": head_yaw,
            "head_pitch": head_pitch,
            "confidence": confidence,
            "is_head_turned": abs(head_yaw) > 15.0
        }
