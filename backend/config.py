"""
config.py — Toàn bộ hằng số & cấu hình pipeline
"""
import os

# ── Sampling & windowing ──────────────────────────────────────────────
FS          = 256       # Tần số mẫu mục tiêu (Hz)
WINDOW_SEC  = 8         # Độ dài mỗi window (giây)
STEP_SEC    = 4         # Bước trượt giữa các window (giây)

# ── Spectrogram ───────────────────────────────────────────────────────
FREQ_MIN    = 0.5       # Tần số thấp nhất (Hz)
FREQ_MAX    = 40.0      # Tần số cao nhất (Hz)
N_MELS      = 128       # Số mel bands
N_FFT       = 1024      # FFT size
HOP_DENOM   = 256       # hop_length = len(signal) // HOP_DENOM
IMG_SIZE    = (224, 224)

# ── Wavelet denoising ─────────────────────────────────────────────────
USE_WAVELET = "haar"    # None để tắt

# ── Model ─────────────────────────────────────────────────────────────
SEQ_LEN     = 5         # Số frames đưa vào LSTM
THRESHOLD   = 0.5       # Ngưỡng phân loại seizure
MODEL_PATH  = os.environ.get("MODEL_PATH", "./model/best_cnn_lstm.pth")

# ── EEG bipolar chains ────────────────────────────────────────────────
EEG_CHAINS = {
    "LL": ["FP1-F7", "F7-T7",  "T7-P7",  "P7-O1"],
    "LP": ["FP1-F3", "F3-C3",  "C3-P3",  "P3-O1"],
    "RP": ["FP2-F4", "F4-C4",  "C4-P4",  "P4-O2"],
    "RR": ["FP2-F8", "F8-T8",  "T8-P8",  "P8-O2"],
}
