FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared/ ./shared/
COPY . .
RUN mkdir -p /data/tournament/.openspace
RUN chmod +x entrypoint.sh
CMD ["./entrypoint.sh"]
