FROM pytorch/pytorch:latest

# Install required packages
RUN pip install requests netifaces

# Copy your code
COPY entrypoint.py /app/
COPY network_optimized_distributed.py /app/
COPY train.py /app/

# Make entrypoint executable
RUN chmod +x /app/entrypoint.py

WORKDIR /app
ENTRYPOINT ["python", "/app/entrypoint.py"] 