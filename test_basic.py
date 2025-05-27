#!/usr/bin/env python3
import os
import time
import json
import signal
import requests
from dotenv import load_dotenv
from network_optimized_distributed import NetworkOptimizedDistributed

# Load environment variables
load_dotenv()

def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")

def print_route_info(route_data):
    """Print formatted SRv6 route information."""
    print("\nSRv6 Route Information:")
    print("-" * 50)
    print(f"Destination: {route_data.get('destination', 'N/A')}")
    print(f"Next Hop: {route_data.get('next_hop', 'N/A')}")
    print(f"Segment List: {route_data.get('segment_list', [])}")
    print(f"Interface: {route_data.get('interface', 'N/A')}")
    print(f"Table ID: {route_data.get('table_id', 'N/A')}")
    print("-" * 50)
    
    # Print the equivalent ip route command
    if route_data.get('segment_list'):
        segments = ','.join(route_data['segment_list'])
        print("\nEquivalent ip route command:")
        print(f"ip -6 route add {route_data['destination']} encap seg6 mode encap segs {segments} dev {route_data['interface']} table {route_data['table_id']}")

def main():
    # Set required environment variables
    os.environ['RANK'] = os.getenv('RANK', '0')
    os.environ['WORLD_SIZE'] = os.getenv('WORLD_SIZE', '2')
    os.environ['MASTER_ADDR'] = os.getenv('MASTER_ADDR', 'localhost')
    os.environ['MASTER_PORT'] = os.getenv('MASTER_PORT', '29500')
    os.environ['BACKEND_INTERFACE'] = os.getenv('BACKEND_INTERFACE', 'eth0')
    os.environ['TOPOLOGY_COLLECTION'] = os.getenv('TOPOLOGY_COLLECTION')
    os.environ['TEST_SOURCE'] = os.getenv('TEST_SOURCE', 'hosts/clab-sonic-host00')
    os.environ['TEST_DESTINATION'] = os.getenv('TEST_DESTINATION', 'hosts/clab-sonic-host01')
    
    if not os.environ['TOPOLOGY_COLLECTION']:
        print("Error: TOPOLOGY_COLLECTION environment variable is required")
        return
    
    # Initialize the plugin with API endpoint from .env
    net_dist = NetworkOptimizedDistributed(
        api_endpoint=os.getenv('JALAPENO_API_ENDPOINT')
    )
    
    print("Initializing distributed training with network optimization...")
    print(f"Using interface: {os.environ['BACKEND_INTERFACE']}")
    print(f"Master address: {os.environ['MASTER_ADDR']}:{os.environ['MASTER_PORT']}")
    print(f"Test source: {os.environ['TEST_SOURCE']}")
    print(f"Test destination: {os.environ['TEST_DESTINATION']}")
    
    try:
        # Set a 10-second timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(10)
        
        # Call the API directly
        test_source = os.environ['TEST_SOURCE']
        test_dest = os.environ['TEST_DESTINATION']
        collection_name = os.environ['TOPOLOGY_COLLECTION']
        
        response = requests.get(
            f"{net_dist.api_endpoint}/graphs/{collection_name}/shortest_path/load",
            params={
                'source': test_source,
                'destination': test_dest,
                'direction': 'outbound'
            }
        )
        response.raise_for_status()
        
        # Process the response
        api_response = response.json()
        print(f"\nAPI Response: {api_response}")
        
        if api_response.get('found'):
            # Extract SRv6 information from the path
            srv6_data = api_response.get('srv6_data', {})
            print(f"\nSRv6 Data: {srv6_data}")
            # Get the destination IP from the API response
            # In a real environment, this would come from the API
            # For now, we'll use a placeholder IPv6 address
            dest_ip = "2001:db8:1002::"  # This should come from the API
            
            route_info = {
                'destination': f"{dest_ip}/64",  # Add prefix length
                'next_hop': srv6_data.get('srv6_sid_list', [])[0] if srv6_data.get('srv6_sid_list') else 'N/A',
                'segment_list': srv6_data.get('srv6_sid_list', []),
                'interface': os.environ['BACKEND_INTERFACE'],
                'table_id': os.environ.get('ROUTE_TABLE_ID', '254')
            }
            
            # Always print the route information
            print_route_info(route_info)
            
            
            # Try to program the route if route programmer is available
            if net_dist.route_programmer:
                try:
                    net_dist.program_srv6_route(
                        destination=route_info['destination'],
                        sid_list=route_info['segment_list']
                    )
                except Exception as e:
                    print(f"\nWarning: Route programming failed: {str(e)}")
                    print("The route information above shows what would have been programmed.")
        else:
            print("\nNo route information available. Check API connection and topology collection.")
        
        # Disable the alarm
        signal.alarm(0)
        print("\nTest completed. Check the logs for additional details.")
        
    except TimeoutError:
        print("\nOperation timed out after 10 seconds.")
        print("The route information above shows what would have been programmed.")
    except Exception as e:
        print(f"\nError during initialization: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. Ensure all required environment variables are set")
        print("2. Check API endpoint connectivity")
        print("3. Verify interface name is correct")
        print("4. For route programming, run with sudo -E to preserve environment")

if __name__ == "__main__":
    main() 