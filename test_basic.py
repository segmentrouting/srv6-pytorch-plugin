#!/usr/bin/env python3
import os
import time
import json
from dotenv import load_dotenv
from network_optimized_distributed import NetworkOptimizedDistributed

# Load environment variables
load_dotenv()

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
    # Initialize the plugin with API endpoint from .env
    net_dist = NetworkOptimizedDistributed(
        api_endpoint=os.getenv('JALAPENO_API_ENDPOINT')
    )
    
    # Set environment variables for distributed setup
    os.environ['RANK'] = '0'
    os.environ['WORLD_SIZE'] = '2'  # Testing with 2 nodes
    os.environ['MASTER_ADDR'] = 'localhost'
    os.environ['TOPOLOGY_COLLECTION'] = os.getenv('TOPOLOGY_COLLECTION')
    
    print("Initializing distributed training with network optimization...")
    
    # Initialize distributed (this will get route information)
    net_dist.init_process_group(backend='nccl')
    
    # Wait for route information to be processed
    time.sleep(2)
    
    # Get and print route information
    route_info = net_dist.get_route_info()
    if route_info:
        print_route_info(route_info)
    else:
        print("\nNo route information available. Check API connection and topology collection.")
    
    # Test connectivity if TEST_DESTINATION is set
    test_destination = os.getenv('TEST_DESTINATION')
    if test_destination:
        print(f"\nTesting connectivity to {test_destination}")
        os.system(f"ping6 -c 3 {test_destination}")
    
    print("\nTest completed. Check the logs for additional details.")

if __name__ == "__main__":
    main() 