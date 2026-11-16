FROM node:22-bookworm-slim AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
COPY shared/ /shared/
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000 STORAGE_DIR=/data/captures DATABASE_URL=sqlite:////data/aura.sqlite3 SECURE_COOKIES=true
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libgomp1 fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --create-home --uid 10001 aura && mkdir -p /data && chown aura:aura /data
COPY --chown=aura:aura backend/ ./backend/
COPY --chown=aura:aura shared/ ./shared/
COPY --from=web --chown=aura:aura /web/dist/ ./frontend/dist/
USER aura
EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
