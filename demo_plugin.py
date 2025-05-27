import os
import logging
from dist_setup import init_distributed, get_all_nodes
from network_programmer import NetworkProgrammer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DemoPlugin:
    """Simple wrapper for the demo that combines distributed setup and network programming"""
    
    def __init__(self, api_endpoint):
        """Initialize with the network API endpoint"""
        self.api_endpoint = api_endpoint
        self.network_programmer = NetworkProgrammer(api_endpoint)
    
    def init_process_group(self, backend='nccl', **kwargs):
        """Initialize distributed training and program routes"""
        # First, initialize PyTorch distributed
        if not init_distributed():
            logger.error("Failed to initialize PyTorch distributed")
            return False
        
        try:
            # Get information about all nodes
            nodes = get_all_nodes()
            logger.info(f"Found {len(nodes)} nodes:")
            for node in nodes:
                logger.info(f"  Rank {node['rank']}: {node['hostname']} ({node['ip_address']})")
            
            # Program routes
            logger.info("Programming network routes...")
            self.network_programmer.program_all_routes(nodes)
            
            return True
            
        except Exception as e:
            logger.error(f"Error during initialization: {e}")
            return False 