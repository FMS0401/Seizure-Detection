"""
main.py
EEG Seizure Detection — FastAPI Backend
Pipeline: EDF → windowing → spectrogram → CNN-LSTM → predict
"""

import os, io, tempfile, time
import numpy as np
import librosa
import pywt
import mne
from PIL import Image as PILImage
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import torch
import torch.nn as nn
from torchvision import models, transforms

# ────────────────────────────── CONFIG ──────────────────────────────
FS          = 256
WINDOW_SEC  = 8
STEP_SEC    = 4
FREQ_MIN    = 0.5
FREQ_MAX    = 40.0
N_MELS      = 128
N_FFT       = 1024
HOP_DENOM   = 256
USE_WAVELET = "haar"
IMG_SIZE    = (224, 224)
SEQ_LEN     = 5
THRESHOLD   = 0.5   # ← thay bằng best_thresh của bạn
MODEL_PATH  = os.environ.get("MODEL_PATH", "./model/best_cnn_lstm.pth")

EEG_CHAINS = {
    "LL": ["FP1-F7", "F7-T7",  "T7-P7",  "P7-O1"],
    "LP": ["FP1-F3", "F3-C3",  "C3-P3",  "P3-O1"],
    "RP": ["FP2-F4", "F4-C4",  "C4-P4",  "P4-O2"],
    "RR": ["FP2-F8", "F8-T8",  "T8-P8",  "P8-O2"],
}

mne.set_log_level("WARNING")

# ────────────────────────────── MODEL ───────────────────────────────
class CNN_LSTM(nn.Module):
    def __init__(self, num_classes=2, lstm_hidden=128,
                 lstm_layers=2, sequence_len=5):
        super().__init__()
        self.sequence_len = sequence_len
        backbone          = models.resnet18(weights=None)
        self.cnn          = nn.Sequential(*list(backbone.children())[:-1])
        self.lstm = nn.LSTM(
            input_size    = 512,
            hidden_size   = lstm_hidden,
            num_layers    = lstm_layers,
            batch_first   = True,
            dropout       = 0.3,
            bidirectional = True
        )
        self.classifier = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(lstm_hidden * 2, 64),
            nn.ReLU(),
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        B, S, C, H, W = x.shape
        x              = x.view(B * S, C, H, W)
        features       = self.cnn(x).squeeze(-1).squeeze(-1)
        features       = features.view(B, S, -1)
        lstm_out, _    = self.lstm(features)
        out            = lstm_out[:, S // 2, :]
        return self.classifier(out)


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model  = None

def load_model():
    global model
    if not os.path.exists(MODEL_PATH):
        print(f"⚠️  Model not found at {MODEL_PATH} — running in DEMO mode")
        model = None
        return
    m = CNN_LSTM(num_classes=2, lstm_hidden=128,
                 lstm_layers=2, sequence_len=SEQ_LEN).to(device)
    m.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    m.eval()
    model = m
    print(f"✅ Model loaded from {MODEL_PATH}")

# ────────────────────────────── TRANSFORMS ──────────────────────────
tfm_eval = transforms.Compose([
    transforms.Resize(IMG_SIZE),
    transforms.ToTensor(),
    transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]),
])

# ────────────────────────────── PIPELINE ────────────────────────────
import re

def normalize_ch_name(ch):
    ch = ch.strip()
    if re.match(r'^[.\-]+\d*$', ch):
        return None
    ch = re.sub(r'-(\d+)$', '', ch)
    return ch


def build_signal_dict(data, ch_names):
    sd = {}
    for i, ch in enumerate(ch_names):
        norm = normalize_ch_name(ch)
        if norm and norm not in sd:
            sd[norm] = data[i]
    return sd


def maddest(d, axis=None):
    return np.mean(np.absolute(d - np.mean(d, axis)), axis)


