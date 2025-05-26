import os
import time
from dotenv import load_dotenv
from network_optimized_distributed import NetworkOptimizedDistributed

# Load environment variables
load_dotenv()

def main():
    # Initialize the plugin with API endpoint from .env
    net_dist = NetworkOptimizedDistributed(
        api_endpoint=os.getenv('JALAPENO_API_ENDPOINT')
    )
    
    # Set environment variables for distributed setup
    # Using 3 hosts instead of 4
    os.environ['RANK'] = '0'  # This would be different for each container
    os.environ['WORLD_SIZE'] = '3'  # Changed to 3 hosts
    os.environ['MASTER_ADDR'] = 'clab-sonic-host00'  # Updated to match containerlab hostname
    os.environ['TOPOLOGY_COLLECTION'] = os.getenv('TOPOLOGY_COLLECTION')
    
    # Initialize distributed (this will program the routes)
    net_dist.init_process_group(backend='nccl')
    
    # Wait for routes to be programmed
    time.sleep(2)
    
    # Test the routes with pings to the other hosts in the job
    destinations = [
        '2001:db8:1001:0::2',  # host-1 IPv6
        '2001:db8:1003:0::2',  # host-3 IPv6 (skipping host-2)
    ]
    
    for dest in destinations:
        print(f"\nTesting route to {dest}")
        os.system(f"ping6 -c 3 {dest}")

if __name__ == "__main__":
    main()