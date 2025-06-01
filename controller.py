import os
import logging
import requests
from route_programmer import RouteProgrammerFactory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NetworkProgrammer:
    def __init__(self, api_endpoint):
        """Initialize with the network API endpoint"""
        self.api_endpoint = api_endpoint
        self.collection_name = os.environ.get('TOPOLOGY_COLLECTION', 'network_topology')
        
        # Initialize route programmer - default to Linux
        platform = os.environ.get('ROUTE_PLATFORM', 'linux')
        try:
            self.route_programmer = RouteProgrammerFactory.get_programmer(platform)
            #logger.info(f"Initialized {platform} route programmer")
        except Exception as e:
            logger.error(f"Failed to initialize route programmer: {e}")
            logger.warning("Route programming will be disabled")
            self.route_programmer = None
    
    def get_route_info(self, source, destination):
        """Get route information from the API"""
        try:
            # logger.info(f"Calling network API for {source} -> {destination}")
            url = f"{self.api_endpoint}/graphs/{self.collection_name}/shortest_path/load"
            params = {
                'source': source,
                'destination': destination,
                'direction': 'outbound'
            }
            # logger.info(f"API URL: {url}")
            # logger.info(f"API Parameters: {params}")
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # logger.info(f"API Response: {data}")
            return data
        except Exception as e:
            logger.error(f"Network API call failed for {source} -> {destination}: {e}")
            return None
    
    def program_route(self, destination, srv6_data, interface='eth1'):
        """Program an SRv6 route"""
        if not self.route_programmer:
            logger.error("Route programmer not initialized, cannot program route")
            return False
        
        # Convert destination IP to CIDR if it's not already
        if '/' not in destination:
            destination = f"{destination}/32"
        
        try:
            logger.info(f"  Route to {destination}, SRv6 data: {srv6_data}")
            # Program the route
            success, message = self.route_programmer.program_route(
                destination_prefix=destination,
                srv6_usid=srv6_data['srv6_usid'],
                outbound_interface=interface,
                table_id=int(os.environ.get('ROUTE_TABLE_ID', '254'))
            )
            
            # if success:
            #     logger.info(f"Route programming successful: {message}")
            # else:
            #     logger.error(f"Route programming failed: {message}")
            
            return success
        except Exception as e:
            logger.error(f"Exception during route programming: {e}")
            return False
    
    def program_all_routes(self, nodes):
        """Program routes for all node pairs"""
        if not self.route_programmer:
            logger.error("Route programmer not initialized, cannot program routes")
            return False
        
        # Generate all possible source/destination pairs
        all_pairs = []
        for i in range(len(nodes)):
            for j in range(len(nodes)):
                if i != j:  # Skip self-pairs
                    all_pairs.append({
                        'source': f"hosts/{nodes[i]['hostname']}",
                        'destination': f"hosts/{nodes[j]['hostname']}"
                    })
        
        #logger.info(f"Generated source/destination pairs: {all_pairs}")
        
        # Get route information for each pair
        route_info = {}
        for pair in all_pairs:
            api_response = self.get_route_info(pair['source'], pair['destination'])
            if api_response and api_response.get('found'):
                route_info[f"{pair['source']}_{pair['destination']}"] = api_response
                #logger.info(f"Found route for {pair['source']} -> {pair['destination']}")
            else:
                logger.warning(f"No route found for {pair['source']} -> {pair['destination']}")
        
        # Program routes for current node
        hostname_prefix = os.environ.get('HOSTNAME_PREFIX', 'host')
        rank = int(os.environ.get('RANK', '0'))
        current_host = None
        
        # Find the current node's hostname from the nodes list
        for node in nodes:
            if node['rank'] == rank:
                current_host = f"hosts/{node['hostname']}"
                break
        
        if not current_host:
            logger.error(f"Could not find hostname for rank {rank}")
            return False
        
        for pair_key, api_response in route_info.items():
            source, destination = pair_key.split('_')
            if source == current_host and api_response.get('found'):
                srv6_data = api_response.get('srv6_data', {})
                if srv6_data:
                    # Extract destination network from the API response
                    dest_info = api_response.get('destination_info', {})
                    if not dest_info or 'prefix' not in dest_info or 'prefix_len' not in dest_info:
                        logger.warning(f"No prefix information found for {destination}")
                        continue
                    
                    # Determine IP version from MASTER_ADDR
                    master_addr = os.environ.get('MASTER_ADDR', '')
                    is_ipv6 = ':' in master_addr
                    
                    # Use the appropriate prefix and prefix_len from the API response
                    if is_ipv6:
                        if not dest_info.get('ipv6_address'):
                            logger.warning(f"No IPv6 address found for {destination}")
                            continue
                        dest_ip = f"{dest_info['prefix']}/{dest_info['prefix_len']}"
                    else:
                        if not dest_info.get('ipv4_address'):
                            logger.warning(f"No IPv4 address found for {destination}")
                            continue
                        dest_ip = f"{dest_info['prefix']}/{dest_info['prefix_len']}"
                    
                    try:
                        #logger.info(f"Programming route to {destination} ({dest_ip})")
                        self.program_route(
                            destination=dest_ip,
                            srv6_data=srv6_data,
                            interface=os.environ.get('BACKEND_INTERFACE', 'eth1')
                        )
                    except Exception as e:
                        logger.error(f"Error programming route to {destination}: {e}")
                else:
                    logger.warning(f"No SRv6 data found in API response for {destination}")
            else:
                logger.debug(f"Skipping route for {source} -> {destination} (not current host or no route found)")
        
        return True 