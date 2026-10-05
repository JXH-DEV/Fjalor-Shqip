FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=43177

COPY pyproject.toml README.md LICENSE ./
COPY app ./app

RUN pip install --no-cache-dir .

EXPOSE 43177
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-43177}"]
