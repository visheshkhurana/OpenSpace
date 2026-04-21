FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

COPY meta/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY host_skills/ ./host_skills/
COPY meta/ .

RUN mkdir -p /data/meta/.openspace
RUN chmod +x entrypoint.sh
CMD ["./entrypoint.sh"]
