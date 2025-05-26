# SRv6 PyTorch Plugin

A PyTorch plugin that integrates with Jalapeno API to optimize network paths for distributed training using SRv6 (Segment Routing over IPv6).

## Overview

This plugin enhances PyTorch's distributed training by:
1. Intercepting NCCL communication setup
2. Querying Jalapeno API for optimized SRv6 paths
3. Programming local SRv6 routes for optimal network paths
4. Enabling distributed training with network-aware routing

## Components

- `network_optimized_distributed.py`: Main plugin that wraps PyTorch's distributed functionality
- `route_programmer.py`: Platform-specific route programming (Linux/VPP)
- `test_basic.py`: Simple test script for basic functionality testing
- `demo/test_plugin.py`: Full demo application using containerlab
- `distributed_app.py`: Example distributed training application

### Prerequisites

- Python 3.8+
- PyTorch
- Access to Jalapeno API
- Linux kernel with SRv6 support (for route programming)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/segment-routing/srv6-pytorch-plugin.git
cd srv6-pytorch-plugin
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your configuration:
```bash
JALAPENO_API_ENDPOINT=http://jalapeno-api:8000
TOPOLOGY_COLLECTION=your-collection-name
BACKEND_INTERFACE=eth0
ROUTE_PLATFORM=linux
ROUTE_TABLE_ID=254
```

5. Test the installation:
```bash
python3 test_basic.py
sudo -E ./venv/bin/python test_basic.py
sudo -E bash -c 'source venv/bin/activate && python test_basic.py'
```

or 
```bash
# Using default values (host00 -> host01)
sudo -E ./venv/bin/python test_basic.py

# Or specify different hosts
sudo -E TEST_SOURCE=hosts/clab-sonic-host02 TEST_DESTINATION=hosts/clab-sonic-host03 ./venv/bin/python test_basic.py
```

This will:
- Initialize the plugin
- Program SRv6 routes
- Test connectivity with a ping
- 
Note: For full functionality including SRv6 route programming, your system needs:
- Linux kernel with SRv6 support
- `iproute2` package installed
- Appropriate permissions to program routes

### Basic Usage

```python
from network_optimized_distributed import NetworkOptimizedDistributed

# Initialize with Jalapeno API endpoint
net_dist = NetworkOptimizedDistributed(
    api_endpoint=os.getenv('JALAPENO_API_ENDPOINT')
)

# Initialize distributed training with network optimization
net_dist.init_process_group(backend="nccl")
```

## Environment Variables

- `JALAPENO_API_ENDPOINT`: URL of the Jalapeno API
- `TOPOLOGY_COLLECTION`: Name of the topology collection in Jalapeno
- `BACKEND_INTERFACE`: Network interface for SRv6 routes (default: eth1)
- `ROUTE_PLATFORM`: Route programming platform (linux/vpp)
- `ROUTE_TABLE_ID`: Routing table ID (default: 254)
- `TEST_DESTINATION`: IPv6 address for testing connectivity (used by test_basic.py)

## Demo

The `demo/` directory contains a complete example using containerlab to simulate a network topology with SONiC switches. See `demo/readme.md` for detailed instructions.

## Kubernetes Deployment

The `k8s/` directory contains Kubernetes deployment files for running distributed training jobs with network optimization.

## Application flow

[PyTorch Distributed Training]
        ↓
[NetworkOptimizedDistributed Plugin]
        ↓
1. Intercepts NCCL initialization
2. Collects node information (IP, hostname)
        ↓
[Jalapeno API]
        ↓
3. Queries /graphs/{collection_name}/shortest_path/load
4. Gets back SRv6 path information
        ↓
[Route Programmer]
        ↓
5. Programs local SRv6 routes
        ↓
[NCCL Communication]

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

