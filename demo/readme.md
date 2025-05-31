### Prerequisites
- Docker
- Containerlab
- Python 3.8+
- Access to Jalapeno API

### Construct the demo

1. Modify [env](.env) variables to fit your environment

2. Build the container image
```
docker build -t pytorch-srv6-demo:latest -f demo/Dockerfile .
```

3. Deploy the topology
```
containerlab deploy -t topology.yaml
```

4. Configure SONiC switches for SRv6 (documented in another repo)

5. Start the test on each host
```
# On host00
docker exec clab-sonic-host00 bash -c "RANK=0 python3 /app/test_plugin.py"

# On host01
docker exec clab-sonic-host01 bash -c "RANK=1 python3 /app/test_plugin.py"

# On host03
docker exec clab-sonic-host03 bash -c "RANK=2 python3 /app/test_plugin.py"
```

### Notes on test_plugin.py flow:
```
1. Collects node info (IP addresses, hostname)
2. Makes HTTP request to Jalapeno API
3. Gets back SRv6 path information
4. Programs local SRv6 routes using route_programmer.py
5. Tests routes with pings
```

