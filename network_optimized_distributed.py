import os
import socket
import json
import requests
import torch.distributed as dist
import netifaces
import logging
from route_programmer import RouteProgrammerFactory
import torch
import datetime

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
        self.last_api_response = None  # Store the last API response
        
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
        backend_iface = os.environ.get('BACKEND_INTERFACE', 'eth1')
        
        logger.info(f"Initializing distributed process group:")
        logger.info(f"  Rank: {rank}")
        logger.info(f"  World Size: {world_size}")
        logger.info(f"  Master Address: {master_addr}")
        logger.info(f"  Backend: {backend}")
        logger.info(f"  Network Interface: {backend_iface}")
        
        # Get local IPv6 address for the backend interface
        node_info = self.get_network_interfaces()
        local_ip = None
        
        # Get IPv6 address from the backend interface
        addrs = netifaces.ifaddresses(backend_iface)
        if netifaces.AF_INET6 in addrs:
            for addr in addrs[netifaces.AF_INET6]:
                if 'addr' in addr and not addr['addr'].startswith('fe80::'):  # Skip link-local addresses
                    local_ip = addr['addr']
                    break
        
        if not local_ip:
            logger.error(f"Could not determine IPv6 address for backend interface {backend_iface}")
            raise ValueError(f"Backend interface {backend_iface} has no valid IPv6 address")
        
        logger.info(f"Local IPv6 address on {backend_iface}: {local_ip}")
        
        # Set environment variables for PyTorch distributed
        os.environ['NCCL_IB_DISABLE'] = '1'  # Disable InfiniBand
        os.environ['NCCL_SOCKET_IFNAME'] = backend_iface  # Set network interface
        os.environ['GLOO_SOCKET_IFNAME'] = backend_iface  # Set network interface for Gloo backend
        
        # Initialize PyTorch distributed first so we can use it for gathering node info
        logger.info("Calling torch.distributed.init_process_group...")
        try:
            dist.init_process_group(
                backend=backend,
                init_method=f"tcp://[{master_addr}]:{os.environ.get('MASTER_PORT', '29500')}",  # IPv6 format
                world_size=world_size,
                rank=rank,
                timeout=datetime.timedelta(seconds=30)  # Add timeout
            )
            logger.info("PyTorch distributed initialization successful")
        except Exception as e:
            logger.error(f"Failed to initialize PyTorch distributed: {e}")
            raise
        
        # Each rank prepares its node information
        node_info = {
            'hostname': f"clab-sonic-host{rank:02d}",
            'ip_address': local_ip,
            'rank': rank
        }
        
        logger.info(f"Preparing node information: {node_info}")
        
        # Convert node info to tensor for all_gather
        node_info_tensor = torch.tensor(bytearray(json.dumps(node_info).encode()))
        node_info_size = torch.tensor([len(node_info_tensor)])
        
        # Gather sizes from all ranks
        logger.info("Gathering node information sizes...")
        size_list = [torch.zeros_like(node_info_size) for _ in range(world_size)]
        dist.all_gather(size_list, node_info_size)
        
        # Calculate max size and pad tensors
        max_size = max(size.item() for size in size_list)
        padded_tensor = torch.zeros(max_size, dtype=torch.uint8)
        padded_tensor[:len(node_info_tensor)] = node_info_tensor
        
        # Gather all node information
        logger.info("Gathering node information from all ranks...")
        gathered_tensors = [torch.zeros_like(padded_tensor) for _ in range(world_size)]
        dist.all_gather(gathered_tensors, padded_tensor)
        
        # Convert gathered tensors back to node info
        all_nodes = []
        for tensor, size in zip(gathered_tensors, size_list):
            node_info_bytes = tensor[:size.item()].tolist()
            node_info_str = bytes(node_info_bytes).decode()
            all_nodes.append(json.loads(node_info_str))
        
        # Sort nodes by rank to ensure consistent order
        all_nodes.sort(key=lambda x: x['rank'])
        logger.info(f"Gathered node information: {all_nodes}")
        
        # Only rank 0 makes API calls
        if rank == 0:
            # Generate all possible source/destination pairs
            all_pairs = []
            for i in range(world_size):
                for j in range(world_size):
                    if i != j:  # Skip self-pairs
                        all_pairs.append({
                            'source': f"hosts/{all_nodes[i]['hostname']}",
                            'destination': f"hosts/{all_nodes[j]['hostname']}"
                        })
            
            logger.info(f"Generated source/destination pairs: {all_pairs}")
            
            # Store all API responses
            self.all_api_responses = {}
            
            # Call the network API for each pair
            for pair in all_pairs:
                try:
                    logger.info(f"Calling network API for {pair['source']} -> {pair['destination']}")
                    response = requests.get(
                        f"{self.api_endpoint}/graphs/{self.collection_name}/shortest_path/load",
                        params={
                            'source': pair['source'],
                            'destination': pair['destination'],
                            'direction': 'outbound'
                        }
                    )
                    response.raise_for_status()
                    
                    # Process the response
                    api_response = response.json()
                    logger.info(f"Network API response for {pair['source']} -> {pair['destination']}: {api_response}")
                    
                    # Store the API response
                    pair_key = f"{pair['source']}_{pair['destination']}"
                    self.all_api_responses[pair_key] = api_response
                    
                except Exception as e:
                    logger.error(f"Warning: Network API call failed for {pair['source']} -> {pair['destination']}: {e}")
                    self.all_api_responses[pair_key] = None
        
        # Broadcast the API responses to all ranks
        if rank == 0:
            # Convert API responses to bytes for broadcasting
            api_responses_bytes = json.dumps(self.all_api_responses).encode() if self.all_api_responses else b''
            api_responses_size = len(api_responses_bytes)
            logger.info(f"Broadcasting API responses (size: {api_responses_size} bytes)")
        else:
            api_responses_bytes = None
            api_responses_size = None
        
        try:
            # Broadcast the size first
            size_tensor = torch.tensor([api_responses_size if api_responses_size is not None else 0], dtype=torch.long)
            dist.broadcast(size_tensor, src=0)
            api_responses_size = size_tensor.item()
            logger.info(f"Broadcast size: {api_responses_size}")
            
            # Allocate buffer for receiving
            if rank != 0:
                api_responses_bytes = bytearray(api_responses_size)
            
            # Broadcast the actual data
            if api_responses_size > 0:
                logger.info("Broadcasting API response data...")
                dist.broadcast_object_list([api_responses_bytes], src=0)
                
                # Convert back to dictionary
                if rank != 0:
                    self.all_api_responses = json.loads(api_responses_bytes.decode()) if api_responses_bytes else {}
                    logger.info(f"Received API responses: {self.all_api_responses}")
            else:
                if rank != 0:
                    self.all_api_responses = {}
                
        except Exception as e:
            logger.error(f"Error during API response broadcast: {e}")
            if rank != 0:
                self.all_api_responses = {}
        
        # After initialization, program the routes for this rank
        # Each rank programs routes where it is the source
        current_host = f"hosts/{node_info['hostname']}"
        logger.info(f"Programming routes for {current_host}")
        
        for pair_key, api_response in self.all_api_responses.items():
            if api_response and api_response.get('found'):
                source, destination = pair_key.split('_')
                if source == current_host:
                    srv6_data = api_response.get('srv6_data', {})
                    if srv6_data:
                        # Extract destination network from the destination host
                        dest_hostname = destination.split('/')[-1]
                        dest_num = int(dest_hostname.split('-')[-1])
                        dest_ip = f"2001:db8:100{dest_num}::/64"
                        
                        try:
                            logger.info(f"Programming route to {destination} ({dest_ip})")
                            self.program_srv6_route(
                                destination=dest_ip,
                                sid_list=[srv6_data['srv6_usid']]
                            )
                        except Exception as e:
                            logger.error(f"Error programming route to {destination}: {e}")
        
        logger.info(f"Distributed initialization complete for rank {rank}")
        return True 