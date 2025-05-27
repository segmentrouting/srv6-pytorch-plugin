import os
import time
import socket
import netifaces
from dotenv import load_dotenv
from network_optimized_distributed import NetworkOptimizedDistributed

# Load environment variables
load_dotenv()

def test_tcp_connectivity(host, port, timeout=5):
    """Test TCP connectivity to a host:port"""
    print(f"  Testing connection to {host}:{port}")
    print(f"  Creating IPv6 socket...")
    try:
        # Create IPv6 socket
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(timeout)
        print(f"  Attempting to connect...")
        result = sock.connect_ex((host, port))
        print(f"  connect_ex result: {result}")
        if result != 0:
            print(f"  Connection failed with error code: {result}")
            print(f"  Error meaning: {socket.errorTab.get(result, 'Unknown error')}")
        sock.close()
        return result == 0
    except Exception as e:
        print(f"  Error testing connectivity to {host}:{port}: {e}")
        print(f"  Error type: {type(e)}")
        return False

def check_port_status(port):
    """Check if a port is in use"""
    try:
        # Try both IPv4 and IPv6
        for family in (socket.AF_INET, socket.AF_INET6):
            sock = socket.socket(family, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(1)
            try:
                sock.bind(('::' if family == socket.AF_INET6 else '0.0.0.0', port))
                sock.close()
                return False  # Port is available
            except socket.error as e:
                if e.errno == 98:  # Address already in use
                    return True
                print(f"Error checking port {port} with family {family}: {e}")
            finally:
                sock.close()
        return False
    except Exception as e:
        print(f"Error checking port {port}: {e}")
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

def test_tcp_server_client():
    """Test basic TCP server/client functionality"""
    rank = int(os.environ['RANK'])
    master_port = int(os.environ['MASTER_PORT'])
    
    if rank == 0:  # Server
        print("\nStarting TCP server test...")
        server = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind(('::', master_port))
            server.listen(1)
            print(f"Server listening on port {master_port}")
            
            # Wait for a short time to see if clients connect
            server.settimeout(5)
            try:
                client, addr = server.accept()
                print(f"Received connection from {addr}")
                client.close()
            except socket.timeout:
                print("No clients connected within timeout")
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            server.close()
    else:  # Client
        print("\nStarting TCP client test...")
        client = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        try:
            master_addr = os.environ['MASTER_ADDR']
            print(f"Attempting to connect to {master_addr}:{master_port}")
            client.connect((master_addr, master_port))
            print("Successfully connected to server")
        except Exception as e:
            print(f"Client error: {e}")
        finally:
            client.close()

def main():
    # Set environment variables for distributed setup
    os.environ['RANK'] = os.getenv('RANK', '0')
    os.environ['WORLD_SIZE'] = os.getenv('WORLD_SIZE', '3')  # Using 3 hosts
    
    # Get the master IP address based on rank
    rank = int(os.environ['RANK'])
    if rank == 0:
        master_ip = '2001:db8:1000::2'  # host00 IPv6
    elif rank == 1:
        master_ip = '2001:db8:1001::2'  # host01 IPv6
    else:
        master_ip = '2001:db8:1003::2'  # host03 IPv6
    
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
    
    # Run the TCP server/client test
    test_tcp_server_client()
    
    # Check if master port is in use
    master_port = int(os.environ['MASTER_PORT'])
    print(f"\nChecking master port {master_port} status:")
    print("-" * 50)
    if check_port_status(master_port):
        print(f"Port {master_port} is already in use!")
    else:
        print(f"Port {master_port} is available")
    print("-" * 50)
    
    # Test TCP connectivity between nodes
    print("\nTesting TCP connectivity:")
    print("-" * 50)
    
    # Get local IP address for the backend interface
    backend_iface = os.environ['BACKEND_INTERFACE']
    local_ip = None
    
    # Get IPv6 address from eth1
    addrs = netifaces.ifaddresses(backend_iface)
    if netifaces.AF_INET6 in addrs:
        for addr in addrs[netifaces.AF_INET6]:
            if 'addr' in addr and not addr['addr'].startswith('fe80::'):  # Skip link-local addresses
                local_ip = addr['addr']
                break
    
    if not local_ip:
        print(f"Error: Could not determine IPv6 address for {backend_iface}")
        return
    
    print(f"Local IPv6 on {backend_iface}: {local_ip}")
    
    # Test connectivity to all nodes
    nodes = {
        'host00': '2001:db8:1000::2',  # host00 IPv6
        'host01': '2001:db8:1001::2',  # host01 IPv6
        'host03': '2001:db8:1003::2'   # host03 IPv6
    }
    
    for node_name, node_ip in nodes.items():
        if node_ip != local_ip:  # Don't test self
            print(f"\nTesting connection to {node_name} ({node_ip}):{os.environ['MASTER_PORT']}")
            if test_tcp_connectivity(node_ip, int(os.environ['MASTER_PORT'])):
                print(f"✓ Successfully connected to {node_name}")
            else:
                print(f"✗ Failed to connect to {node_name}")
                # Try to get more information about the failure
                try:
                    print(f"  Attempting detailed connection test...")
                    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    print(f"  Socket created, attempting connect...")
                    sock.connect((node_ip, int(os.environ['MASTER_PORT'])))
                except socket.error as e:
                    print(f"  Error details: {e}")
                    print(f"  Error type: {type(e)}")
                finally:
                    sock.close()
    print("-" * 50)
    
    # Set test source and destination based on rank
    if rank == 0:
        os.environ['TEST_SOURCE'] = 'hosts/clab-sonic-host00'
        os.environ['TEST_DESTINATION'] = 'hosts/clab-sonic-host01'
        ping_destination = '2001:db8:1001::2'  # host-1 IPv6
    elif rank == 1:
        os.environ['TEST_SOURCE'] = 'hosts/clab-sonic-host01'
        os.environ['TEST_DESTINATION'] = 'hosts/clab-sonic-host03'
        ping_destination = '2001:db8:1003::2'  # host-3 IPv6
    else:
        os.environ['TEST_SOURCE'] = 'hosts/clab-sonic-host03'
        os.environ['TEST_DESTINATION'] = 'hosts/clab-sonic-host00'
        ping_destination = '2001:db8:1000::2'  # host-0 IPv6
    
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