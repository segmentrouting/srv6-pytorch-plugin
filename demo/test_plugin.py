import os
import time
from dotenv import load_dotenv
from network_optimized_distributed import NetworkOptimizedDistributed

# Load environment variables
load_dotenv()

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
    os.environ['MASTER_ADDR'] = os.getenv('MASTER_ADDR', 'clab-sonic-host00')
    os.environ['MASTER_PORT'] = os.getenv('MASTER_PORT', '29500')
    os.environ['BACKEND_INTERFACE'] = os.getenv('BACKEND_INTERFACE', 'eth1')
    os.environ['TOPOLOGY_COLLECTION'] = os.getenv('TOPOLOGY_COLLECTION')
    
    # Set test source and destination based on rank
    rank = int(os.environ['RANK'])
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
    
    # Initialize the plugin with API endpoint from .env
    net_dist = NetworkOptimizedDistributed(
        api_endpoint=os.getenv('JALAPENO_API_ENDPOINT')
    )
    
    print(f"\nInitializing distributed training with network optimization...")
    print(f"Rank: {os.environ['RANK']}")
    print(f"Using interface: {os.environ['BACKEND_INTERFACE']}")
    print(f"Master address: {os.environ['MASTER_ADDR']}:{os.environ['MASTER_PORT']}")
    print(f"Test source: {os.environ['TEST_SOURCE']}")
    print(f"Test destination: {os.environ['TEST_DESTINATION']}")
    print(f"Ping destination: {ping_destination}")
    
    try:
        # Initialize distributed (this will get route information)
        net_dist.init_process_group(backend='nccl')
        
        # Wait for route information to be processed
        time.sleep(2)
        
        # Get and print route information
        route_info = net_dist.get_route_info()
        if route_info:
            # Extract SRv6 information from the path
            srv6_data = route_info.get('srv6_data', {})
            dest_ip = route_info.get('destination', '2001:db8:1002::/64')
            
            print_route_info(
                destination=dest_ip,
                srv6_data=srv6_data,
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

if __name__ == "__main__":
    main()