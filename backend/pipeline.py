"""
pipeline.py — Toàn bộ xử lý tín hiệu EEG:
    normalize_ch_name → build_signal_dict → wavelet_denoise
    → compute_mel_chain → segment_to_pil → predict_sequence
"""
import re
from typing import Optional
import numpy as np
import librosa
import pywt
import torch
from PIL import Image as PILImage

from config import (
    FS, FREQ_MIN, FREQ_MAX,
    N_MELS, N_FFT, HOP_DENOM,
    USE_WAVELET, EEG_CHAINS,
    THRESHOLD, SEQ_LEN,
)
import model as mdl   # import module, không import biến trực tiếp


# ────────────────────────────── Channel helpers ───────────────────────

def normalize_ch_name(ch: str) -> Optional[str]:
    """Chuẩn hóa tên kênh EEG; trả về None nếu tên không hợp lệ."""
    ch = ch.strip()
    if re.match(r'^[.\-]+\d*$', ch):
        return None
    ch = re.sub(r'-(\d+)$', '', ch)
    return ch


def build_signal_dict(data: np.ndarray, ch_names: list) -> dict:
    """Map tên kênh → mảng tín hiệu (bỏ qua kênh trùng/không hợp lệ)."""
    sd = {}
    for i, ch in enumerate(ch_names):
        norm = normalize_ch_name(ch)
        if norm and norm not in sd:
            sd[norm] = data[i]
    return sd


# ────────────────────────────── Wavelet denoising ────────────────────

def _maddest(d: np.ndarray, axis=None) -> np.ndarray:
    return np.mean(np.absolute(d - np.mean(d, axis)), axis)


def wavelet_denoise(x: np.ndarray, wavelet: str = "haar", level: int = 1) -> np.ndarray:
    """Áp dụng hard-thresholding wavelet để lọc nhiễu."""
    coeff     = pywt.wavedec(x, wavelet, mode="per")
    sigma     = (1 / 0.6745) * _maddest(coeff[-level])
    uthresh   = sigma * np.sqrt(2 * np.log(len(x)))
    coeff[1:] = (pywt.threshold(c, value=uthresh, mode="hard") for c in coeff[1:])
    return pywt.waverec(coeff, wavelet, mode="per")[: len(x)]


# ────────────────────────────── Mel spectrogram ───────────────────────

def compute_mel_chain(
    signal_dict: dict,
    chain_channels: list,
    fs: int,
) -> Optional[np.ndarray]:
    """
    Tính mel spectrogram trung bình cho một bipolar chain.
    Trả về None nếu không đủ kênh.
    """
    chain_spec, count = None, 0

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
            y          = x.astype(np.float32),
            sr         = fs,
            hop_length = hop_length,
            n_fft      = N_FFT,
            n_mels     = N_MELS,
            fmin       = FREQ_MIN,
            fmax       = FREQ_MAX,
            win_length = 128,
        )
        width  = (mel_spec.shape[1] // 32) * 32
        mel_db = librosa.power_to_db(mel_spec, ref=np.max).astype(np.float32)[:, :width]
        mel_std = (mel_db + 40) / 40

        if chain_spec is None:
            chain_spec = mel_std
        else:
            w          = min(chain_spec.shape[1], mel_std.shape[1])
            chain_spec = chain_spec[:, :w] + mel_std[:, :w]
        count += 1

    return chain_spec / max(count, 1) if chain_spec is not None else None


def _spec_to_uint8(spec: np.ndarray) -> np.ndarray:
    spec = np.clip(spec, -1, 1)
    return ((spec + 1) / 2 * 255).astype(np.uint8)


# ────────────────────────────── Segment → PIL image ──────────────────

def segment_to_pil(
    segment: np.ndarray,
    ch_names: list,
    fs: int,
) -> PILImage.Image:
    """
    Chuyển một window EEG (channels × samples) thành ảnh RGB 3 kênh:
        - kênh R: chain LL
        - kênh G: trung bình LP + RP
        - kênh B: chain RR
    """
    signal_dict = build_signal_dict(segment, ch_names)
    chain_specs = {
        name: compute_mel_chain(signal_dict, chs, fs)
        for name, chs in EEG_CHAINS.items()
    }
    all_valid = [s for s in chain_specs.values() if s is not None]

    # Fallback: dùng tín hiệu trung bình nếu không có chain nào hợp lệ
    if not all_valid:
        x   = np.mean(segment, axis=0).astype(np.float32)
        hop = max(1, len(x) // HOP_DENOM)
        mel = librosa.feature.melspectrogram(
            y=x, sr=fs, hop_length=hop, n_fft=N_FFT, n_mels=N_MELS,
            fmin=FREQ_MIN, fmax=FREQ_MAX, win_length=128,
        )
        w  = (mel.shape[1] // 32) * 32
        fb = (librosa.power_to_db(mel, ref=np.max).astype(np.float32)[:, :w] + 40) / 40
        all_valid                          = [fb]
        chain_specs = {"LL": fb, "LP": fb, "RP": fb, "RR": fb}

    def _get(name: str) -> np.ndarray:
        s = chain_specs.get(name)
        return s if s is not None else all_valid[0]

    ll  = _get("LL")
    mid = (_get("LP") + _get("RP")) / 2.0
    rr  = _get("RR")

    resized = []
    for ch in [ll, mid, rr]:
        img = PILImage.fromarray(_spec_to_uint8(ch), mode="L")
        resized.append(np.array(img.resize((224, 224), PILImage.BILINEAR)))

    return PILImage.fromarray(np.stack(resized, axis=-1), mode="RGB")


# ────────────────────────────── Predict sequence ──────────────────────

def predict_sequence(pil_images: list) -> dict:
    """
    Chạy inference trên 1 sequence gồm SEQ_LEN PIL images.

    Returns:
        {"label": "seizure"|"normal", "prob": float, "confidence": float}
    """
    if mdl.model is None:
        # DEMO mode: sinh xác suất ngẫu nhiên
        prob  = float(np.random.beta(2, 5))
        label = "seizure" if prob >= THRESHOLD else "normal"
        return {
            "label":      label,
            "prob":       round(prob, 4),
            "confidence": round(abs(prob - 0.5) * 2, 4),
        }

    frames = [mdl.tfm_eval(img) for img in pil_images]
    x      = torch.stack(frames).unsqueeze(0).to(mdl.device)  # (1, S, C, H, W)

    with torch.no_grad():
        logits = mdl.model(x)
        prob   = torch.softmax(logits, dim=1)[0, 1].item()

    label = "seizure" if prob >= THRESHOLD else "normal"
    return {
        "label":      label,
        "prob":       round(prob, 4),
        "confidence": round(abs(prob - 0.5) * 2, 4),
    }
