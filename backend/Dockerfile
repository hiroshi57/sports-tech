# sports-tech backend (FastAPI + Celery worker 共用イメージ)
FROM python:3.11-slim

# MediaPipe / OpenCV の実行に必要なシステムライブラリ
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 依存を先にインストール（レイヤーキャッシュ効率化）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# デフォルトは API サーバー（worker は compose 側で command を上書き）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
