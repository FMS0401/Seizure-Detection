# EEG Seizure Detection

Ứng dụng web phát hiện cơn động kinh từ file EEG (`.edf`) sử dụng mô hình CNN + LSTM.

---

## Yêu cầu cài đặt

- [Python 3.9+](https://www.python.org/downloads/)
- [Visual Studio Code](https://code.visualstudio.com/)
- Extension **Python** (của Microsoft) cài trong VS Code

---

## Cấu trúc thư mục

```
eeg-app/
├── backend/
│   ├── __init__.py
│   ├── config.py
│   ├── main.py           # FastAPI app — toàn bộ pipeline inference
│   ├── model.py
│   ├── pipeline.py
│   ├── requirements.txt
│   └── schemas.py
├── frontend/
│   ├── css
│   │   └── style.css
│   ├── js
│   │   ├── app.js
│   │   └── ui.js
│   └── index.html        # Giao diện web
├── model/
│   └── best_cnn_lstm.pth ← ĐẶT MODEL VÀO ĐÂY
├── .gitignore
├── Dockerfile
├── railway.json
└── README.md
```

## Cài đặt & Chạy

### 1. Tạo môi trường ảo

```bash
python -m venv venv
```

Kích hoạt môi trường ảo:

```bash
# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

> Sau khi kích hoạt thành công, đầu dòng terminal sẽ hiện `(venv)`.

### 2. Cài thư viện

```bash
pip install -r backend/requirements.txt
```

### 3. Đặt file model

Sao chép file `best_cnn_lstm.pth` vào thư mục `model/`:

> Nếu không có file model, app vẫn chạy được ở **chế độ DEMO** (kết quả ngẫu nhiên).

### 4. Chạy server

```bash
uvicorn backend.main:app --reload
```

Terminal sẽ hiện thông báo:

```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 5. Mở trình duyệt

Truy cập: **http://localhost:8000**

---

## Cách sử dụng

1. Kéo thả hoặc click để chọn file `.edf`
2. Điều chỉnh ngưỡng seizure nếu cần (mặc định: 0.20)
3. Nhấn **Phân tích**
4. Xem kết quả trên timeline và danh sách các đoạn seizure phát hiện được

---

## Lưu ý

- Mỗi lần mở terminal mới cần kích hoạt lại môi trường ảo (Bước 3).
- Kết quả chỉ mang tính tham khảo, không thay thế chẩn đoán y tế.
