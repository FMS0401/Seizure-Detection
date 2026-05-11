"""
main.py — FastAPI routes (chỉ chứa API, logic nằm ở các file khác)

Cấu trúc:
    config.py   → hằng số
    model.py    → kiến trúc CNN-LSTM + load
    pipeline.py → xử lý EEG, tạo spectrogram, predict
    schemas.py  → cấu trúc dữ liệu request/response
    main.py     → API endpoints (file này)
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import os
import gc
import tempfile
import time
import mne

from collections import deque
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import FS, WINDOW_SEC, STEP_SEC, FREQ_MIN, FREQ_MAX, SEQ_LEN, THRESHOLD
from model import load_model, model, device
from pipeline import segment_to_pil, predict_sequence
from schemas import WindowResult, PredictionResponse

mne.set_log_level("WARNING")

# ── App ───────────────────────────────────────────────────────────────
app = FastAPI(title="Seizure Detection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Startup ───────────────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    load_model()


# ── Health check ──────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status":       "ok",
        "model_loaded": model is not None,
        "device":       str(device),
        "threshold":    THRESHOLD,
    }


# ── Predict ───────────────────────────────────────────────────────────
@app.post("/predict", response_model=PredictionResponse)
async def predict(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".edf"):
        raise HTTPException(400, "Chỉ hỗ trợ file .edf")

    t_start = time.time()
    content = await file.read()

    # Ghi file tạm
    with tempfile.NamedTemporaryFile(suffix=".edf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    del content
    gc.collect()

    try:
        # 1. Load & preprocess EDF
        raw = mne.io.read_raw_edf(tmp_path, preload=True, verbose=False)
        fs  = int(raw.info["sfreq"])
        if fs != FS:
            raw.resample(FS, verbose=False)
            fs = FS
        raw.notch_filter(freqs=50.0, verbose=False)
        raw.filter(FREQ_MIN, FREQ_MAX, fir_window="hamming", verbose=False)

        data     = raw.get_data()
        ch_names = raw.ch_names
        n_samp   = data.shape[1]
        duration = n_samp / fs

        del raw
        gc.collect()

        win_samp   = int(WINDOW_SEC * fs)
        step_samp  = int(STEP_SEC * fs)
        all_starts = list(range(0, n_samp - win_samp + 1, step_samp))

        if not all_starts:
            raise HTTPException(400, "File quá ngắn để tạo window")

        # 2. Sliding buffer — chỉ giữ SEQ_LEN ảnh trong RAM
        pad     = SEQ_LEN // 2
        buf     = deque()
        results = []

        # Pre-fill buffer
        for j in range(min(pad + 1, len(all_starts))):
            s = all_starts[j]
            buf.append(segment_to_pil(data[:, s:s + win_samp], ch_names, fs))

        for i, s in enumerate(all_starts):
            # Thêm ảnh tương lai vào buffer
            future_idx = i + pad + 1
            if future_idx < len(all_starts):
                fs_ = all_starts[future_idx]
                buf.append(segment_to_pil(data[:, fs_:fs_ + win_samp], ch_names, fs))

            # Lấy SEQ_LEN ảnh từ buffer
            buf_list = list(buf)
            if len(buf_list) >= SEQ_LEN:
                center = len(buf_list) // 2
                start  = max(0, center - SEQ_LEN // 2)
                seq    = buf_list[start:start + SEQ_LEN]
            else:
                seq = buf_list[:]
                while len(seq) < SEQ_LEN:
                    seq = [seq[0]] + seq
            seq = seq[:SEQ_LEN]

            pred = predict_sequence(seq)
            results.append(WindowResult(
                window_idx = i,
                start_sec  = round(s / fs, 2),
                end_sec    = round((s + win_samp) / fs, 2),
                label      = pred["label"],
                prob       = pred["prob"],
            ))

            # Xóa ảnh cũ khỏi buffer
            if len(buf) > SEQ_LEN + pad:
                buf.popleft()

            # Dọn RAM mỗi 50 windows
            if i % 50 == 0:
                gc.collect()

        del data, buf
        gc.collect()

        n_seizure = sum(1 for r in results if r.label == "seizure")

        return PredictionResponse(
            filename      = file.filename,
            duration_sec  = round(duration, 2),
            fs            = fs,
            n_windows     = len(results),
            n_seizure     = n_seizure,
            n_normal      = len(results) - n_seizure,
            windows       = results,
            processing_ms = int((time.time() - t_start) * 1000),
        )

    finally:
        os.unlink(tmp_path)


# ── Serve frontend ────────────────────────────────────────────────────
_frontend = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(_frontend):
    app.mount("/", StaticFiles(directory=_frontend, html=True), name="frontend")