def wavelet_denoise(x, wavelet="haar", level=1):
    coeff   = pywt.wavedec(x, wavelet, mode="per")
    sigma   = (1 / 0.6745) * maddest(coeff[-level])
    uthresh = sigma * np.sqrt(2 * np.log(len(x)))
    coeff[1:] = (pywt.threshold(c, value=uthresh, mode="hard")
                 for c in coeff[1:])
    return pywt.waverec(coeff, wavelet, mode="per")[:len(x)]


def compute_mel_chain(signal_dict, chain_channels, fs):
    chain_spec = None
    count      = 0
    for i in range(len(chain_channels) - 1):
        ch_a, ch_b = chain_channels[i], chain_channels[i + 1]
        if ch_a not in signal_dict or ch_b not in signal_dict:
            continue
        x = signal_dict[ch_a] - signal_dict[ch_b]
        m = np.nanmean(x)
        x = np.nan_to_num(x, nan=m if not np.isnan(m) else 0)
        if USE_WAVELET:
            x = wavelet_denoise(x, wavelet=USE_WAVELET)
        hop_length = max(1, len(x) // HOP_DENOM)
        mel_spec   = librosa.feature.melspectrogram(
            y=x.astype(np.float32), sr=fs,
            hop_length=hop_length, n_fft=N_FFT, n_mels=N_MELS,
            fmin=FREQ_MIN, fmax=FREQ_MAX, win_length=128
        )
        width  = (mel_spec.shape[1] // 32) * 32
        mel_db = librosa.power_to_db(mel_spec, ref=np.max
                 ).astype(np.float32)[:, :width]
        mel_std = (mel_db + 40) / 40
        if chain_spec is None:
            chain_spec = mel_std
        else:
            w = min(chain_spec.shape[1], mel_std.shape[1])
            chain_spec = chain_spec[:, :w] + mel_std[:, :w]
        count += 1
    return chain_spec / max(count, 1) if chain_spec is not None else None


def spec_to_uint8(spec):
    spec = np.clip(spec, -1, 1)
    return ((spec + 1) / 2 * 255).astype(np.uint8)


def segment_to_pil(segment, ch_names, fs) -> PILImage.Image:
    signal_dict = build_signal_dict(segment, ch_names)
    chain_specs = {
        name: compute_mel_chain(signal_dict, chs, fs)
        for name, chs in EEG_CHAINS.items()
    }
    all_valid = [s for s in chain_specs.values() if s is not None]
    if not all_valid:
        x   = np.mean(segment, axis=0).astype(np.float32)
        hop = max(1, len(x) // HOP_DENOM)
        mel = librosa.feature.melspectrogram(
            y=x, sr=fs, hop_length=hop, n_fft=N_FFT, n_mels=N_MELS,
            fmin=FREQ_MIN, fmax=FREQ_MAX, win_length=128
        )
        w  = (mel.shape[1] // 32) * 32
        fb = (librosa.power_to_db(mel, ref=np.max
             ).astype(np.float32)[:, :w] + 40) / 40
        all_valid = [fb]
        chain_specs = {"LL": fb, "LP": fb, "RP": fb, "RR": fb}

    def get(name):
        s = chain_specs.get(name)
        return s if s is not None else all_valid[0]

    ll  = get("LL")
    mid = (get("LP") + get("RP")) / 2.0
    rr  = get("RR")

    resized = []
    for ch in [ll, mid, rr]:
        img = PILImage.fromarray(spec_to_uint8(ch), mode="L")
        resized.append(np.array(img.resize((224, 224), PILImage.BILINEAR)))
    return PILImage.fromarray(np.stack(resized, axis=-1), mode="RGB")


def predict_sequence(pil_images: list) -> dict:
    """
    Predict trên 1 sequence gồm SEQ_LEN PIL images.
    Returns: {"label": "seizure"|"normal", "prob": float, "confidence": float}
    """
    if model is None:
        # DEMO mode: random prediction
        prob  = float(np.random.beta(2, 5))
        label = "seizure" if prob >= THRESHOLD else "normal"
        return {"label": label, "prob": round(prob, 4),
                "confidence": round(abs(prob - 0.5) * 2, 4)}

    frames = [tfm_eval(img) for img in pil_images]
    x      = torch.stack(frames).unsqueeze(0).to(device)  # (1, S, C, H, W)
    with torch.no_grad():
        logits = model(x)
        prob   = torch.softmax(logits, dim=1)[0, 1].item()
    label = "seizure" if prob >= THRESHOLD else "normal"
    return {"label": label, "prob": round(prob, 4),
            "confidence": round(abs(prob - 0.5) * 2, 4)}


# ────────────────────────────── APP ─────────────────────────────────
app = FastAPI(title="EEG Seizure Detection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class WindowResult(BaseModel):
    window_idx:   int
    start_sec:    float
    end_sec:      float
    label:        str
    prob:         float
    confidence:   float


class PredictionResponse(BaseModel):
    filename:      str
    duration_sec:  float
    fs:            int
    n_windows:     int
    n_seizure:     int
    n_normal:      int
    windows:       List[WindowResult]
    processing_ms: int


@app.on_event("startup")
def startup():
    load_model()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "device": str(device),
        "threshold": THRESHOLD,
    }


@app.post("/predict", response_model=PredictionResponse)
async def predict(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".edf"):
        raise HTTPException(400, "Chỉ hỗ trợ file .edf")

    t_start = time.time()

    # Save to temp file
    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".edf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Load EDF
        raw = mne.io.read_raw_edf(tmp_path, preload=True, verbose=False)
        fs  = int(raw.info["sfreq"])
        if fs != FS:
            raw.resample(FS, verbose=False)
            fs = FS

        raw.notch_filter(freqs=50.0, verbose=False)
        raw.filter(FREQ_MIN, FREQ_MAX, fir_window="hamming", verbose=False)

        data      = raw.get_data()
        ch_names  = raw.ch_names
        n_samp    = data.shape[1]
        duration  = n_samp / fs
        win_samp  = int(WINDOW_SEC * fs)
        step_samp = int(STEP_SEC   * fs)

        # Generate all window starts
        all_starts = list(range(0, n_samp - win_samp + 1, step_samp))
        if not all_starts:
            raise HTTPException(400, "File quá ngắn để tạo window")

        # Build spectrograms for all windows
        all_pils = []
        for s in all_starts:
            pil = segment_to_pil(data[:, s:s + win_samp], ch_names, fs)
            all_pils.append(pil)

        # Predict using sliding sequence window (SEQ_LEN = 5)
        results = []
        pad = SEQ_LEN // 2  # 2

        for i, s in enumerate(all_starts):
            # build sequence centered at window i
            seq_indices = []
            for offset in range(-pad, pad + 1):
                idx = max(0, min(len(all_pils) - 1, i + offset))
                seq_indices.append(idx)
            seq_imgs = [all_pils[idx] for idx in seq_indices]

            pred = predict_sequence(seq_imgs)
            results.append(WindowResult(
                window_idx  = i,
                start_sec   = round(s / fs, 2),
                end_sec     = round((s + win_samp) / fs, 2),
                label       = pred["label"],
                prob        = pred["prob"],
                confidence  = pred["confidence"],
            ))

        n_seizure = sum(1 for r in results if r.label == "seizure")
        n_normal  = len(results) - n_seizure
        proc_ms   = int((time.time() - t_start) * 1000)

        return PredictionResponse(
            filename      = file.filename,
            duration_sec  = round(duration, 2),
            fs            = fs,
            n_windows     = len(results),
            n_seizure     = n_seizure,
            n_normal      = n_normal,
            windows       = results,
            processing_ms = proc_ms,
        )

    finally:
        os.unlink(tmp_path)


# Serve frontend
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")