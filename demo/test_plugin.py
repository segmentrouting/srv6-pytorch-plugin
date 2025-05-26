import os
import time
from network_optimized_distributed import NetworkOptimizedDistributed

def main():
    # Initialize the plugin
    net_dist = NetworkOptimizedDistributed(
        api_endpoint="http://jalapeno-api:8000"
    )
    
    # Simulate a 4-node distributed job
    os.environ['RANK'] = '0'  # This would be different for each container
    os.environ['WORLD_SIZE'] = '4'
    os.environ['MASTER_ADDR'] = 'host-0'  # First container's hostname
    
    # Initialize distributed (this will program the routes)
    net_dist.init_process_group(backend='nccl')
    
    # Wait for routes to be programmed
    time.sleep(2)
    
    # Test the routes with pings
    destinations = [
        '2001:db8:1001:0::2',  # host-1
        '2001:db8:1002:0::2',  # host-2
        '2001:db8:1003:0::2',  # host-3
    ]
    
    for dest in destinations:
        print(f"\nTesting route to {dest}")
        os.system(f"ping -c 3 {dest}")

if __name__ == "__main__":
    main()