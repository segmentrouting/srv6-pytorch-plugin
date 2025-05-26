import os
import socket
import json
import requests
import torch.distributed as dist
import netifaces
import logging
from route_programmer import RouteProgrammerFactory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NetworkOptimizedDistributed:
    def __init__(self, api_endpoint):
        """
        Initialize with the network API endpoint
        """
        self.api_endpoint = api_endpoint
        self.initialized = False
        self.job_id = os.environ.get('JOB_ID', f"pytorch_job_{os.getpid()}")
        self.collection_name = os.environ.get('TOPOLOGY_COLLECTION', 'network_topology')
        
        # Initialize route programmer - default to Linux
        platform = os.environ.get('ROUTE_PLATFORM', 'linux')
        try:
            self.route_programmer = RouteProgrammerFactory.get_programmer(platform)
            logger.info(f"Initialized {platform} route programmer")
        except Exception as e:
            logger.error(f"Failed to initialize route programmer: {e}")
            logger.warning("Route programming will be disabled")
            self.route_programmer = None
        
    def get_network_interfaces(self):
        """Get the network interfaces of this node"""
        hostname = socket.gethostname()
        interfaces = {}
        
        # Get all network interfaces and their IPs
        for iface in netifaces.interfaces():
            if iface == 'lo':
                continue
            addrs = netifaces.ifaddresses(iface)
            if netifaces.AF_INET in addrs:
                interfaces[iface] = addrs[netifaces.AF_INET][0]['addr']
                
        return {
            "hostname": hostname,
            "interfaces": interfaces
        }
    
    def program_srv6_route(self, destination, sid_list):
        """
        Program an SRv6 route using the route programmer
        """
        if not self.route_programmer:
            logger.error("Route programmer not initialized, cannot program route")
            return False
            
        # Get the backend interface name from environment or default to eth1
        backend_iface = os.environ.get('BACKEND_INTERFACE', 'eth1')
        
        # Convert destination IP to CIDR if it's not already
        if '/' not in destination:
            destination = f"{destination}/32"
            
        # Use the first SID in the list
        if not sid_list:
            logger.error("Empty SID list provided")
            return False
            
        srv6_usid = sid_list[0]
        
        try:
            # Program the route
            success, message = self.route_programmer.program_route(
                destination_prefix=destination,
                srv6_usid=srv6_usid,
                outbound_interface=backend_iface,
                table_id=int(os.environ.get('ROUTE_TABLE_ID', '254'))
            )
            
            if success:
                logger.info(f"Route programming successful: {message}")
            else:
                logger.error(f"Route programming failed: {message}")
                
            return success
        except Exception as e:
            logger.error(f"Exception during route programming: {e}")
            return False
    
    def init_process_group(self, backend='nccl', **kwargs):
        """
        Wrapper around PyTorch's distributed init_process_group that calls the network API
        """
        # Get distributed training info
        rank = int(os.environ.get('RANK', '0'))
        world_size = int(os.environ.get('WORLD_SIZE', '1'))
        master_addr = os.environ.get('MASTER_ADDR', 'localhost')
        
        # Get local IP address
        node_info = self.get_network_interfaces()
        local_ip = None
        backend_iface = os.environ.get('BACKEND_INTERFACE', 'eth1')
        
        for iface, ip in node_info["interfaces"].items():
            if iface == backend_iface:
                local_ip = ip
                break
        
        if not local_ip:
            logger.warning(f"Could not determine local IP address for backend interface {backend_iface}")
            local_ip = list(node_info["interfaces"].values())[0]  # Use first available
            logger.warning(f"Using {local_ip} as fallback")
        
        # Only rank 0 collects information and calls the API
        if rank == 0:
            # In a real setup, we would collect information from all nodes
            # For now, we'll simulate with just this node's info
            gpu_nodes = []
            
            # In a real setup, you would gather this information from all nodes
            # For testing, we'll create dummy entries for all ranks
            for r in range(world_size):
                # For rank 0, use our actual information
                if r == 0:
                    gpu_nodes.append({
                        "hostname": node_info["hostname"],
                        "ip_address": local_ip,
                        "rank": r,
                        "gpu_id": 0  # Assuming one GPU per process for simplicity
                    })
                else:
                    # For other ranks, create dummy entries
                    # In a real setup, you would gather this information
                    last_octet = 10 + r  # Simple IP generation for testing
                    ip_parts = local_ip.split('.')
                    ip_parts[-1] = str(last_octet)
                    dummy_ip = '.'.join(ip_parts)
                    
                    gpu_nodes.append({
                        "hostname": f"node-{r}",
                        "ip_address": dummy_ip,
                        "rank": r,
                        "gpu_id": 0
                    })
            
            # Prepare payload for API
            payload = {
                "job_id": self.job_id,
                "world_size": world_size,
                "master_addr": master_addr,
                "collection_name": self.collection_name,
                "gpu_nodes": gpu_nodes,
                "direction": "outbound"
            }
            
            # Call the network API
            try:
                logger.info(f"Calling network API to optimize NCCL paths")
                # For testing, we'll use the first non-local node as destination
                dest_node = gpu_nodes[1] if len(gpu_nodes) > 1 else None
                
                if dest_node:
                    response = requests.get(
                        f"{self.api_endpoint}/graphs/{self.collection_name}/shortest_path/load",
                        params={
                            'source': f"hosts/{node_info['hostname']}",
                            'destination': f"hosts/{dest_node['hostname']}",
                            'direction': 'outbound'
                        }
                    )
                    response.raise_for_status()
                    
                    # Process the response
                    api_response = response.json()
                    logger.info(f"Network API response: {api_response}")
                    
                    # Store the paths for distribution to other ranks
                    self.optimized_paths = api_response.get("paths", [])
                else:
                    logger.warning("No destination node available for path optimization")
                    self.optimized_paths = []
                
            except Exception as e:
                logger.error(f"Warning: Network API call failed: {e}")
                self.optimized_paths = []
        
        # Initialize PyTorch distributed as normal
        dist.init_process_group(backend=backend, **kwargs)
        
        # After initialization, program the routes
        # In a real setup, rank 0 would distribute the paths to all ranks
        # For now, we'll have rank 0 program all routes
        if rank == 0 and hasattr(self, 'optimized_paths'):
            for path in self.optimized_paths:
                # Only program routes for paths where this node is the source
                if path["source"] == local_ip:
                    self.program_srv6_route(
                        destination=path["destination"],
                        sid_list=path["srv6_sid_list"]
                    )
        
        logger.info(f"Distributed initialization complete for rank {rank}")
        return True 