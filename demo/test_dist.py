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

def get_all_nodes():
    """Get list of all nodes in the distributed setup from environment variables"""
    hosts = os.environ.get('HOSTS', '').split(',')
    nodes = []
    for i, hostname in enumerate(hosts):
        if hostname:  # Skip empty strings
            nodes.append({
                'rank': i,
                'hostname': hostname.strip()  # Remove any whitespace
            })
    return nodes

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
        # Get all nodes from distributed setup
        nodes = get_all_nodes()
        
        # Get current node's hostname
        current_host = os.environ.get('HOSTNAME', f"host{rank:02d}")
        
        # Determine IP version from MASTER_ADDR
        master_addr = os.environ.get('MASTER_ADDR', '')
        is_ipv6 = ':' in master_addr
        
        # Find ping destination - ping the next host in the list
        ping_destination = None
        for i, node in enumerate(nodes):
            if node['hostname'] == current_host:
                # Get the next host in the list (wrap around to first if at end)
                next_node = nodes[(i + 1) % len(nodes)]
                # Get the IP address from the API response
                api_response = plugin.network_programmer.get_route_info(
                    f"hosts/{current_host}",
                    f"hosts/{next_node['hostname']}"
                )
                if api_response and 'destination_info' in api_response:
                    dest_info = api_response['destination_info']
                    if is_ipv6:
                        ping_destination = dest_info.get('ipv6_address')
                    else:
                        ping_destination = dest_info.get('ipv4_address')
                break
        
        if ping_destination:
            print(f"Pinging {ping_destination}")
            ping_cmd = "ping6" if is_ipv6 else "ping"
            os.system(f"{ping_cmd} -c 5 {ping_destination}")
        else:
            print("Could not determine ping destination")
        
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