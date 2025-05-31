## 2nd try

1. build
```
docker build -t pytorch-srv6-plugin  .
```

2. deploy topology
```
sudo clab deploy -t topology.yaml
```

3. update files:
```
docker cp demo/.env clab-sonic-host00:/app/
docker cp demo/test_plugin.py clab-sonic-host00:/app/
docker cp srv6_plugin.py clab-sonic-host00:/app/
docker cp dist_setup.py clab-sonic-host00:/app/
docker cp controller.py clab-sonic-host00:/app/
docker cp route_programmer.py clab-sonic-host00:/app/

docker cp demo/.env clab-sonic-host01:/app/
docker cp demo/test_plugin.py clab-sonic-host01:/app/
docker cp srv6_plugin.py clab-sonic-host01:/app/
docker cp dist_setup.py clab-sonic-host01:/app/
docker cp controller.py clab-sonic-host01:/app/
docker cp route_programmer.py clab-sonic-host01:/app/

docker cp demo/.env clab-sonic-host02:/app/
docker cp demo/test_plugin.py clab-sonic-host02:/app/
docker cp srv6_plugin.py clab-sonic-host02:/app/
docker cp dist_setup.py clab-sonic-host02:/app/
docker cp controller.py clab-sonic-host02:/app/
docker cp route_programmer.py clab-sonic-host02:/app/

docker cp demo/.env clab-sonic-host03:/app/
docker cp demo/test_plugin.py clab-sonic-host03:/app/
docker cp srv6_plugin.py clab-sonic-host03:/app/
docker cp dist_setup.py clab-sonic-host03:/app/
docker cp controller.py clab-sonic-host03:/app/
docker cp route_programmer.py clab-sonic-host03:/app/
```

4. docker exec and start pytorch
```
# Start host00 (master)
docker exec clab-sonic-host00 bash -c "RANK=0 python3 /app/test_plugin.py"

# Start host01
docker exec clab-sonic-host01 bash -c "RANK=1 python3 /app/test_plugin.py"

# Start host03
docker exec clab-sonic-host03 bash -c "RANK=2 python3 /app/test_plugin.py"
```