FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential gcc g++ libgomp1 && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[api]"
EXPOSE 8000
CMD ["uvicorn", "mmm.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
