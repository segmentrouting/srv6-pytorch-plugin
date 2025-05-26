# nccl


## Distributed Training with Network Optimization

Docker run command to spin up nccl simulation containers:

```bash
# Example Docker run command for dual-homed containers
docker run -d --name nccl00 \
  --network frontend \
  --network backend \
  --hostname nccl00 \
  -v $(pwd)/pytorch_app:/app \
  pytorch/pytorch:latest
```

# Run on a single node with simulated processes
```bash
python -m torch.distributed.launch --nproc_per_node=4 distributed_app.py
```

# Or across multiple containers
```bash
# On nccl00 (master):
MASTER_ADDR=nccl00 MASTER_PORT=29500 WORLD_SIZE=4 RANK=0 python distributed_app.py

# On nccl01:
MASTER_ADDR=nccl00 MASTER_PORT=29500 WORLD_SIZE=4 RANK=1 python distributed_app.py

# And so on for nccl02 and nccl03

## API service
### Install dependencies
```bash
pip install fastapi uvicorn pydantic
```

### Run the API server
```bash
python network_api.py
```

### curl test
```json
curl -X POST http://localhost:8000/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test_job_1",
    "world_size": 4,
    "master_addr": "nccl00",
    "nodes": [
      {
        "hostname": "nccl00",
        "interfaces": {
          "eth0": "10.1.0.10",
          "eth1": "10.2.0.10"
        }
      },    
      {
        "hostname": "nccl01",
        "interfaces": {
          "eth0": "10.1.0.11",
          "eth1": "10.2.0.11"
        }
      }
    ],
    "frontend_network": "10.1.0.0/16",
    "backend_network": "10.2.0.0/16"
  }'
```

### Get optimization status
```bash
curl http://localhost:8000/optimization/test_job_1
```