# SRv6 PyTorch Plugin

A PyTorch plugin that integrates with Jalapeno API to optimize network paths for distributed training using SRv6

## Overview

This plugin enhances PyTorch's distributed training by:
1. Intercepting NCCL communication setup
2. Querying Jalapeno API for optimized SRv6 paths
3. Programming local SRv6 routes for optimal network paths
4. Enabling distributed training with network-aware routing

## Components

- `srv6_plugin.py`: Main plugin that wraps PyTorch's distributed functionality
- `route_programmer.py`: Platform-specific route programming (Linux/VPP)
- `controller.py`: Network controller for managing routes and API interactions
- `dist_setup.py`: Distributed training setup utilities
- `demo/test_dist.py`: Full demo application using containerlab

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
BACKEND_INTERFACE=eth1
ROUTE_PLATFORM=linux
ROUTE_TABLE_ID=254
HOSTS=host00,host01,host02  # Comma-separated list of hostnames
```

### Basic Usage

```python
from srv6_plugin import DemoPlugin

# Initialize with Jalapeno API endpoint
plugin = DemoPlugin(
    api_endpoint=os.getenv('JALAPENO_API_ENDPOINT')
)

# Initialize distributed training with network optimization
plugin.init_process_group()
```

## Environment Variables

- `JALAPENO_API_ENDPOINT`: URL of the Jalapeno API
- `TOPOLOGY_COLLECTION`: Name of the topology collection in Jalapeno
- `BACKEND_INTERFACE`: Network interface for SRv6 routes (default: eth1)
- `ROUTE_PLATFORM`: Route programming platform (linux/vpp)
- `ROUTE_TABLE_ID`: Routing table ID (default: 254)
- `HOSTS`: Comma-separated list of hostnames for distributed training
- `RANK`: Node rank in distributed training (0-based)
- `WORLD_SIZE`: Total number of nodes in distributed training
- `MASTER_ADDR`: IP address of the master node
- `MASTER_PORT`: Port for distributed training communication

## Demo

The `demo/` directory contains a complete example using containerlab to simulate a network topology with SONiC switches. See `demo/readme.md` for detailed instructions.

## Application flow

[PyTorch Distributed Training]
        ↓
[DemoPlugin]
        ↓
1. Initializes distributed process group
2. Collects node information from environment
        ↓
[Network Controller]
        ↓
3. Queries Jalapeno API for optimized paths
4. Gets back SRv6 path information
        ↓
[Route Programmer]
        ↓
5. Programs local SRv6 routes
        ↓
[Distributed Training Communication]

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

