# OpenSpace Telegram bot
# Includes:
#   - the bot itself
#   - openspace package (installed from your fork)
#   - litestream binary that pulls the skill DB from Supabase on boot,
#     then continuously replicates back
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    OPENSPACE_WORKSPACE=/data/openspace \
    OPENSPACE_HOST_SKILL_DIRS=/data/openspace/host_skills \
    OPENSPACE_DB_PATH=/data/openspace/.openspace/openspace.db

# System deps + litestream
RUN apt-get update && apt-get install -y --no-install-recommends \
      git curl ca-certificates ffmpeg \
      whois dnsutils jq tzdata uuid-runtime openssl yt-dlp && \
    curl -fsSL https://github.com/benbjohnson/litestream/releases/download/v0.3.13/litestream-v0.3.13-linux-amd64.tar.gz \
      -o /tmp/lts.tgz && \
    tar -C /usr/local/bin -xzf /tmp/lts.tgz && rm /tmp/lts.tgz && \
    rm -rf /var/lib/apt/lists/*

# Install OpenSpace from the fork (sparse to skip 50MB assets)
WORKDIR /opt
RUN git clone --depth 1 https://github.com/visheshkhurana/OpenSpace.git openspace-src
WORKDIR /opt/openspace-src
RUN pip install -e .

# Bot deps
COPY requirements.txt /opt/bot/requirements.txt
RUN pip install -r /opt/bot/requirements.txt

# Bot code
COPY app /opt/bot/app
COPY host_skills /opt/bot/host_skills
COPY litestream.yml /etc/litestream.yml
COPY entrypoint.sh /opt/bot/entrypoint.sh
RUN chmod +x /opt/bot/entrypoint.sh

# Seed host_skills so OpenSpace finds them
RUN mkdir -p /data/openspace/host_skills && \
    cp -r /opt/openspace-src/openspace/host_skills/delegate-task   /data/openspace/host_skills/ && \
    cp -r /opt/openspace-src/openspace/host_skills/skill-discovery /data/openspace/host_skills/

WORKDIR /opt/bot
CMD ["/opt/bot/entrypoint.sh"]
