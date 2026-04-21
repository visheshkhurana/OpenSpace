FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

COPY recruiter/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY host_skills/ ./host_skills/
COPY recruiter/ .

RUN mkdir -p /data/recruiter/.openspace
RUN chmod +x entrypoint.sh 2>/dev/null || true
CMD ["python","-u","runner.py"]
