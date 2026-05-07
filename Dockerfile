FROM python:3.11-slim

WORKDIR /app

# Cài dependencies trước (tận dụng Docker layer cache)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY backend/ ./backend/

# Copy model và frontend
COPY model/    ./model/
COPY frontend/ ./frontend/

ENV MODEL_PATH=/app/model/best_cnn_lstm.pth

WORKDIR /app/backend

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
