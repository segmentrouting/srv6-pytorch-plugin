
### update files in running docker containers:

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

1. docker exec and start pytorch
```
# Start host00 (master)
docker exec clab-sonic-host00 bash -c "RANK=0 python3 /app/test_plugin.py"

# Start host01
docker exec clab-sonic-host01 bash -c "RANK=1 python3 /app/test_plugin.py"

# Start host03
docker exec clab-sonic-host03 bash -c "RANK=2 python3 /app/test_plugin.py"
```

## port freeze?

```
docker exec -it clab-sonic-host00 bash
apt update
apt install netcat
exit
docker exec clab-sonic-host00 bash -c "nc -zv 2001:db8:1001::2 29501"
```