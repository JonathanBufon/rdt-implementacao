FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    tmux \
    make \
    psmisc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN sed -i 's/\r$//' docker-entrypoint.sh \
    && chmod +x docker-entrypoint.sh \
    && mkdir -p logs

ENTRYPOINT ["bash", "docker-entrypoint.sh"]
