"""
model.py — Định nghĩa kiến trúc CNN-LSTM và hàm load checkpoint
"""
import os
import torch
import torch.nn as nn
from torchvision import models, transforms

from backend.config import MODEL_PATH, SEQ_LEN, IMG_SIZE

# ── Device ────────────────────────────────────────────────────────────
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ── Singleton model instance (được gán bởi load_model) ───────────────
model = None


# ── Architecture ─────────────────────────────────────────────────────
class CNN_LSTM(nn.Module):
    """ResNet-18 CNN backbone + Bi-LSTM classifier cho chuỗi spectrogram."""

    def __init__(
        self,
        num_classes: int = 2,
        lstm_hidden: int = 128,
        lstm_layers: int = 2,
        sequence_len: int = 5,
    ):
        super().__init__()
        self.sequence_len = sequence_len

        backbone   = models.resnet18(weights=None)
        self.cnn   = nn.Sequential(*list(backbone.children())[:-1])

        self.lstm  = nn.LSTM(
            input_size    = 512,
            hidden_size   = lstm_hidden,
            num_layers    = lstm_layers,
            batch_first   = True,
            dropout       = 0.3,
            bidirectional = True,
        )

        self.classifier = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(lstm_hidden * 2, 64),
            nn.ReLU(),
            nn.Linear(64, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, S, C, H, W = x.shape
        x              = x.view(B * S, C, H, W)
        features       = self.cnn(x).squeeze(-1).squeeze(-1)
        features       = features.view(B, S, -1)
        lstm_out, _    = self.lstm(features)
        out            = lstm_out[:, S // 2, :]          # frame trung tâm
        return self.classifier(out)


# ── Loader ────────────────────────────────────────────────────────────
def load_model() -> None:
    """Load checkpoint vào singleton `model`. Nếu không có file → DEMO mode."""
    global model
    if not os.path.exists(MODEL_PATH):
        print(f"⚠️  Model not found at {MODEL_PATH} — running in DEMO mode")
        model = None
        return

    m = CNN_LSTM(
        num_classes  = 2,
        lstm_hidden  = 128,
        lstm_layers  = 2,
        sequence_len = SEQ_LEN,
    ).to(device)
    m.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    m.eval()
    model = m
    print(f"✅ Model loaded from {MODEL_PATH}")


# ── Eval transform ────────────────────────────────────────────────────
tfm_eval = transforms.Compose([
    transforms.Resize(IMG_SIZE),
    transforms.ToTensor(),
    transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]),
])
