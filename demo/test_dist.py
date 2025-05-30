import os
import time
import atexit
import torch.distributed as dist
from dotenv import load_dotenv
from srv6_plugin import DemoPlugin

# Load environment variables
load_dotenv()

def cleanup():
    """Cleanup function to destroy distributed process group"""
    if dist.is_initialized():
        dist.destroy_process_group()

# Register cleanup function
atexit.register(cleanup)

def main():
    # Set environment variables for distributed setup
    os.environ['RANK'] = os.getenv('RANK', '0')
    os.environ['WORLD_SIZE'] = os.getenv('WORLD_SIZE', '3')  # Using 3 hosts
    
    # Get the master IP address based on rank
    rank = int(os.environ['RANK'])
    # Always use host00 as the master
    master_ip = '2001:db8:1000::2'  # host00 IPv6
    
    os.environ['MASTER_ADDR'] = master_ip
    os.environ['MASTER_PORT'] = os.getenv('MASTER_PORT', '29501')
    os.environ['BACKEND_INTERFACE'] = os.getenv('BACKEND_INTERFACE', 'eth1')
    os.environ['TOPOLOGY_COLLECTION'] = os.getenv('TOPOLOGY_COLLECTION')
    
    # Print all environment variables for debugging
    print("\nEnvironment Variables:")
    print("-" * 50)
    print(f"RANK: {os.environ['RANK']}")
    print(f"WORLD_SIZE: {os.environ['WORLD_SIZE']}")
    print(f"MASTER_ADDR: {os.environ['MASTER_ADDR']}")
    print(f"MASTER_PORT: {os.environ['MASTER_PORT']}")
    print(f"BACKEND_INTERFACE: {os.environ['BACKEND_INTERFACE']}")
    print(f"TOPOLOGY_COLLECTION: {os.environ['TOPOLOGY_COLLECTION']}")
    print(f"JALAPENO_API_ENDPOINT: {os.getenv('JALAPENO_API_ENDPOINT')}")
    print("-" * 50)
    
    try:
        # Initialize the demo plugin
        api_endpoint = os.getenv('JALAPENO_API_ENDPOINT')
        if not api_endpoint:
            print("Error: JALAPENO_API_ENDPOINT environment variable not set")
            return
        
        print("\nInitializing demo plugin...")
        plugin = DemoPlugin(api_endpoint)
        
        # Initialize distributed training and program routes
        print("\nInitializing distributed training and programming routes...")
        if not plugin.init_process_group():
            print("Failed to initialize distributed training")
            return
        
        # Test connectivity
        print("\nTesting connectivity...")
        if rank == 0:
            ping_destination = '2001:db8:1001::2'  # host-1 IPv6
        elif rank == 1:
            ping_destination = '2001:db8:1003::2'  # host-3 IPv6
        else:
            ping_destination = '2001:db8:1000::2'  # host-0 IPv6
        
        # print(f"Pinging {ping_destination}")
        # os.system(f"ping6 -c 5 {ping_destination}")
        
        print("\nTest completed successfully!")
        
    except Exception as e:
        print(f"\nError during test: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. Ensure all required environment variables are set")
        print("2. Check API endpoint connectivity")
        print("3. Verify interface name is correct")
        print("4. Check containerlab network connectivity")
        print("5. Verify all nodes can reach the master IP address")
        print("6. Check if the master port is available and not blocked")
    finally:
        # Ensure cleanup happens even if there's an error
        cleanup()

if __name__ == "__main__":
    main() 