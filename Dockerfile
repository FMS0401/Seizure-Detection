FROM python:3.11-slim
WORKDIR /app

# Cài torch CPU-only trước (nhẹ hơn ~600MB so với bản đầy đủ)
RUN pip install --no-cache-dir \
    torch==2.2.2+cpu \
    torchvision==0.17.2+cpu \
    --extra-index-url https://download.pytorch.org/whl/cpu

# Cài các thư viện còn lại
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/  ./backend/
COPY model/    ./model/
COPY frontend/ ./frontend/

ENV MODEL_PATH=/app/model/best_cnn_lstm.pth
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]