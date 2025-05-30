FROM ubuntu:22.04

# Install required packages
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    iproute2 \
    iputils-ping \
    net-tools \
    libcap2-bin \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt /app/
WORKDIR /app

# Install Python packages from requirements.txt
RUN pip3 install -r requirements.txt

# Copy plugin files
COPY dist_setup.py /app/
COPY network_programmer.py /app/
COPY route_programmer.py /app/
COPY demo_plugin.py /app/
COPY test_dist.py /app/
COPY demo/.env /app/

# Create a script to set capabilities at runtime
RUN echo '#!/bin/bash\nsetcap cap_net_admin,cap_net_raw+ep /sbin/ip\nexec "$@"' > /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

WORKDIR /app
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["/bin/bash"]