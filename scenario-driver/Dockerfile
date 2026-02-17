FROM python:3.12-slim
WORKDIR /app

# Install Docker CLI (needed for power outage simulation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && \
    curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-27.4.1.tgz | \
    tar xz --strip-components=1 -C /usr/local/bin docker/docker && \
    apt-get purge -y curl && apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY driver.py .
CMD ["python", "-u", "driver.py"]
