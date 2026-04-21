FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y git curl && rm -rf /var/lib/apt/lists/*

COPY meta-learner/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY host_skills/ ./host_skills/
COPY meta-learner/ .

RUN mkdir -p /data/meta-learner/.openspace
CMD ["python","-u","runner.py"]
