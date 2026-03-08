FROM python:3.11-slim

WORKDIR /workspace

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -m appuser && \
    mkdir -p /workspace/creator_intelligence_app/data && \
    chown -R appuser:appuser /workspace

USER appuser

EXPOSE 8000
CMD ["uvicorn", "creator_intelligence_app.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
