import os
import time
import socket
from dotenv import load_dotenv
from network_optimized_distributed import NetworkOptimizedDistributed

# Load environment variables
load_dotenv()

def test_tcp_connectivity(host, port, timeout=5):
    """Test TCP connectivity to a host:port"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"Error testing connectivity to {host}:{port}: {e}")
        return False

def print_route_info(destination, srv6_data, interface, table_id=254):
    """Print formatted route information"""
    print("\nSRv6 Route Information:")
    print("-" * 50)
    print(f"Destination: {destination}")
    print(f"Next Hop: {srv6_data['srv6_usid']}")
    print(f"uSID: {srv6_data['srv6_usid']}")
    print(f"Interface: {interface}")
    print(f"Table ID: {table_id}")
    print("-" * 50)
    print("\nEquivalent ip route command:")
    print(f"ip -6 route add {destination} encap seg6 mode encap segs {srv6_data['srv6_usid']} dev {interface} table {table_id}")

def main():
    # Set environment variables for distributed setup
    os.environ['RANK'] = os.getenv('RANK', '0')
    os.environ['WORLD_SIZE'] = os.getenv('WORLD_SIZE', '3')  # Using 3 hosts
    
    # Get the master IP address based on rank
    rank = int(os.environ['RANK'])
    if rank == 0:
        master_ip = '172.20.6.224'  # host00 IP
    elif rank == 1:
        master_ip = '172.20.6.225'  # host01 IP
    else:
        master_ip = '172.20.6.227'  # host03 IP
    
    os.environ['MASTER_ADDR'] = master_ip
    os.environ['MASTER_PORT'] = os.getenv('MASTER_PORT', '29500')
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
    
    # Test TCP connectivity between nodes
    print("\nTesting TCP connectivity:")
    print("-" * 50)
    master_port = int(os.environ['MASTER_PORT'])
    
    # Test connectivity to all nodes
    nodes = {
        'host00': '172.20.6.224',
        'host01': '172.20.6.225',
        'host03': '172.20.6.227'
    }
    
    for node_name, node_ip in nodes.items():
        if node_ip != master_ip:  # Don't test self
            print(f"Testing connection to {node_name} ({node_ip}):{master_port}")
            if test_tcp_connectivity(node_ip, master_port):
                print(f"✓ Successfully connected to {node_name}")
            else:
                print(f"✗ Failed to connect to {node_name}")
    print("-" * 50)
    
    # Set test source and destination based on rank
    if rank == 0:
        os.environ['TEST_SOURCE'] = 'hosts/clab-sonic-host00'
        os.environ['TEST_DESTINATION'] = 'hosts/clab-sonic-host01'
        ping_destination = '2001:db8:1001:0::2'  # host-1 IPv6
    elif rank == 1:
        os.environ['TEST_SOURCE'] = 'hosts/clab-sonic-host01'
        os.environ['TEST_DESTINATION'] = 'hosts/clab-sonic-host03'
        ping_destination = '2001:db8:1003:0::2'  # host-3 IPv6
    else:
        os.environ['TEST_SOURCE'] = 'hosts/clab-sonic-host03'
        os.environ['TEST_DESTINATION'] = 'hosts/clab-sonic-host00'
        ping_destination = '2001:db8:1000:0::2'  # host-0 IPv6
    
    print(f"\nTest Configuration:")
    print("-" * 50)
    print(f"Test source: {os.environ['TEST_SOURCE']}")
    print(f"Test destination: {os.environ['TEST_DESTINATION']}")
    print(f"Ping destination: {ping_destination}")
    print("-" * 50)
    
    # Initialize the plugin with API endpoint from .env
    api_endpoint = os.getenv('JALAPENO_API_ENDPOINT')
    if not api_endpoint:
        print("Error: JALAPENO_API_ENDPOINT environment variable not set")
        return
        
    print(f"\nInitializing distributed training with network optimization...")
    net_dist = NetworkOptimizedDistributed(api_endpoint=api_endpoint)
    
    try:
        print("\nInitializing PyTorch distributed...")
        # Initialize distributed (this will get route information)
        #  net_dist.init_process_group(backend='nccl')
        net_dist.init_process_group(backend='gloo')  # Using gloo backend for CPU testing
        print("PyTorch distributed initialization complete")
        
        # Wait for route information to be processed
        print("\nWaiting for route information...")
        time.sleep(2)
        
        # Get route information from the API responses
        if hasattr(net_dist, 'all_api_responses'):
            current_host = f"hosts/clab-sonic-host{rank:02d}"
            print(f"\nRoute information for {current_host}:")
            print("-" * 50)
            
            for pair_key, api_response in net_dist.all_api_responses.items():
                if api_response and api_response.get('found'):
                    source, destination = pair_key.split('_')
                    if source == current_host:
                        # Extract destination network from the destination host
                        dest_num = int(destination.split('-')[-1])
                        dest_ip = f"2001:db8:100{dest_num}::/64"
                        
                        print(f"\nRoute to {destination}:")
                        print_route_info(
                            destination=dest_ip,
                            srv6_data=api_response.get('srv6_data', {}),
                            interface=os.environ['BACKEND_INTERFACE'],
                            table_id=os.environ.get('ROUTE_TABLE_ID', '254')
                        )
        else:
            print("\nNo route information available. Check API connection and topology collection.")
        
        # Test connectivity using IPv6 address
        print(f"\nTesting connectivity to {ping_destination}")
        os.system(f"ping6 -c 3 {ping_destination}")
        
        print("\nTest completed. Check the logs for additional details.")
        
    except Exception as e:
        print(f"\nError during initialization: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. Ensure all required environment variables are set")
        print("2. Check API endpoint connectivity")
        print("3. Verify interface name is correct")
        print("4. Check containerlab network connectivity")
        print("5. Verify all nodes can reach the master IP address")
        print("6. Check if the master port is available and not blocked")
        print("7. Verify all nodes are running with correct RANK values")
        print("8. Check if the master port (29500) is not in use")
        print("9. Verify TCP connectivity between nodes on port 29500")

if __name__ == "__main__":
    main()