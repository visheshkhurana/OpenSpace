# Railway-ready OpenSpace MCP server
# Exposes streamable HTTP so ALL your agents (on laptop, desktop, CI)
# hit ONE shared skill DB. This is what gives you cross-device token
# savings — evolution from Claude Code on laptop benefits Codex on desktop.

FROM python:3.12-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    OPENSPACE_WORKSPACE=/workspace \
    OPENSPACE_HOST_SKILL_DIRS=/workspace/host_skills

RUN apt-get update && apt-get install -y --no-install-recommends \
      git build-essential ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
# Sparse clone — skip the 50MB assets dir
RUN git clone --filter=blob:none --sparse https://github.com/visheshkhurana/OpenSpace.git . && \
    git sparse-checkout set '/*' '!assets/'

RUN pip install --upgrade pip && pip install -e .

# Persistent storage — mount a Railway volume at /workspace
# so the SQLite skill DB survives redeploys.
RUN mkdir -p /workspace/host_skills && \
    cp -r /app/openspace/host_skills/delegate-task    /workspace/host_skills/ && \
    cp -r /app/openspace/host_skills/skill-discovery  /workspace/host_skills/

EXPOSE 8081

# streamable HTTP mode (recommended for remote hosts)
CMD openspace-mcp --transport streamable-http \
      --host 0.0.0.0 \
      --port ${PORT:-8081}
