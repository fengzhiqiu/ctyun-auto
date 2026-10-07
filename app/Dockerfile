ARG BASE_IMAGE=su3817807/ctyun:1.1.5
FROM ${BASE_IMAGE}

USER root
WORKDIR /app
ENV TZ=Asia/Shanghai RUNNING_IN_DOCKER=true PYTHONUNBUFFERED=1 CTYUN_DATA_DIR=/app/data \
    PATH="/opt/venv/bin:${PATH}" CHROME_PATH=/usr/bin/chromium

ARG APT_MIRROR=deb.debian.org
RUN sed -i "s/deb.debian.org/${APT_MIRROR}/g" /etc/apt/sources.list 2>/dev/null || true
RUN sed -i "s/deb.debian.org/${APT_MIRROR}/g" /etc/apt/sources.list.d/debian.sources 2>/dev/null || true
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv chromium fonts-wqy-zenhei cron \
    libgl1 libglib2.0-0 tzdata ca-certificates procps tini \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/venv

ARG PIP_INDEX_URL=https://pypi.org/simple
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -i "$PIP_INDEX_URL" -r /app/requirements.txt

COPY *.py /app/
COPY entrypoint.sh /app/entrypoint.sh
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh \
    && mkdir -p /app/data \
    && rm -f /etc/cron.d/ctyun-cron \
    && (crontab -r 2>/dev/null || true)

HEALTHCHECK --interval=60s --timeout=5s --start-period=30s --retries=3 \
    CMD pgrep -x cron >/dev/null || exit 1
ENTRYPOINT ["/usr/bin/tini", "-g", "--", "/app/entrypoint.sh"]
