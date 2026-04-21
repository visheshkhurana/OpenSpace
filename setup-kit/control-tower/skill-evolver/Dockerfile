FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

COPY skill-evolver/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY host_skills/ ./host_skills/
COPY skill-evolver/ .

RUN mkdir -p /data/skill-evolver/.openspace
CMD ["python","-u","runner.py"]
