FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
RUN useradd --create-home --uid 10001 appuser && chown appuser:appuser /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=appuser:appuser . .
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "uvicorn main:app --no-access-log --host 0.0.0.0 --port ${PORT:-8000}"]
