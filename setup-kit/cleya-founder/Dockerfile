# Cleya founder agent — always-on, self-evolving
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OPENSPACE_WORKSPACE=/data/openspace \
    OPENSPACE_HOST_SKILL_DIRS=/data/openspace/host_skills \
    OPENSPACE_DB_PATH=/data/openspace/.openspace/openspace.db

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
      git curl ca-certificates jq tzdata uuid-runtime openssl whois dnsutils \
    && rm -rf /var/lib/apt/lists/*

# Install OpenSpace from the fork
WORKDIR /opt
RUN git clone --depth 1 https://github.com/visheshkhurana/OpenSpace.git openspace-src
WORKDIR /opt/openspace-src
RUN pip install -e .

# Agent code + skills
COPY app /opt/agent/app
COPY host_skills /opt/agent/host_skills
COPY entrypoint.sh /opt/agent/entrypoint.sh
RUN chmod +x /opt/agent/entrypoint.sh

WORKDIR /opt/agent
CMD ["/opt/agent/entrypoint.sh"]
