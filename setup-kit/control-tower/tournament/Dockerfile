FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

COPY tournament/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY host_skills/ ./host_skills/
COPY tournament/ .

RUN mkdir -p /data/tournament/.openspace
RUN chmod +x entrypoint.sh 2>/dev/null || true
CMD ["python","-u","runner.py"]
