FROM ubuntu:22.04

# Install required packages
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    iproute2 \
    iputils-ping \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt /app/
WORKDIR /app

# Install Python packages from requirements.txt
RUN pip3 install -r requirements.txt

# Copy plugin files
COPY network_optimized_distributed.py /app/
COPY route_programmer.py /app/
COPY test_plugin.py /app/
COPY entrypoint.py /app/

WORKDIR /app
ENTRYPOINT ["python", "/app/entrypoint.py"] 