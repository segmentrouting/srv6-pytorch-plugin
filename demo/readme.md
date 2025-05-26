
1. Build the container image
```
docker build -t pytorch-srv6-demo:latest .
```

2. Deploy the topology
```
containerlab deploy -t topology.yml
```

3. Configure SONiC switches for SRv6


4. Start the test on each host
docker exec host-0 python3 /app/test_plugin.py
docker exec host-1 python3 /app/test_plugin.py
docker exec host-2 python3 /app/test_plugin.py
docker exec host-3 python3 /app/test_plugin.py