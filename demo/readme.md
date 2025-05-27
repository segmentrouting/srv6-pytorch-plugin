### Prerequisites
- Docker
- Containerlab
- Python 3.8+
- Access to Jalapeno API

### Environment Variables
Create a `.env` file with the following variables:
```
JALAPENO_API_ENDPOINT=http://jalapeno-api:8000
TOPOLOGY_COLLECTION=your-collection-name
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
test_plugin.py
↓
Creates NetworkOptimizedDistributed instance
↓
Calls init_process_group()
↓
1. Collects node info (IP addresses, hostname)
2. Makes HTTP request to your Jalapeno API
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

Container clab-sonic-host01:
(Same process, but with different rank/world_size)

### Troubleshooting
- Ensure all environment variables are set correctly
- Check network connectivity between hosts
- Verify SONiC switch configurations
- Check Jalapeno API accessibility

# For host00
docker cp demo/test_plugin.py clab-sonic-host00:/app/
docker cp network_optimized_distributed.py clab-sonic-host00:/app/

# For host01
docker cp demo/test_plugin.py clab-sonic-host01:/app/
docker cp network_optimized_distributed.py clab-sonic-host01:/app/

# For host03
docker cp demo/test_plugin.py clab-sonic-host03:/app/
docker cp network_optimized_distributed.py clab-sonic-host03:/app/





docker cp demo/test_plugin.py clab-sonic-host00:/app/
docker cp net_dist.py clab-sonic-host00:/app/

docker cp demo/test_plugin.py clab-sonic-host01:/app/
docker cp net_dist.py clab-sonic-host01:/app/

docker cp demo/test_plugin.py clab-sonic-host03:/app/
docker cp net_dist.py clab-sonic-host03:/app/



This new structure gives us:
Simple Demo Interface:
Users just need to create a DemoPlugin instance and call init_process_group()
All the complexity is hidden behind a simple interface
Clean Separation of Concerns:
dist_setup.py handles PyTorch distributed initialization
network_programmer.py handles route programming
demo_plugin.py combines them in a user-friendly way
Easy Path to Plugin:
The code is already structured in a way that will make it easy to convert to a proper plugin
We can later add proper packaging, documentation, and a more polished API
To test this new setup:
First, start host00 (master):
Apply to test_dist.py
Run
"
Then, in a separate terminal, start host01:
Apply to test_dist.py
Run
"
Finally, start host03:
Apply to test_dist.py
Run
"
Would you like to try this simplified approach? We can make adjustments as needed while keeping the code structured for future plugin development.