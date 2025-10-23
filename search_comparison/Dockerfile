FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY search_comparison/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY search_comparison/ .

EXPOSE 8001

CMD ["python", "demo_server.py"]
