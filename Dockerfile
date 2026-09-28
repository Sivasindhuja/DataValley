FROM python:3.11-slim

WORKDIR /app

# system deps
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ensure data dirs exist
RUN mkdir -p data/chroma knowledge

EXPOSE 8000

CMD ["sh", "-c", "python -m app.tools.seed && python -m app.rag.ingestion; uvicorn app.api.main:app --host 0.0.0.0 --port 8000"]
