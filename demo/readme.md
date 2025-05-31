### Prerequisites
- Docker
- Containerlab
- Python 3.8+
- Access to Jalapeno API

### Environment Variables
Create a `.env` file with the following variables:
```
# PyTorch distributed settings
RANK=0
WORLD_SIZE=3
MASTER_ADDR=2001:db8:1000::2
MASTER_PORT=29501
BACKEND_INTERFACE=eth1
HOSTNAME_PREFIX=host

# Network settings
TOPOLOGY_COLLECTION=fabric_graph
JALAPENO_API_ENDPOINT=http://198.18.128.101:30800/api/v1
ROUTE_TABLE_ID=254
ROUTE_PLATFORM=linux
DEST_FUNCTION=fe06
```

### Construct the demo

1. Build the container image
```
docker build -t pytorch-srv6-demo:latest -f demo/Dockerfile .
```

2. Deploy the topology
```
containerlab deploy -t topology.yaml
```

3. Configure SONiC switches for SRv6 (documented in another repo)

4. Start the test on each host
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

Example:

Container clab-sonic-host00:
1. Runs test_plugin.py
2. Calls API at http://jalapeno-api:8000/graphs/{collection_name}/shortest_path/load
3. Gets back SRv6 paths
4. Programs routes using route_programmer.py
5. Tests routes with pings

Container clab-sonic-host01 and host03:
(Same process, but with different rank/world_size)

### Troubleshooting
- Ensure all environment variables are set correctly
- Check network connectivity between hosts
- Verify SONiC switch configurations
- Check Jalapeno API accessibility
