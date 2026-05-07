# NeuroScan — EEG Seizure Detection Web App

Deploy pipeline: `.edf` → windowing → Mel spectrogram → CNN+LSTM → kết quả từng window

## Cấu trúc thư mục

```
eeg-app/
├── backend/
│   ├── main.py           # FastAPI app — toàn bộ pipeline inference
│   └── requirements.txt
├── frontend/
│   └── index.html        # Giao diện web
├── model/
│   └── best_cnn_lstm.pth ← ĐẶT MODEL VÀO ĐÂY
└── Dockerfile
```

## Cài đặt & chạy

### 1. Đặt model vào đúng chỗ

```bash
cp /content/best_cnn_lstm.pth model/best_cnn_lstm.pth
```

### 2. Cài dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Chạy server

```bash
# Từ thư mục gốc eeg-app/
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Mở trình duyệt: **http://localhost:8000**

---

### Docker (khuyến nghị cho production)

```bash
docker build -t neuroscan .
docker run -p 8000:8000 -v $(pwd)/model:/app/model neuroscan
```

---

## Config quan trọng trong `backend/main.py`

| Biến | Giá trị | Mô tả |
|------|---------|-------|
| `THRESHOLD` | `0.50` | **Đổi thành `best_thresh` từ training của bạn** |
| `FS` | `256` | Sample rate |
| `WINDOW_SEC` | `8` | Độ dài mỗi window |
| `STEP_SEC` | `4` | Bước trượt |
| `SEQ_LEN` | `5` | Số frame cho LSTM |

> ⚠️ **Quan trọng**: Thay `THRESHOLD = 0.5` bằng `best_thresh` tối ưu đã tìm được trên validation set.

---

## API Endpoints

### `POST /predict`
Upload file EDF, trả về JSON với kết quả từng window.

**Request**: `multipart/form-data` với field `file` là file `.edf`

**Response**:
```json
{
  "filename": "chb01_03.edf",
  "duration_sec": 3600.0,
  "fs": 256,
  "n_windows": 899,
  "n_seizure": 12,
  "n_normal": 887,
  "windows": [
    {
      "window_idx": 0,
      "start_sec": 0.0,
      "end_sec": 8.0,
      "label": "normal",
      "prob": 0.0342,
      "confidence": 0.9316
    },
    ...
  ],
  "processing_ms": 45231
}
```

### `GET /health`
Kiểm tra trạng thái server & model.

---

## Demo mode

Nếu không có file model, app chạy ở **DEMO mode** — predict random để test giao diện.
